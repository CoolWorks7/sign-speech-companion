import csv

def get_insight():
    # read and store the keypoint labels
    with open('model/keypoint_classifier/keypoint_classifier_label.csv', encoding='utf-8-sig') as f:
        keypoint_classifier_labels = csv.reader(f)
        keypoint_classifier_labels = [
            row[0] for row in keypoint_classifier_labels
        ]

    # Create a dictionary to store the counts
    number_counts = {}
    with open('model/keypoint_classifier/keypoint.csv', 'r') as file:
        csv_reader = csv.reader(file)

        for row in csv_reader:
            if row:
                first_column_value = row[0]
                number_counts[first_column_value] = number_counts.get(first_column_value, 0) + 1

    for number, count in number_counts.items():
        print(f"{keypoint_classifier_labels[int(number)]}: {count} occurrences")

if __name__ == '__main__':
    get_insight()