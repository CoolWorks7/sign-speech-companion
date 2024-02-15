finalState = ['q3']
startState = 'q1'

transition = {
    'q1': {
        'h_2': {'state': 'q2', 'output': ''},
        'hello_2': {'state': 'q4', 'output': ''},
        'sign_1': {'state': 'q5', 'output': ''},
        'language_2': {'state': 'q7', 'output': ''},
        'that': {'state': 'q9', 'output': ''},
        'deaf_2': {'state': 'q10', 'output': ''},
        'hear_2': {'state': 'q11', 'output': ''},
        'teacher_1': {'state': 'q14', 'output': ''},
        'thank_you_2': {'state': 'q16', 'output': ''},
        'child': {'state': 'q20', 'output': ''},
        'morning_2': {'state': 'q21', 'output': ''},
        'morning_1': {'state': 'q22', 'output': ''},
        'peace_3': {'state': 'q27', 'output': ''},
        'understand_2': {'state': 'q29', 'output': ''},
        'understand_1': {'state': 'q30', 'output': ''},
        'a': {'state': 'q31', 'output': ''},
        'q': {'state': 'q32', 'output': ''},
        'u': {'state': 'q33', 'output': ''},
        'what': {'state': 'q34', 'output': ''},
        'marry': {'state': 'q35', 'output': ''},
        'relation_1': {'state': 'q36', 'output': ''},
        'relation_2': {'state': 'q37', 'output': ''},
    },
    'q2': {'h_1': {'state': 'q3', 'output': 'h'}},
    'q4': {'hello_1': {'state': 'q3', 'output': 'hello'}},
    'q5': {'sign_2': {'state': 'q6', 'output': ''}},
    'q6': {'sign_1': {'state': 'q3', 'output': 'sign'}},
    'q7': {'language_1': {'state': 'q3', 'output': 'language'}},
    'q9': {
        'woman': {'state': 'q3', 'output': 'she'},
        'man': {'state': 'q3', 'output': 'he'}
    },
    'q10': {'deaf_1': {'state': 'q3', 'output': 'deaf'}},
    'q11': {'hear_1': {'state': 'q12', 'output': ''}},
    'q12': {'hear_2': {'state': 'q13', 'output': ''}},
    'q13': {'hear_1': {'state': 'q3', 'output': 'hear'}},
    'q14': {'teacher_2': {'state': 'q15', 'output': ''}},
    'q15': {'teacher_1': {'state': 'q3', 'output': 'teacher'}},
    'q16': {'thank_you_1': {'state': 'q3', 'output': 'thank you'}},
    'q20': {
        'woman': {'state': 'q3', 'output': 'girl'},
        'man': {'state': 'q3', 'output': 'boy'}
    },
    'q21': {'morning_1': {'state': 'q3', 'output': 'morning'}},
    'q22': {'morning_2': {'state': 'q3', 'output': 'night'}},
    'q27': {'peace_2': {'state': 'q28', 'output': ''}},
    'q28': {'peace_1': {'state': 'q3', 'output': 'peace'}},
    'q29': {'understand_1': {'state': 'q3', 'output': 'understand'}},
    'q30': {'peace_1': {'state': 'q3', 'output': 'remember'}},
    'q31': {
        'a': {'state': 'q3', 'output': 'answer'},
        'woman': {'state': 'q3', 'output': 'aunt'}
    },
    'q32': {'q': {'state': 'q3', 'output': 'question'}},
    'q33': {'u': {'state': 'q3', 'output': 'uncle'}},
    'q34': {
        'why_1': {'state': 'q3', 'output': 'why'},
        'place': {'state': 'q3', 'output': 'where'},
        'time': {'state': 'q3', 'output': 'when'},
        'this': {'state': 'q3', 'output': 'which'}
    },
    'q35': {
        'woman': {'state': 'q3', 'output': 'wife'},
        'man': {'state': 'q3', 'output': 'man'}
    },
    'q36': {
        'woman': {'state': 'q3', 'output': 'sister'},
        'man': {'state': 'q3', 'output': 'brother'}
    },
    'q37': {
        'woman': {'state': 'q3', 'output': 'grand mother'},
        'man': {'state': 'q3', 'output': 'grand father'}
    },
}