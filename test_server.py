import pytest
import pandas as pd
import os
from unittest.mock import patch, MagicMock
from Code.readmission_rate import (
    ReadmissionRate,
    ReadmissionPredictionResult,
    get_readmission_prediction,
)

# Constants
TEST_STAY_ID = 123456
TEST_PROBABILITY = 0.75
INPUT_DATABANK_PATH = os.path.join(os.getcwd(), "data", "processed", "merged_df_cleaned.feather")
MODEL_PICKLE_PATH = os.path.join(os.getcwd(), "models", "Readmission_Model.pkl")

# Sample DataFrame for testing
sample_df = pd.DataFrame(
    {
        "icu_stay_id": [TEST_STAY_ID],
        "icu_los": [10],
        "Glucose_max": [120],
        "Hematocrit_max": [45],
        "Respiratory Rate_mean": [18],
        "Creatinine_max": [1.2],
        "Sodium_min": [135],
        "urine_last_1d": [500],
        "Platelet Count_median": [250],
        "Glucose_median": [110],
        "Strength L Leg_max": [4],
        "Magnesium_median": [2],
        "Magnesium_max": [2.2],
        "MCHC_std": [1],
        "Potassium_min": [3.5],
        "Glucose_min": [80],
        "Anion Gap_max": [12],
        "Respiratory Rate_std": [2],
        "White Blood Cells_max": [10],
        "Phosphorous_median": [3.5],
        "Non Invasive Blood Pressure mean_max": [120],
        "Alanine Aminotransferase (ALT)_median": [30],
    }
)


@pytest.fixture
def readmission_rate():
    return ReadmissionRate(TEST_STAY_ID)


@patch("readmission_rate.pd.read_feather")
@patch("readmission_rate.pickle.load")
@patch("readmission_rate.os.path.exists")
def test_load_pickle_file(mock_exists, mock_pickle_load, mock_read_feather, readmission_rate):
    # Mocking the existence of the model file
    mock_exists.return_value = True

    # Mocking the loading of the model
    mock_model = MagicMock()
    mock_pickle_load.return_value = mock_model

    model = readmission_rate.load_pickle_file()

    mock_exists.assert_called_once_with(MODEL_PICKLE_PATH)
    mock_pickle_load.assert_called_once()
    assert model == mock_model


@patch("readmission_rate.pd.read_feather")
@patch("readmission_rate.pickle.load")
@patch("readmission_rate.os.path.exists")
def test_predict_readmission_success(
    mock_exists, mock_pickle_load, mock_read_feather, readmission_rate
):
    # Mocking the existence of the model file and the feature DataFrame
    mock_exists.return_value = True
    mock_read_feather.return_value = sample_df

    # Mocking the model's predict_proba method
    mock_model = MagicMock()
    mock_model.predict_proba.return_value = [[0.25, TEST_PROBABILITY]]
    mock_pickle_load.return_value = mock_model

    prediction_result = readmission_rate.predict_readmission()

    assert prediction_result.stay_id == TEST_STAY_ID
    assert prediction_result.probability == TEST_PROBABILITY
    assert prediction_result.percentage == TEST_PROBABILITY * 100
    assert prediction_result.message == "Prediction successful!"


@patch("readmission_rate.pd.read_feather")
@patch("readmission_rate.os.path.exists")
def test_predict_readmission_no_stay_id(mock_exists, mock_read_feather, readmission_rate):
    # Mocking the existence of the model file and the feature DataFrame without the stay_id
    mock_exists.return_value = True
    sample_df_no_id = sample_df.copy()
    sample_df_no_id["icu_stay_id"] = [999999]  # Different ID
    mock_read_feather.return_value = sample_df_no_id

    prediction_result = readmission_rate.predict_readmission()

    assert prediction_result.stay_id == TEST_STAY_ID
    assert prediction_result.probability is None
    assert prediction_result.message == "Prediction failed as no such stay_id was found"


@patch("readmission_rate.pd.read_feather")
@patch("readmission_rate.os.path.exists")
def test_predict_readmission_empty_dataframe(mock_exists, mock_read_feather, readmission_rate):
    # Mocking the existence of the model file and an empty feature DataFrame
    mock_exists.return_value = True
    empty_df = pd.DataFrame(columns=sample_df.columns)
    mock_read_feather.return_value = empty_df

    prediction_result = readmission_rate.predict_readmission()

    assert prediction_result.stay_id == TEST_STAY_ID
    assert prediction_result.probability is None
    assert prediction_result.message == "Prediction failed, feature dataframe is empty"


@patch("readmission_rate.ReadmissionRate.predict_readmission")
def test_get_readmission_prediction(mock_predict_readmission):
    # Mocking the prediction result
    mock_result = ReadmissionPredictionResult(
        stay_id=TEST_STAY_ID,
        success=True,
        probability=TEST_PROBABILITY,
    )
    mock_predict_readmission.return_value = mock_result

    with patch("readmission_rate.jsonify") as mock_jsonify:
        response = get_readmission_prediction(TEST_STAY_ID)
        mock_jsonify.assert_called_once_with(mock_result)
        assert response == mock_jsonify.return_value
