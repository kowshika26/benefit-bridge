from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import google.generativeai as genai
from eligibility import check_eligibility, format_schemes_message
from sessions import get_session, update_session, reset_session

app = Flask(__name__)

# CONFIGURE GEMINI AI HERE
import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

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

def process_answer(session, question_number, answer):
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
        except:
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
            clean_answer = answer.replace(',', '')
            profile['income'] = int(clean_answer)
        except:
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
            profile['girl_child_age'] = 5

    elif question_number == 11:
        profile['is_working'] = answer in ['1', 'yes', 'y']

    session['profile'] = profile
    return True


@app.route('/webhook', methods=['POST'])
def webhook():
    incoming_msg = request.values.get('Body', '').strip()
    sender = request.values.get('From', '')

    resp = MessagingResponse()
    msg = resp.message()
    session = get_session(sender)
    current_step = session.get('step', 0)
    language = session.get('language', 'english')

    if incoming_msg.lower() in ['hi', 'hello', 'start', 'reset', 'vanakkam', 'namaste']:
        reset_session(sender)
        session = get_session(sender)
        questions = QUESTIONS[language]
        msg.body(questions[0])
        update_session(sender, {'step': 1})
        return str(resp)

    if current_step == 99 and incoming_msg.isdigit():
        schemes = session.get('eligible_schemes', [])
        idx = int(incoming_msg) - 1
        if 0 <= idx < len(schemes):
            scheme = schemes[idx]
            detail_msg = f"Scheme: {scheme['name']}\n"
            detail_msg += f"Benefit: {scheme['benefit']}\n"
            detail_msg += f"Documents: {', '.join(scheme['documents'])}\n"
            detail_msg += f"Apply: {scheme['apply_link']}"
            msg.body(detail_msg)
        else:
            msg.body("Invalid number!")
        return str(resp)

    if current_step == 0:
        msg.body(QUESTIONS['english'][0])
        update_session(sender, {'step': 1})
    elif 1 <= current_step <= 11:
        valid = process_answer(session, current_step, incoming_msg)
        if not valid:
            msg.body(QUESTIONS[language][current_step - 1] + "\n(Invalid input, try again)")
        else:
            next_step = current_step + 1
            if next_step > 11:
                profile = session.get('profile', {})
                eligible_schemes = check_eligibility(profile)
                update_session(sender, {
                    'step': 99,
                    'eligible_schemes': eligible_schemes
                })
                result_message = format_schemes_message(eligible_schemes, language)
                msg.body(result_message)
            else:
                msg.body(QUESTIONS[language][next_step - 1])
                update_session(sender, {'step': next_step})

    return str(resp)


@app.route('/', methods=['GET'])
def home():
    return "Bot is running!"


import os

if __name__ == "__main__":
    print("Starting Benefit Bridge AI...")
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)