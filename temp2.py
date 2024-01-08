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


mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
mp_holistic = mp.solutions.holistic


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


def main():
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
    
    # --------------------- Camera Preparation --------------------- #
    cap = cv.VideoCapture(cap_device)
    cap.set(cv.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv.CAP_PROP_FRAME_HEIGHT, height)

    # --------------------- Load NN Classifier Model --------------------- #
    keypoint_classifier = KeyPointClassifier()

    # --------------------- Read Labels --------------------- #
    with open('model/keypoint_classifier/keypoint_classifier_label.csv',
              encoding='utf-8-sig') as f:
        keypoint_classifier_labels = csv.reader(f)
        keypoint_classifier_labels = [
            row[0] for row in keypoint_classifier_labels
        ]

    # --------------------- Initial Setup --------------------- #
    mode = 1
    t = 0

    # --------------------- Media Pipe Model --------------------- #
    with mp_holistic.Holistic(
        static_image_mode=use_static_image_mode,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5) as holistic:
        while cap.isOpened():
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
                print(NUMBER)
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
            

            success, image = cap.read()
            if not success:
                print("Ignoring empty camera frame.")
                continue

            # image = cv.flip(image, 1)
            debug_image = copy.deepcopy(image)
        
            # To improve performance, optionally mark the image as not writeable to pass by reference.
            image = cv.cvtColor(image, cv.COLOR_BGR2RGB)
            image.flags.writeable = False
            results = holistic.process(image)
            image.flags.writeable = True
            
            data_points = {
                'POSE': [[0, 0]]*9,
                'LEFT': [[0, 0]]*21,
                'RIGHT': [[0, 0]]*21,
                'detected': False
            }
            
            # Drawing White Rectangle
            cv.rectangle(debug_image, (0, 0), (150, 60), (255, 255, 255), -1)

            if results.pose_landmarks is not None:
                pose_landmarks = results.pose_landmarks
                pose_bounding_rect = calc_bounding_rect(debug_image, pose_landmarks)
                pose_landmarks_list = calc_landmark_list(debug_image, pose_landmarks)
                pose_landmarks_list_filtered = [pose_landmarks_list[0], pose_landmarks_list[9], pose_landmarks_list[10], pose_landmarks_list[11], pose_landmarks_list[12], pose_landmarks_list[13], pose_landmarks_list[14], pose_landmarks_list[15], pose_landmarks_list[16]]
                data_points['POSE'] = pose_landmarks_list_filtered
                data_points['detected'] = True

                # if left hand is visible
                if results.left_hand_landmarks is not None:
                    left_hand_landmarks = results.left_hand_landmarks
                    left_hand_bounding_rect = calc_bounding_rect(debug_image, left_hand_landmarks)
                    left_hand_landmarks_list = calc_landmark_list(debug_image, left_hand_landmarks)
                    # connect pose left wrist to left hand
                    pose_landmarks_list[15] = left_hand_landmarks_list[0]
                    pose_landmarks_list_filtered[7] = left_hand_landmarks_list[0]
                    data_points['POSE'] = pose_landmarks_list_filtered
                    data_points['LEFT'] = left_hand_landmarks_list
                    # drawing left hand
                    debug_image = draw_landmarks(debug_image, left_hand_landmarks_list)
                    debug_image = draw_bounding_rect(debug_image, left_hand_bounding_rect)
                    debug_image = draw_info_text(debug_image, left_hand_bounding_rect, 'Left')
                

                # if right hand is visible
                if results.right_hand_landmarks is not None:
                    right_hand_landmarks = results.right_hand_landmarks
                    right_hand_bounding_rect = calc_bounding_rect(debug_image, right_hand_landmarks)
                    right_hand_landmarks_list = calc_landmark_list(debug_image, right_hand_landmarks)
                    # connect pose right wrist to right hand
                    pose_landmarks_list[16] = right_hand_landmarks_list[0]
                    pose_landmarks_list_filtered[8] = right_hand_landmarks_list[0]
                    data_points['POSE'] = pose_landmarks_list_filtered
                    data_points['RIGHT'] = right_hand_landmarks_list
                    # drawing right hand
                    debug_image = draw_landmarks(debug_image, right_hand_landmarks_list)
                    debug_image = draw_bounding_rect(debug_image, right_hand_bounding_rect)
                    debug_image = draw_info_text(debug_image, right_hand_bounding_rect, 'Right')


                # drawing pose
                debug_image = draw_pose_landmarks(debug_image, pose_landmarks_list)
                debug_image = draw_bounding_rect(debug_image, pose_bounding_rect)


                if data_points['detected'] == True:
                    # merge pose, left and right landmarks
                    merged_landmark_list = np.concatenate((data_points['POSE'], data_points['LEFT'], data_points['RIGHT']), axis=0)
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
                            sign = keypoint_classifier_labels[hand_sign_id]

                        cv.putText(debug_image, 'Detected: ' + sign, (10, 50),
                           cv.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1, cv.LINE_AA)


                # Other Stuff
                res = int(t*(width/NEXT_AFTER))
                cv.rectangle(debug_image, (0, height - 20), (res, height), (0, 0, 255), -1)

                mode_info(mode, debug_image, COUNTER)
                

            # --------------------- Display Screen --------------------- #
            cv.imshow('Hand Gesture Recognition', debug_image)

        cap.release()
        cv.destroyAllWindows()





#     while True:



#         # --------------------- Capture Camera --------------------- #
#         ret, image = cap.read()
#         if not ret:
#             break
#         image = cv.flip(image, 1)  # Mirror display
#         debug_image = copy.deepcopy(image)

#         # --------------------- Image Pre-Processing --------------------- #
#         image = cv.cvtColor(image, cv.COLOR_BGR2RGB)

#         image.flags.writeable = False
#         results = hands.process(image)
#         image.flags.writeable = True

#         data_points = {
#             'Left': [0]*42,
#             'Right': [0]*42,
#             'detected': False
#         }
#         # If hands are detected
#         if results.multi_hand_landmarks is not None:
#             for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
#                 # Bounding box calculation
#                 brect = calc_bounding_rect(debug_image, hand_landmarks)
                
#                 # Landmark calculation
#                 landmark_list = calc_landmark_list(debug_image, hand_landmarks)

#                 # Conversion to relative coordinates / normalized coordinates
#                 pre_processed_landmark_list = pre_process_landmark(landmark_list)
                
#                 # Pushing the Data_point of each hand into data_points dict
#                 data_points[handedness.classification[0].label[0:]] = pre_processed_landmark_list
#                 data_points['detected'] = True

#                 # Drawing part
#                 debug_image = draw_bounding_rect(use_brect, debug_image, brect)
#                 debug_image = draw_landmarks(debug_image, landmark_list)
#                 debug_image = draw_info_text(
#                     debug_image,
#                     brect,
#                     handedness,
#                     # keypoint_classifier_labels[hand_sign_id]
#                     ''
#                 )

#         # Drawing While Rectangle
#         cv.rectangle(debug_image, (0, 0), (150, 60), (255, 255, 255), -1)

#         if data_points['detected'] == True:
#             # merge the landmarks of two hands
#             merged_landmark_list = np.concatenate((data_points['Left'], data_points['Right']), axis=0)

#             # --------------------- Write to the dataset file --------------------- #
#             if LOGGING_BOOL:
#                 logging_csv(number, merged_landmark_list)
#                 print('Data Collected: ' + str(number))
#                 LOGGING_BOOL = False

#             # --------------------- Hand Sign Classification Process --------------------- #
#             elif mode == 0:
#                 hand_sign_id = keypoint_classifier(merged_landmark_list)

#                 if hand_sign_id == None:
#                     sign = 'Not Trained!'
#                 else:
#                     sign = keypoint_classifier_labels[hand_sign_id]

#                 cv.putText(debug_image, 'Detected: ' + sign, (10, 50),
#                    cv.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1, cv.LINE_AA)


#         # Other Stuff
#         res = int(t*(width/NEXT_AFTER))
#         cv.rectangle(debug_image, (0, height - 20), (res, height), (0, 0, 255), -1)

#         mode_info(mode, debug_image, COUNTER)

#         # --------------------- Display Screen --------------------- #
#         cv.imshow('Hand Gesture Recognition', debug_image)

#     cap.release()
#     cv.destroyAllWindows()

def show_help():
    print('k \t=>\t change the mode i.e logging/detecting')
    print('0 - 9 \t=>\t input the label number')
    print('backspace \t=>\t remove the last digit of the number')
    print('x \t=>\t reset the number back to 0')
    print('s \t=>\t add a single data when on logging data mode')
    print('s \t=>\t add a single data when on logging data mode')
    print('g \t=>\t get insight on the collected data')
    print('esc \t=>\t close the application')

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


def draw_pose_landmarks(image, landmark_points):
    # 0, 9, 10
    pairs = [[11, 12], [23, 24], [11, 23], [11, 13], [13, 15], [12, 24], [12, 14], [14, 16]]
    dots = np.array(pairs).flatten()
    for pair in pairs:
        if pair[0] == 9 and pair[1] == 10:
            continue
        cv.line(image, tuple(landmark_points[pair[0]]), tuple(landmark_points[pair[1]]), (0, 0, 0), 2)
    
    for dot in dots:
        cv.circle(image, tuple(landmark_points[dot]), 5, (255, 255, 255), -1)
    return image

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


def draw_bounding_rect(image, brect):
    cv.rectangle(image, (brect[0], brect[1]), (brect[2], brect[3]), (0, 0, 0), 1)
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


def draw_info_text(image, brect, info_text):
    cv.rectangle(image, (brect[0], brect[1]), (brect[2], brect[1] - 22),
                 (0, 0, 0), -1)
    cv.putText(image, info_text, (brect[0] + 5, brect[1] - 4),
               cv.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv.LINE_AA)
    return image

if __name__ == '__main__':
    main()