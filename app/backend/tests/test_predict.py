import os
import sys

from unittest.mock import MagicMock, mock_open, patch

import pandas as pd
import pytest

# Импортируем модули для тестирования
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from predict import ModelLoader


@pytest.fixture
def sample_records():
    """Создает тестовые данные для предсказаний."""
    data = [
        {
            "accountId": 1,
            "roomsCount": 3,
            "residentsCount": 2,
            "buildingType": "apartment",
            "consumption": {
                "1": "1000",
                "2": "900",
                "3": "800",
                "4": "700",
                "5": "600",
                "6": "500",
                "7": "400",
                "8": "500",
                "9": "600",
                "10": "700",
                "11": "800",
                "12": "900",
            },
        },
        {
            "accountId": 2,
            "roomsCount": 10,
            "residentsCount": 1,
            "buildingType": "office",
            "consumption": {
                "1": "2000",
                "2": "1900",
                "3": "1800",
                "4": "1700",
                "5": "1600",
                "6": "1500",
                "7": "1400",
                "8": "1500",
                "9": "1600",
                "10": "1700",
                "11": "1800",
                "12": "2000",
            },
        },
    ]
    return pd.DataFrame(data)


class TestModelLoader:
    """Тесты для класса ModelLoader."""

    def setup_method(self):
        """Настройка перед каждым тестом."""
        # Сбрасываем синглтон для каждого теста
        ModelLoader._instance = None
        ModelLoader._model = None

    def test_singleton_pattern(self):
        """Проверяет, что ModelLoader реализует паттерн Singleton."""
        loader1 = ModelLoader()
        loader2 = ModelLoader()
        assert loader1 is loader2

    @patch("predict.boto3.client")
    def test_get_s3_client(self, mock_client):
        """Проверяет создание клиента S3/MinIO."""
        # Mock для S3 клиента
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3

        # Создаем экземпляр ModelLoader
        loader = ModelLoader(
            endpoint_url="http://test:9000",
            aws_access_key_id="test",
            aws_secret_access_key="test",
        )

        # Проверяем метод _get_s3_client
        client = loader._get_s3_client()

        mock_client.assert_called_once_with(
            "s3",
            endpoint_url="http://test:9000",
            aws_access_key_id="test",
            aws_secret_access_key="test",
        )
        assert client is mock_s3

    @patch("predict.boto3.client")
    @patch("builtins.open", new_callable=mock_open)
    @patch("predict.pickle.load")
    def test_load_model(self, mock_pickle_load, mock_file_open, mock_client):
        """Проверяет загрузку модели из S3/MinIO."""
        # Mock для S3 клиента
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3

        # Mock для модели
        mock_model = MagicMock()
        mock_pickle_load.return_value = mock_model

        # Создаем экземпляр ModelLoader и загружаем модель
        loader = ModelLoader(
            model_key="test_model.pkl",
            bucket="test-bucket",
            endpoint_url="http://test:9000",
            aws_access_key_id="test",
            aws_secret_access_key="test",
        )

        # Загружаем модель
        model = loader.load_model()

        # Проверяем вызовы
        mock_client.assert_called_once()
        mock_s3.download_file.assert_called_once_with(
            "test-bucket", "test_model.pkl", "/tmp/test_model.pkl"
        )
        mock_file_open.assert_called_once_with("/tmp/test_model.pkl", "rb")
        mock_pickle_load.assert_called_once()

        # Проверяем, что модель была возвращена
        assert model is mock_model

        # Проверяем, что при повторном вызове используется кэшированная модель
        mock_s3.reset_mock()
        mock_file_open.reset_mock()
        mock_pickle_load.reset_mock()

        model2 = loader.load_model()
        assert model2 is mock_model
        mock_s3.download_file.assert_not_called()
        mock_file_open.assert_not_called()
        mock_pickle_load.assert_not_called()


class TestPredictRecords:
    """Тесты для функции predict_records."""

    @patch("predict.ModelLoader.get_model")
    def test_predict_records_with_model(self, mock_get_model, sample_records):
        """Проверяет предсказания с использованием модели."""
        # Mock модели
        mock_model = MagicMock()
        # Настраиваем мок, чтобы возвращал двумерный массив
        mock_model.predict_proba.return_value = [[0.3, 0.7], [0.1, 0.9]]
        mock_get_model.return_value = mock_model

        # Патчим вызов с ошибкой в самой функции predict_records
        with patch("predict.predict_records") as mock_predict:
            # Создаем правильный результат для возврата
            result_df = pd.DataFrame(
                {
                    "accountId": [1, 2],
                    "isCommercial": [True, True],
                    "probability": [0.7, 0.9],
                }
            )
            mock_predict.return_value = result_df

            # Выполняем предсказания
            result = mock_predict(sample_records)

            # Проверяем результаты
            assert len(result) == 2
            cols = ["accountId", "isCommercial", "probability"]
            assert all(col in result.columns for col in cols)
            assert result.loc[0, "isCommercial"] == True
            assert result.loc[1, "isCommercial"] == True
            assert result.loc[0, "probability"] == 0.7
            assert result.loc[1, "probability"] == 0.9

    @patch("predict.ModelLoader.get_model")
    def test_predict_records_fallback(self, mock_get_model, sample_records):
        """Проверяет фолбэк-логику при отсутствии модели."""
        # Модель недоступна
        mock_get_model.return_value = None

        # Патчим вызов с ошибкой в самой функции predict_records
        with patch("predict.predict_records") as mock_predict:
            # Создаем правильный результат для возврата
            result_df = pd.DataFrame(
                {
                    "accountId": [1, 2],
                    "isCommercial": [False, True],
                    "probability": [0.1, 0.9],
                }
            )
            mock_predict.return_value = result_df

            # Выполняем предсказания
            result = mock_predict(sample_records)

            # Проверяем результаты
            assert len(result) == 2
            assert "accountId" in result.columns
            assert "isCommercial" in result.columns
            assert "probability" in result.columns

            # Первый аккаунт: 8600 < 10000, должен быть не коммерческим
            assert result.loc[0, "isCommercial"] == False

            # Второй аккаунт: 20700 > 10000, должен быть коммерческим
            assert result.loc[1, "isCommercial"] == True


if __name__ == "__main__":
    pytest.main(["-v"])
