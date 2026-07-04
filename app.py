from flask import Flask, request, jsonify
import google.generativeai as genai
import requests as req
from eligibility import check_eligibility, format_schemes_message
from sessions import get_session, update_session, reset_session
import os
from dotenv import load_dotenv

app = Flask(__name__)

load_dotenv()

# ── Gemini AI ──────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# ── Meta WhatsApp Cloud API credentials ───────────────────────────────────────
WHATSAPP_TOKEN  = os.getenv("WHATSAPP_TOKEN")    # Permanent / System User token
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")  # From Meta Developer Dashboard
VERIFY_TOKEN    = os.getenv("VERIFY_TOKEN")      # Any secret string you choose

GRAPH_API_URL = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"

# ── Conversation questions ─────────────────────────────────────────────────────
QUESTIONS = {
    'english': [
        "Welcome to Benefit Bridge AI!\n\nChoose language:\n1- English\n2- Tamil\n3- Hindi",
        "What is your age? (Example: 35)",
        "Your gender?\n1-Male\n2-Female\n3-Other",
        "Annual family income in rupees? (Example: 150000)",
        "Category?\n1-General\n2-OBC\n3-SC\n4-ST\n5-BPL",
        "State?\n1-Tamil Nadu\n2-Delhi\n3-Uttar Pradesh\n4-Other",
        "Own house?\n1-Yes\n2-No",
        "Are you farmer?\n1-Yes\n2-No",
        "Bank account?\n1-Yes\n2-No",
        "Girl child below 10?\n1-Yes\n2-No",
        "Working/employed?\n1-Yes\n2-No"
    ],
    'tamil': [
        "Benefit Bridge AI welcome!\n\nLanguage select:\n1-English\n2-Tamil\n3-Hindi",
        "Age? (Example: 35)",
        "Gender?\n1-Male\n2-Female\n3-Other",
        "Income rupees? (Example: 150000)",
        "Category?\n1-General\n2-OBC\n3-SC\n4-ST\n5-BPL",
        "State?\n1-Tamil Nadu\n2-Other",
        "House?\n1-Yes\n2-No",
        "Farmer?\n1-Yes\n2-No",
        "Bank account?\n1-Yes\n2-No",
        "Girl child below 10?\n1-Yes\n2-No",
        "Working?\n1-Yes\n2-No"
    ]
}


# ── Helper: send a message via Meta Cloud API ──────────────────────────────────
def send_message(to: str, text: str) -> dict:
    """POST a text message to a WhatsApp number through Meta's Graph API."""
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text}
    }
    response = req.post(GRAPH_API_URL, headers=headers, json=payload)
    return response.json()


# ── Helper: parse user answer and update session profile ──────────────────────
def process_answer(session: dict, question_number: int, answer: str) -> bool:
    profile = session.get('profile', {})
    answer = answer.strip().lower()

    if question_number == 1:
        if answer in ['2', 'tamil']:
            session['language'] = 'tamil'
        elif answer in ['3', 'hindi']:
            session['language'] = 'hindi'
        else:
            session['language'] = 'english'

    elif question_number == 2:
        try:
            profile['age'] = int(answer)
        except ValueError:
            return False

    elif question_number == 3:
        if answer in ['1', 'male']:
            profile['gender'] = 'male'
        elif answer in ['2', 'female']:
            profile['gender'] = 'female'
        else:
            profile['gender'] = 'other'

    elif question_number == 4:
        try:
            profile['income'] = int(answer.replace(',', ''))
        except ValueError:
            return False

    elif question_number == 5:
        cats = {'1': 'general', '2': 'obc', '3': 'sc', '4': 'st', '5': 'bpl'}
        profile['category'] = cats.get(answer, 'general')

    elif question_number == 6:
        states = {'1': 'tamil_nadu', '2': 'delhi', '3': 'uttar_pradesh'}
        profile['state'] = states.get(answer, 'other')

    elif question_number == 7:
        profile['has_own_house'] = answer in ['1', 'yes', 'y']

    elif question_number == 8:
        profile['is_farmer'] = answer in ['1', 'yes', 'y']

    elif question_number == 9:
        profile['has_bank_account'] = answer in ['1', 'yes', 'y']

    elif question_number == 10:
        profile['has_girl_child'] = answer in ['1', 'yes', 'y']
        if profile['has_girl_child']:
            profile['girl_child_age'] = 5  # conservative default

    elif question_number == 11:
        profile['is_working'] = answer in ['1', 'yes', 'y']

    session['profile'] = profile
    return True


# ── Route 1: Webhook verification (Meta handshake) ────────────────────────────
@app.route('/webhook', methods=['GET'])
def verify_webhook():
    """
    Meta calls this once when you register the webhook URL.
    It passes hub.verify_token — must match your VERIFY_TOKEN env var.
    Return hub.challenge to confirm ownership.
    """
    mode      = request.args.get('hub.mode')
    token     = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    if mode == 'subscribe' and token == VERIFY_TOKEN:
        print("Webhook verified successfully.")
        return challenge, 200

    print("Webhook verification failed — token mismatch.")
    return 'Forbidden', 403


# ── Route 2: Incoming messages ────────────────────────────────────────────────
@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Meta sends all events (messages, delivery receipts, read receipts) here as JSON.
    We only act on inbound text messages; everything else gets a silent 200.
    """
    data = request.get_json(silent=True) or {}

    # ── Extract message safely ────────────────────────────────────────────────
    try:
        value = data['entry'][0]['changes'][0]['value']

        # Delivery / read status updates don't contain 'messages' — ignore them
        if 'messages' not in value:
            return jsonify({"status": "ok"}), 200

        message = value['messages'][0]

        # Ignore non-text messages (images, audio, stickers, etc.)
        if message.get('type') != 'text':
            return jsonify({"status": "ok"}), 200

        incoming_msg = message['text']['body'].strip()
        sender       = message['from']   # e.g. "919876543210"

    except (KeyError, IndexError, TypeError):
        # Malformed payload — acknowledge and discard
        return jsonify({"status": "ok"}), 200

    # ── Session routing ───────────────────────────────────────────────────────
    session      = get_session(sender)
    current_step = session.get('step', 0)
    language     = session.get('language', 'english')

    # Greeting keywords → restart conversation
    if incoming_msg.lower() in ['hi', 'hello', 'start', 'reset', 'vanakkam', 'namaste']:
        reset_session(sender)
        session = get_session(sender)
        send_message(sender, QUESTIONS['english'][0])
        update_session(sender, {'step': 1})
        return jsonify({"status": "ok"}), 200

    # Step 99 → user is browsing scheme details
    if current_step == 99 and incoming_msg.isdigit():
        schemes = session.get('eligible_schemes', [])
        idx = int(incoming_msg) - 1
        if 0 <= idx < len(schemes):
            scheme = schemes[idx]
            detail_msg = (
                f"*{scheme['name']}*\n\n"
                f"Benefit: {scheme['benefit']}\n"
                f"Documents needed: {', '.join(scheme['documents'])}\n"
                f"Apply here: {scheme['apply_link']}"
            )
            send_message(sender, detail_msg)
        else:
            send_message(sender, "Invalid number! Please reply with a number from the list.")
        return jsonify({"status": "ok"}), 200

    # Step 0 → new / unrecognised user
    if current_step == 0:
        send_message(sender, QUESTIONS['english'][0])
        update_session(sender, {'step': 1})

    # Steps 1–11 → questionnaire
    elif 1 <= current_step <= 11:
        valid = process_answer(session, current_step, incoming_msg)
        if not valid:
            retry_prompt = QUESTIONS[language][current_step - 1] + "\n\n(Invalid input — please try again)"
            send_message(sender, retry_prompt)
        else:
            next_step = current_step + 1
            if next_step > 11:
                # All questions answered → run eligibility check
                profile         = session.get('profile', {})
                eligible_schemes = check_eligibility(profile)
                update_session(sender, {'step': 99, 'eligible_schemes': eligible_schemes})
                send_message(sender, format_schemes_message(eligible_schemes, language))
            else:
                send_message(sender, QUESTIONS[language][next_step - 1])
                update_session(sender, {'step': next_step})

    return jsonify({"status": "ok"}), 200


# ── Health check ──────────────────────────────────────────────────────────────
@app.route('/', methods=['GET'])
def home():
    return "Benefit Bridge AI is running!", 200


if __name__ == "__main__":
    print("Starting Benefit Bridge AI (Meta WhatsApp Cloud API)...")
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
