import json

def load_schemes():
    with open('schemes.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['schemes']

def check_eligibility(user_profile):
    schemes = load_schemes()
    eligible_schemes = []

    for scheme in schemes:
        criteria = scheme.get('eligibility', {})
        is_eligible = True

        # Check income
        if 'max_income' in criteria:
            if user_profile.get('income', 0) > criteria['max_income']:
                is_eligible = False

        # Check age - minimum
        if 'min_age' in criteria:
            if user_profile.get('age', 0) < criteria['min_age']:
                is_eligible = False

        # Check house ownership
        if 'has_own_house' in criteria:
            if criteria['has_own_house'] != user_profile.get('has_own_house', True):
                is_eligible = False

        # Check farmer status
        if 'is_farmer' in criteria:
            if criteria['is_farmer'] != user_profile.get('is_farmer', False):
                is_eligible = False

        # Check bank account
        if 'has_bank_account' in criteria:
            if criteria['has_bank_account'] != user_profile.get('has_bank_account', True):
                is_eligible = False

        # Check girl child
        if 'has_girl_child' in criteria:
            if not user_profile.get('has_girl_child', False):
                is_eligible = False

        # Check category (SC/ST/OBC/BPL)
        if 'category' in criteria:
            if user_profile.get('category', 'general') not in criteria['category']:
                is_eligible = False

        # Check state
        if 'state' in criteria:
            if criteria['state'] != user_profile.get('state', ''):
                is_eligible = False

        # Check gender
        if 'gender' in criteria:
            if criteria['gender'] != user_profile.get('gender', ''):
                is_eligible = False

        # Check working status
        if 'is_working' in criteria:
            if criteria['is_working'] != user_profile.get('is_working', False):
                is_eligible = False

        if is_eligible:
            eligible_schemes.append(scheme)

    return eligible_schemes


def format_schemes_message(schemes, language='english'):
    if not schemes:
        if language == 'tamil':
            return "Sorry, no eligible schemes found!"
        elif language == 'hindi':
            return "Sorry, no eligible schemes found!"
        else:
            return "Sorry, no eligible schemes found!"

    if language == 'tamil':
        message = f"You qualify for {len(schemes)} schemes!\n\n"
    elif language == 'hindi':
        message = f"You qualify for {len(schemes)} schemes!\n\n"
    else:
        message = f"You qualify for {len(schemes)} schemes!\n\n"

    for i, scheme in enumerate(schemes, 1):
        message += f"{i}. {scheme['name']}\n"
        message += f"   Benefit: {scheme['benefit']}\n\n"

    return message