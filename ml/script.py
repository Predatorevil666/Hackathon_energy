import json
import csv


def main():
    list_prob = load_csv('./probbility_control_pipeline_random_forest.csv')
    json_list = load_json('./dataset_control.json')

    for i, item in enumerate(json_list):
        item["isCommercial"] = list_prob[i][1] >= list_prob[i][0]

    with open('new_probability.json', 'w') as file:
        json.dump(json_list, file)


def load_json(path):
    with open(path, 'r') as file:
        json_list = json.loads(file.read())

    return json_list


def load_csv(csv_file ):
    list_prob = []
# Method 2: Reading as dictionaries (with headers)
    with open(csv_file, 'r') as file:
        for row in file:
            row = row.strip()
            row = list(map(float, row.split(',')))
            list_prob.append(row)

    return list_prob


if __name__ == '__main__':
    main()
