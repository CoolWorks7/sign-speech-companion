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
    },
    'q2': {'h_1': {'state': 'q3', 'output': 'h'}},
    'q4': {'hello_1': {'state': 'q3', 'output': 'hello'}},
    'q5': {'sign_2': {'state': 'q6', 'output': ''}},
    'q6': {'sign_1': {'state': 'q3', 'output': 'sign'}},
    'q7': {'language_1': {'state': 'q3', 'output': 'language'}},
    'q9': {
        'Woman': {'state': 'q3', 'output': 'she'},
        'Man': {'state': 'q3', 'output': 'he'}
    },
    'q10': {'deaf_1': {'state': 'q3', 'output': 'deaf'}},
    'q11': {'hear_1': {'state': 'q12', 'output': ''}},
    'q12': {'hear_2': {'state': 'q13', 'output': ''}},
    'q13': {'hear_1': {'state': 'q3', 'output': 'hear'}},
    'q14': {'teacher_2': {'state': 'q15', 'output': ''}},
    'q15': {'teacher_1': {'state': 'q3', 'output': 'teacher'}},
}