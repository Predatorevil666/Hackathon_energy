import json
import pickle

import numpy as np
import pandas as pd
from keras import Sequential, Input
from keras.optimizers import Adam
from keras.src.layers import BatchNormalization, Dense, LeakyReLU, Dropout
from sklearn.base import BaseEstimator, ClassifierMixin


def main():

    print('load dataset')
    df = load_dataframe_from_json('dataset_test.json')
    df = preparing_dataset(df)

    print('load model')
    model = file_to_pipeline("model_object")
    list_prob = model.predict_proba(df)

    json_list = load_json_for_output('./dataset_test.json')
    for i, item in enumerate(json_list):
        item["isCommercial_control"] = bool(list_prob[i][1] >= list_prob[i][0])

    with open('new_probability.json', 'w') as file:
        json.dump(json_list, file)

    print('success!')


def load_dataframe_from_json(path):
    return pd.read_json(path)


def load_json_for_output(path):
    with open(path, 'r') as file:
        json_list = json.loads(file.read())
    return json_list


def preparing_dataset(df: pd.DataFrame):
    df = unpack_consumption(df)
    df = average_for_season(df)
    df = diff_two_month(df)
    df['mean'] = df.loc[:,'consumption_1':'consumption_12'].apply(mean_consumption, axis=1)
    df['std'] = df.loc[:, 'consumption_1':'consumption_12'].apply(std_consumption, axis=1)
    df['cv'] = df.loc[:, 'consumption_1':'consumption_12'].apply(coefficient_of_variation, axis=1)
    df['sum'] = df.loc[:, 'consumption_1':'consumption_12'].apply(sum_consumption, axis=1)
    df['min'] = df.loc[:, 'consumption_1':'consumption_12'].apply(min_consumption, axis=1)
    df['max'] = df.loc[:, 'consumption_1':'consumption_12'].apply(min_consumption, axis=1)
    df['rooms_per_person'] = df['roomsCount'].div(df['residentsCount'])
    df['total_area_per_person'] = df['totalArea'].div(df['residentsCount'])
    return df


def file_to_pipeline(file):
    with open(file, "rb") as f:
        return pickle.load(f)


def unpack_consumption(df):
    for month in range(1, 13):
        month_str = str(month)
        df[f'consumption_{month_str}'] = df['consumption'].apply(
            lambda x: x.get(month_str, 0) if isinstance(x, dict) else 0
        )
    df = df.drop('consumption', axis=1)
    return df


def average_for_season(df):
    window = 3
    for i in range(1, 12, window):
        df[f'season_average_{int(i/3) + 1}'] = df.loc[:,f'consumption_{i}':f'consumption_{i+window - 1}'].mean(axis=1)

    return df


def diff_two_month(df):
    for i in range(1, 12):
        df[f'diff_{i}'] = df[f'consumption_{i}'] - df[f'consumption_{i+1}']
        df[f'diff_{i}'] = df[f'diff_{i}'].abs()
    return df


def mean_consumption(row):
    return row.mean()


def std_consumption(row):
    return row.std(ddof=0)


def coefficient_of_variation(row):  # Коэффициент вариативности (отношение стандартного отклонения к среднему)
    mean_val = row.mean()
    std_val = row.std(ddof=0)  # ddof=0 для расчета по всей совокупности
    if mean_val != 0:
        return std_val / mean_val
    else:
        return 0  # или np.nan, если среднее равно 0


def sum_consumption(row):
    return row.sum()


def min_consumption(row):
    return row.min()


def max_consumption(row):
    return row.max(axis=1)


class KerasNNClassifier(BaseEstimator, ClassifierMixin):
    def __init__(self, epochs=20, learning_rate=0.1, batch_size=32, verbose=0):
        self.epochs = epochs
        self.learning_rate = learning_rate
        self.batch_size = batch_size
        self.verbose = verbose
        self.classes_ = None
        self.model = self._build_model()

    def _build_model(self, input_dim=None):
        model = Sequential()
        if input_dim:
            model.add(Input(shape=(input_dim,)), )

        model.add(BatchNormalization())
        model.add(Dense(
            units=256,
            activation=LeakyReLU(negative_slope=0.2)
        ))
        model.add(Dropout(0.3))

        model.add(BatchNormalization())
        model.add(Dense(
            units=128,
            activation=LeakyReLU(negative_slope=0.2)
        ))
        model.add(Dropout(0.2))

        model.add(BatchNormalization())
        model.add(Dense(
            units=64,
            activation=LeakyReLU(negative_slope=0.2)
        ))
        model.add(Dropout(0.2))

        model.add(BatchNormalization())
        model.add(Dense(
            units=32,
            activation=LeakyReLU(negative_slope=0.2)
        ))
        model.add(Dropout(0.2))

        model.add(Dense(1, activation="sigmoid"))

        model.compile(
            optimizer=Adam(learning_rate=self.learning_rate),
            loss="binary_crossentropy",
        )
        return model

    def fit(self, X, y):
        self.classes_ = np.unique(y)

        if not hasattr(self.model.layers[0], 'input_shape'):
            self.model = self._build_model(input_dim=X.shape[1])

        self.model.fit(
            X, y,
            epochs=self.epochs,
            batch_size=self.batch_size,
            verbose=self.verbose
        )
        return self

    def predict(self, X):
        return (self.model.predict(X) > 0.5).astype(int)

    def predict_proba(self, X):
        return self.model.predict(X)

    def score(self, X, y, **kwargs):
        return self.model.evaluate(X, y, verbose=0)[1]


if __name__ == '__main__':
    main()
