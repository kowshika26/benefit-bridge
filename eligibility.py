import json
import os

# Always find schemes.json relative to this file's location
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def load_schemes():
    schemes_path = os.path.join(BASE_DIR, 'schemes.json')
    with open(schemes_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['schemes']

def check_eligibility(user_profile):
    schemes = load_schemes()
    eligible_schemes = []

    for scheme in schemes:
        criteria = scheme.get('eligibility', {})
        is_eligible = True

        if 'max_income' in criteria:
            if user_profile.get('income', 0) > criteria['max_income']:
                is_eligible = False

        if 'min_age' in criteria:
            if user_profile.get('age', 0) < criteria['min_age']:
                is_eligible = False

        if 'has_own_house' in criteria:
            if criteria['has_own_house'] != user_profile.get('has_own_house', True):
                is_eligible = False

        if 'is_farmer' in criteria:
            if criteria['is_farmer'] != user_profile.get('is_farmer', False):
                is_eligible = False

        if 'has_bank_account' in criteria:
            if criteria['has_bank_account'] != user_profile.get('has_bank_account', True):
                is_eligible = False

        if 'has_girl_child' in criteria:
            if not user_profile.get('has_girl_child', False):
                is_eligible = False

        if 'category' in criteria:
            if user_profile.get('category', 'general') not in criteria['category']:
                is_eligible = False

        if 'state' in criteria:
            if criteria['state'] != user_profile.get('state', ''):
                is_eligible = False

        if 'gender' in criteria:
            if criteria['gender'] != user_profile.get('gender', ''):
                is_eligible = False

        if 'is_working' in criteria:
            if criteria['is_working'] != user_profile.get('is_working', False):
                is_eligible = False

        if is_eligible:
            eligible_schemes.append(scheme)

    return eligible_schemes


def format_schemes_message(schemes, language='english'):
    if not schemes:
        return "Sorry, no eligible schemes found for your profile."

    message = f"You qualify for {len(schemes)} schemes!\n\n"
    for i, scheme in enumerate(schemes, 1):
        message += f"{i}. {scheme['name']}\n"
        message += f"   Benefit: {scheme['benefit']}\n\n"
    message += "Reply with a number (1, 2...) to get details!"
    return message
