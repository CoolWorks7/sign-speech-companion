import csv
import copy
import itertools
import cv2 as cv
import numpy as np
import mediapipe as mp
from model import KeyPointClassifier
import argparse
import ctypes
from insight import get_insight
from transition import finalState, startState, transition

LOOK_UP_TABLE = {
    'h': ['h_1', 'h_2'],
}

def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("--device", type=int, default=0)
    parser.add_argument("--width", help='cap width', type=int, default=540)
    parser.add_argument("--height", help='cap height', type=int, default=540)

    parser.add_argument('--use_static_image_mode', action='store_true')
    parser.add_argument("--min_detection_confidence", help='min_detection_confidence', type=float, default=0.7)
    parser.add_argument("--min_tracking_confidence", help='min_tracking_confidence', type=int, default=0.5)
    args = parser.parse_args()
    return args


BUFFER = []

def main():
    global BUFFER

    user32 = ctypes.windll.user32
    width = int(user32.GetSystemMetrics(0) / 2)
    height = int(user32.GetSystemMetrics(1) / 2)

    # --------------------- Argument parsing --------------------- #
    args = get_args()
    cap_device = args.device

    use_static_image_mode = args.use_static_image_mode
    min_detection_confidence = args.min_detection_confidence
    min_tracking_confidence = args.min_tracking_confidence

    seconds = 2
    STARTED = False
    COUNTER = 0
    LOGGING_BOOL = False
    NUMBER = 0
    NEXT_AFTER = 15*seconds
    use_brect = True
    SYMBOL_COUNTER = 0
    MAX_SYMBOL_COUNTER = 25

    # --------------------- Camera Preparation --------------------- #
    cap = cv.VideoCapture(cap_device)
    cap.set(cv.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv.CAP_PROP_FRAME_HEIGHT, height)

    # --------------------- Load MediaPipe Model --------------------- #
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        static_image_mode=use_static_image_mode,
        max_num_hands=2,
        min_detection_confidence=min_detection_confidence,
        min_tracking_confidence=min_tracking_confidence,
    )

    mp_face = mp.solutions.face_detection
    face = mp_face.FaceDetection(
        # static_image_mode=use_static_image_mode,
        # max_num_hands=2,
        # min_detection_confidence=min_detection_confidence,
        # min_tracking_confidence=min_tracking_confidence,
        model_selection=1, min_detection_confidence=0.5
    )

    # --------------------- Load NN Classifier Model --------------------- #
    keypoint_classifier = KeyPointClassifier()

    # --------------------- Read Labels --------------------- #
    with open('model/keypoint_classifier/keypoint_classifier_label.csv',
              encoding='utf-8-sig') as f:
        keypoint_classifier_labels = csv.reader(f)
        keypoint_classifier_labels = [
            row[0] for row in keypoint_classifier_labels
        ]

    
    resultDict = {}
    # --------------------- Initial Setup --------------------- #
    mode = 1
    t = 0

    while True:
        key = cv.waitKey(10)
        # if key != -1:
        #     print(key)

        if key == 27:  # ESC
            print('Exited the Program!')
            break
        elif key == 115 and not STARTED:    # s -> Save to the csv
            if mode == 1: LOGGING_BOOL = True
        elif key == 120 and not STARTED:    # x -> Reset the number
            NUMBER = 0
            print('Number: ' + str(NUMBER))
        elif key == 107 and not STARTED:    # k
            if mode == 1:
                mode = 0
                print('Mode: Detecting!')
            else:
                mode = 1
                t = 0
                print('Mode: Logging Data!')
        elif 0 <= (key - 48) <= 9 and not STARTED:
            if mode == 1: NUMBER = NUMBER*10 + (key - 48)
            print(NUMBER, end=' corresponds to ')
            print(keypoint_classifier_labels[NUMBER])
        elif key == 8 and not STARTED:  # backspace -> Delete the last number
            if mode == 1: NUMBER = int(NUMBER/10)
            print(NUMBER)
        elif key == 13 and mode == 1:   # enter -> start/stop the snap shooting
            STARTED = not STARTED
            t = 0
            COUNTER = 0
            if STARTED: print('Started Logging!')
            else: print('Stopped Logging!')
        elif key == 103:    # g -> get insight
            get_insight()
        elif key == 104:    # h -> help
            show_help()

        number = NUMBER
        
        if STARTED:
            t = t + 1
            if t % NEXT_AFTER == 0:
                t = 0
                LOGGING_BOOL = True
                COUNTER = COUNTER + 1


        # --------------------- Capture Camera --------------------- #
        ret, image = cap.read()
        if not ret:
            break
        image = cv.flip(image, 1)  # Mirror display
        debug_image = copy.deepcopy(image)

        # --------------------- Image Pre-Processing --------------------- #
        image = cv.cvtColor(image, cv.COLOR_BGR2RGB)

        image.flags.writeable = False
        results = hands.process(image)
        result2 = face.process(image)
        image.flags.writeable = True

        data_points = {
            'Face': [[0, 0]]*1,
            'Left': [[0, 0]]*21,
            'Right': [[0, 0]]*21,
            'detected': False
        }

        # if face is detected
        if result2.detections is not None:
            face_landmarks = result2.detections[0].location_data
            face_bounding_rect = calc_bounding_rect_face(debug_image, [face_landmarks.relative_bounding_box])
            face_landmarks_list = calc_landmark_list_face(debug_image, face_landmarks.relative_keypoints)[2: 3]
            data_points['Face'] = face_landmarks_list

            debug_image = draw_bounding_rect(use_brect, debug_image, face_bounding_rect)
            debug_image = draw_face_landmarks(debug_image, face_landmarks_list)
            

        # If hands are detected
        if results.multi_hand_landmarks is not None:
            for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):

                brect = calc_bounding_rect(debug_image, hand_landmarks)
                landmark_list = calc_landmark_list(debug_image, hand_landmarks)
                data_points[handedness.classification[0].label[0:]] = landmark_list
                # pre_processed_landmark_list = pre_process_landmark(landmark_list)
                # data_points[handedness.classification[0].label[0:]] = pre_processed_landmark_list
                data_points['detected'] = True

                # Drawing part
                debug_image = draw_bounding_rect(use_brect, debug_image, brect)
                debug_image = draw_landmarks(debug_image, landmark_list)
                debug_image = draw_info_text(
                    debug_image,
                    brect,
                    handedness,
                    # keypoint_classifier_labels[hand_sign_id]
                    ''
                )

        # Drawing While Rectangle
        cv.rectangle(debug_image, (0, 0), (150, 60), (255, 255, 255), -1)

        if data_points['detected'] == True:
            # incrementing the symbol counter
            SYMBOL_COUNTER = SYMBOL_COUNTER + 1
            
            # print('INFINITE')

            # merge the landmarks of two hands
            merged_landmark_list = np.concatenate((data_points['Face'], data_points['Left'], data_points['Right']), axis=0)
            # convert the points relatively to 1st point
            pre_process_merged_list = pre_process_landmark(merged_landmark_list)

            # --------------------- Write to the dataset file --------------------- #
            if LOGGING_BOOL:
                logging_csv(number, pre_process_merged_list)
                print('Data Collected: ' + str(number))
                LOGGING_BOOL = False

            # --------------------- Hand Sign Classification Process --------------------- #
            elif mode == 0:
                hand_sign_id = keypoint_classifier(pre_process_merged_list)

                if hand_sign_id == None:
                    sign = 'Not Trained!'
                else:
                    # symbol = keypoint_classifier_labels[hand_sign_id]
                    # if len(BUFFER) == 0 or BUFFER[-1] != symbol:
                    #     if SYMBOL_COUNTER >= MAX_SYMBOL_COUNTER:
                    #         SYMBOL_COUNTER = 0
                    #         BUFFER.append(symbol)
                    #         print(BUFFER)
                    #         validateBuffer(BUFFER)
                    sign = keypoint_classifier_labels[hand_sign_id]
                    
                    # creating a temp hash map that contains the number of times a sign was predicted
                    try :
                        resultDict[sign] = resultDict[sign] + 1
                        prominentSign = max(resultDict, key=resultDict.get)
                        # if sign occurs more than 16 times then it is most prominent sign and we add it to the buffer
                        if resultDict[prominentSign] > 16:
                            BUFFER.append(prominentSign)
                            print(BUFFER)
                            try:
                                # The part which should be inside a function
                                index = len(BUFFER) - 1
                                state = startState
                                output = ''
                                while (index > 0 and state not in finalState) :
                                    inp = BUFFER[index]
                                    fin = transition[state][inp]
                                    state = fin['state']
                                    output = fin['output']
                                    index = index - 1
                                
                                if output != '':
                                    BUFFER = BUFFER[0: index + 1]
                                    BUFFER.append(output)
                            except:
                                pass
                            finally:
                                resultDict = {} 
                                cv.rectangle(debug_image, (0, 0), (width, height), (255, 255, 255), -1)
                                    
                    except:
                        resultDict[sign] = 1

                cv.putText(debug_image, 'Detected: ' + sign, (10, 50),
                   cv.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1, cv.LINE_AA)


        # Other Stuff
        res = int(t*(width/NEXT_AFTER))
        cv.rectangle(debug_image, (0, height - 20), (res, height), (0, 0, 255), -1)
        
        
        # if (len(BUFFER) > 3) :
        #     # cv.rectangle(debug_image, (0, height - 20), (res, height), (0, 0, 255), -1)
        #     cv.putText(debug_image, ''.join(BUFFER[-3: ]), (20, height - 30), cv.FONT_HERSHEY_SIMPLEX, 0.6, (1, 1, 1), 1, cv.LINE_AA)

        mode_info(mode, debug_image, COUNTER)

        # --------------------- Display Screen --------------------- #
        cv.imshow('Hand Gesture Recognition', debug_image)

    cap.release()
    cv.destroyAllWindows()

def show_help():
    print('k \t=>\t change the mode i.e logging/detecting')
    print('0 - 9 \t=>\t input the label number')
    print('backspace \t=>\t remove the last digit of the number')
    print('x \t=>\t reset the number back to 0')
    print('s \t=>\t add a single data when on logging data mode')
    print('s \t=>\t add a single data when on logging data mode')
    print('g \t=>\t get insight on the collected data')
    print('esc \t=>\t close the application')

def validateBuffer(buffer):
    global BUFFER
    
    try:
        last = buffer[-1]
        i = last.index('_')
        last = last[0: i]
        list_point = LOOK_UP_TABLE[last]

        if len(buffer) >= len(list_point):
            for i in range(len(list_point)):
                if buffer[- len(list_point) + i] == list_point[i]:
                    print(buffer[- len(list_point) + i], end=' ')
                    continue
                else:
                    return
            print()

            buffer = [i for i in buffer if '_' not in i]
            buffer.append(last)
            BUFFER = buffer
            # return buffer
            # buffer[- len(list_point)] = last
            # del buffer[- len(list_point) + 1: ]
            # for i in range(len(list_point)): 
            #     print('removed')
            #     buffer.pop(- len(list_point) + i)

            # print('found ' + last)
            # print(buffer)
    except: 
        pass



def calc_bounding_rect(image, landmarks):
    image_width, image_height = image.shape[1], image.shape[0]
    landmark_array = np.empty((0, 2), int)

    for _, landmark in enumerate(landmarks.landmark):
        landmark_x = min(int(landmark.x * image_width), image_width - 1)
        landmark_y = min(int(landmark.y * image_height), image_height - 1)

        landmark_point = [np.array((landmark_x, landmark_y))]

        landmark_array = np.append(landmark_array, landmark_point, axis=0)

    x, y, w, h = cv.boundingRect(landmark_array)

    return [x, y, x + w, y + h]

def calc_bounding_rect_face(image, landmarks):
    image_width, image_height = image.shape[1], image.shape[0]
    landmark_array = []

    for _, landmark in enumerate(landmarks):
        landmark_x = min(int(landmark.xmin * image_width), image_width - 1)
        landmark_y = min(int(landmark.ymin * image_height), image_height - 1)
        landmark_width = min(int(landmark.width * image_width), image_width - 1)
        landmark_height = min(int(landmark.height * image_height), image_height - 1)

        landmark_array = [landmark_x, landmark_y, landmark_x + landmark_width,  landmark_y + landmark_height]
    return landmark_array


def calc_landmark_list(image, landmarks):
    image_width, image_height = image.shape[1], image.shape[0]

    landmark_point = []

    # Keypoint
    for _, landmark in enumerate(landmarks.landmark):
        landmark_x = min(int(landmark.x * image_width), image_width - 1)
        landmark_y = min(int(landmark.y * image_height), image_height - 1)
        # landmark_z = landmark.z

        landmark_point.append([landmark_x, landmark_y])

    return landmark_point

def calc_landmark_list_face(image, landmarks):
    image_width, image_height = image.shape[1], image.shape[0]

    landmark_point = []

    # Keypoint
    for _, landmark in enumerate(landmarks):
        landmark_x = min(int(landmark.x * image_width), image_width - 1)
        landmark_y = min(int(landmark.y * image_height), image_height - 1)
        # landmark_z = landmark.z

        landmark_point.append([landmark_x, landmark_y])

    return landmark_point


def pre_process_landmark(landmark_list):
    temp_landmark_list = copy.deepcopy(landmark_list)

    # Convert to relative coordinates
    base_x, base_y = 0, 0
    for index, landmark_point in enumerate(temp_landmark_list):
        if index == 0:
            base_x, base_y = landmark_point[0], landmark_point[1]

        temp_landmark_list[index][0] = temp_landmark_list[index][0] - base_x
        temp_landmark_list[index][1] = temp_landmark_list[index][1] - base_y

    # Convert to a one-dimensional list
    temp_landmark_list = list(
        itertools.chain.from_iterable(temp_landmark_list))

    # Normalization
    max_value = max(list(map(abs, temp_landmark_list)))

    def normalize_(n):
        return n / max_value

    temp_landmark_list = list(map(normalize_, temp_landmark_list))

    return temp_landmark_list


def logging_csv(number, landmark_list):
    csv_path = 'model/keypoint_classifier/keypoint.csv'
    with open(csv_path, 'a', newline="") as f:
        writer = csv.writer(f)
        writer.writerow([number, *landmark_list])


def draw_landmarks(image, landmark_point):
    if len(landmark_point) > 0:
        # Thumb
        cv.line(image, tuple(landmark_point[2]), tuple(landmark_point[3]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[2]), tuple(landmark_point[3]),
                (0, 255, 0), 2)
        cv.line(image, tuple(landmark_point[3]), tuple(landmark_point[4]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[3]), tuple(landmark_point[4]),
                (0, 255, 0), 2)

        # Index finger
        cv.line(image, tuple(landmark_point[5]), tuple(landmark_point[6]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[5]), tuple(landmark_point[6]),
                (0, 255, 0), 2)
        cv.line(image, tuple(landmark_point[6]), tuple(landmark_point[7]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[6]), tuple(landmark_point[7]),
                (0, 255, 0), 2)
        cv.line(image, tuple(landmark_point[7]), tuple(landmark_point[8]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[7]), tuple(landmark_point[8]),
                (0, 255, 0), 2)

        # Middle finger
        cv.line(image, tuple(landmark_point[9]), tuple(landmark_point[10]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[9]), tuple(landmark_point[10]),
                (0, 255, 0), 2)
        cv.line(image, tuple(landmark_point[10]), tuple(landmark_point[11]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[10]), tuple(landmark_point[11]),
                (0, 255, 0), 2)
        cv.line(image, tuple(landmark_point[11]), tuple(landmark_point[12]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[11]), tuple(landmark_point[12]),
                (0, 255, 0), 2)

        # Ring finger
        cv.line(image, tuple(landmark_point[13]), tuple(landmark_point[14]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[13]), tuple(landmark_point[14]),
                (0, 255, 0), 2)
        cv.line(image, tuple(landmark_point[14]), tuple(landmark_point[15]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[14]), tuple(landmark_point[15]),
                (0, 255, 0), 2)
        cv.line(image, tuple(landmark_point[15]), tuple(landmark_point[16]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[15]), tuple(landmark_point[16]),
                (0, 255, 0), 2)

        # Little finger
        cv.line(image, tuple(landmark_point[17]), tuple(landmark_point[18]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[17]), tuple(landmark_point[18]),
                (0, 255, 0), 2)
        cv.line(image, tuple(landmark_point[18]), tuple(landmark_point[19]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[18]), tuple(landmark_point[19]),
                (0, 255, 0), 2)
        cv.line(image, tuple(landmark_point[19]), tuple(landmark_point[20]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[19]), tuple(landmark_point[20]),
                (0, 255, 0), 2)

        # Palm
        cv.line(image, tuple(landmark_point[0]), tuple(landmark_point[1]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[0]), tuple(landmark_point[1]),
                (0, 255, 0), 2)
        cv.line(image, tuple(landmark_point[1]), tuple(landmark_point[2]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[1]), tuple(landmark_point[2]),
                (0, 255, 0), 2)
        cv.line(image, tuple(landmark_point[2]), tuple(landmark_point[5]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[2]), tuple(landmark_point[5]),
                (0, 255, 0), 2)
        cv.line(image, tuple(landmark_point[5]), tuple(landmark_point[9]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[5]), tuple(landmark_point[9]),
                (0, 255, 0), 2)
        cv.line(image, tuple(landmark_point[9]), tuple(landmark_point[13]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[9]), tuple(landmark_point[13]),
                (0, 255, 0), 2)
        cv.line(image, tuple(landmark_point[13]), tuple(landmark_point[17]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[13]), tuple(landmark_point[17]),
                (0, 255, 0), 2)
        cv.line(image, tuple(landmark_point[17]), tuple(landmark_point[0]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[17]), tuple(landmark_point[0]),
                (0, 255, 0), 2)

    # Key Points
    for index, landmark in enumerate(landmark_point):
        if index == 0:  # 手首1
            cv.circle(image, (landmark[0], landmark[1]), 5, (255, 255, 255),
                      -1)
            cv.circle(image, (landmark[0], landmark[1]), 5, (0, 0, 0), 1)
        if index == 1:  # 手首2
            cv.circle(image, (landmark[0], landmark[1]), 5, (255, 255, 255),
                      -1)
            cv.circle(image, (landmark[0], landmark[1]), 5, (0, 0, 0), 1)
        if index == 2:  # 親指：付け根
            cv.circle(image, (landmark[0], landmark[1]), 5, (255, 255, 255),
                      -1)
            cv.circle(image, (landmark[0], landmark[1]), 5, (0, 0, 0), 1)
        if index == 3:  # 親指：第1関節
            cv.circle(image, (landmark[0], landmark[1]), 5, (255, 255, 255),
                      -1)
            cv.circle(image, (landmark[0], landmark[1]), 5, (0, 0, 0), 1)
        if index == 4:  # 親指：指先
            cv.circle(image, (landmark[0], landmark[1]), 8, (255, 255, 255),
                      -1)
            cv.circle(image, (landmark[0], landmark[1]), 8, (0, 0, 0), 1)
        if index == 5:  # 人差指：付け根
            cv.circle(image, (landmark[0], landmark[1]), 5, (255, 255, 255),
                      -1)
            cv.circle(image, (landmark[0], landmark[1]), 5, (0, 0, 0), 1)
        if index == 6:  # 人差指：第2関節
            cv.circle(image, (landmark[0], landmark[1]), 5, (255, 255, 255),
                      -1)
            cv.circle(image, (landmark[0], landmark[1]), 5, (0, 0, 0), 1)
        if index == 7:  # 人差指：第1関節
            cv.circle(image, (landmark[0], landmark[1]), 5, (255, 255, 255),
                      -1)
            cv.circle(image, (landmark[0], landmark[1]), 5, (0, 0, 0), 1)
        if index == 8:  # 人差指：指先
            cv.circle(image, (landmark[0], landmark[1]), 8, (255, 255, 255),
                      -1)
            cv.circle(image, (landmark[0], landmark[1]), 8, (0, 0, 0), 1)
        if index == 9:  # 中指：付け根
            cv.circle(image, (landmark[0], landmark[1]), 5, (255, 255, 255),
                      -1)
            cv.circle(image, (landmark[0], landmark[1]), 5, (0, 0, 0), 1)
        if index == 10:  # 中指：第2関節
            cv.circle(image, (landmark[0], landmark[1]), 5, (255, 255, 255),
                      -1)
            cv.circle(image, (landmark[0], landmark[1]), 5, (0, 0, 0), 1)
        if index == 11:  # 中指：第1関節
            cv.circle(image, (landmark[0], landmark[1]), 5, (255, 255, 255),
                      -1)
            cv.circle(image, (landmark[0], landmark[1]), 5, (0, 0, 0), 1)
        if index == 12:  # 中指：指先
            cv.circle(image, (landmark[0], landmark[1]), 8, (255, 255, 255),
                      -1)
            cv.circle(image, (landmark[0], landmark[1]), 8, (0, 0, 0), 1)
        if index == 13:  # 薬指：付け根
            cv.circle(image, (landmark[0], landmark[1]), 5, (255, 255, 255),
                      -1)
            cv.circle(image, (landmark[0], landmark[1]), 5, (0, 0, 0), 1)
        if index == 14:  # 薬指：第2関節
            cv.circle(image, (landmark[0], landmark[1]), 5, (255, 255, 255),
                      -1)
            cv.circle(image, (landmark[0], landmark[1]), 5, (0, 0, 0), 1)
        if index == 15:  # 薬指：第1関節
            cv.circle(image, (landmark[0], landmark[1]), 5, (255, 255, 255),
                      -1)
            cv.circle(image, (landmark[0], landmark[1]), 5, (0, 0, 0), 1)
        if index == 16:  # 薬指：指先
            cv.circle(image, (landmark[0], landmark[1]), 8, (255, 255, 255),
                      -1)
            cv.circle(image, (landmark[0], landmark[1]), 8, (0, 0, 0), 1)
        if index == 17:  # 小指：付け根
            cv.circle(image, (landmark[0], landmark[1]), 5, (255, 255, 255),
                      -1)
            cv.circle(image, (landmark[0], landmark[1]), 5, (0, 0, 0), 1)
        if index == 18:  # 小指：第2関節
            cv.circle(image, (landmark[0], landmark[1]), 5, (255, 255, 255),
                      -1)
            cv.circle(image, (landmark[0], landmark[1]), 5, (0, 0, 0), 1)
        if index == 19:  # 小指：第1関節
            cv.circle(image, (landmark[0], landmark[1]), 5, (255, 255, 255),
                      -1)
            cv.circle(image, (landmark[0], landmark[1]), 5, (0, 0, 0), 1)
        if index == 20:  # 小指：指先
            cv.circle(image, (landmark[0], landmark[1]), 8, (255, 255, 255),
                      -1)
            cv.circle(image, (landmark[0], landmark[1]), 8, (0, 0, 0), 1)

    return image


def draw_face_landmarks(image, landmark_points):
    for index, landmark_point in enumerate(landmark_points):
        cv.circle(image, (landmark_point[0], landmark_point[1]), 3, (255, 255, 255), -1)
        # cv.putText(image, str(index), (landmark_point[0], landmark_point[1]), cv.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1, cv.LINE_AA)
    return image

def draw_bounding_rect(use_brect, image, brect):
    if use_brect:
        # Outer rectangle
        cv.rectangle(image, (brect[0], brect[1]), (brect[2], brect[3]),
                     (0, 0, 0), 1)
    return image


def mode_info(mode, image, ctr):
    mode_text = 'Nothing'
    if mode == 0:
        mode_text = 'Detecting'
    elif mode == 1:
        mode_text = 'Logging Data'
        cv.putText(image, 'Counter: ' + str(ctr), (10, 50),
                   cv.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1, cv.LINE_AA)
    cv.putText(image, mode_text, (10, 20),
               cv.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1, cv.LINE_AA)


def draw_info_text(image, brect, handedness, hand_sign_text):
    cv.rectangle(image, (brect[0], brect[1]), (brect[2], brect[1] - 22),
                 (0, 0, 0), -1)
    info_text = handedness.classification[0].label[0:]
    if hand_sign_text != "":
        info_text = info_text + ':' + hand_sign_text
    cv.putText(image, info_text, (brect[0] + 5, brect[1] - 4),
               cv.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv.LINE_AA)
    return image


if __name__ == '__main__':
    main()