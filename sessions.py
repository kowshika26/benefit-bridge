user_sessions = {}

def get_session(phone_number):
    if phone_number not in user_sessions:
        user_sessions[phone_number] = {
            'step': 0,
            'language': 'english',
            'profile': {},
            'eligible_schemes': []
        }
    return user_sessions[phone_number]

def update_session(phone_number, updates):
    session = get_session(phone_number)
    session.update(updates)
    user_sessions[phone_number] = session

def reset_session(phone_number):
    user_sessions[phone_number] = {
        'step': 0,
        'language': 'english',
        'profile': {},
        'eligible_schemes': []
    }