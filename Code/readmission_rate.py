"""This file contains the implementation of OptiFox Readmission Rate.

More details are listed in file README.md.
"""

import os
import pickle
import pandas as pd
from dataclasses import dataclass, field, asdict
from typing import List, Optional
from flask import abort, jsonify
from utils import logger

# Determine the root folder for relative paths
ROOT_FOLDER = os.getcwd()


@dataclass
class ReadmissionPredictionResult:
    """Class that defines the structure for the readmission prediction result which will be used as
    part of the API."""

    stay_id: int
    success: bool
    readmission_probability: float
    icu_intime: Optional[str]
    last_abs_event_time: Optional[str]
    days_between: Optional[float]
    percentage: float = field(init=False)
    message: Optional[str] = None
    feature_names: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Convert probability to percentage after initialization."""
        self.percentage = None
        if self.readmission_probability is not None:
            self.percentage = self.readmission_probability * 100

    def to_dict(self):
        """Convert the result to a dictionary with JSON serializable values."""
        result_dict = asdict(self)
        # Convert any non-serializable types here (if needed)
        if isinstance(result_dict.get("feature_names"), pd.Index):
            result_dict["feature_names"] = result_dict["feature_names"].tolist()
        return result_dict


class ReadmissionRate:
    """Readmission rate class that houses functions to load the pickle file and generate a valid
    result."""

    def __init__(self, stay_id) -> None:
        """Initialize the ReadmissionRate class with the given stay_id."""
        self.stay_id = int(stay_id)
        self.model_path = os.path.join(ROOT_FOLDER, "models", "final_readmission_model.pkl")

        # Load all necessary objects from the pickle file
        self.loaded_objects = self.load_pickle_file()
        self.best_rf_model = self.loaded_objects["best_rf_model"]
        self.top_features = self.loaded_objects["top_features"]
        self.imputer = self.loaded_objects["imputer"]
        self.encoder = self.loaded_objects["encoder"]
        self.scaler = self.loaded_objects["scaler"]
        self.scaler_final = self.loaded_objects["scaler_final"]
        self.merge_final = self.loaded_objects["merge_final"]

    def load_pickle_file(self):
        """Load the model and other objects from the pickle file."""
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model file '{self.model_path}' not found.")
        with open(self.model_path, "rb") as pickle_file:
            return pickle.load(pickle_file)

    def predict_readmission(self) -> ReadmissionPredictionResult:
        """Predict the readmission probability for the given stay_id using the updated logic."""
        logger.info(f"Predicting readmission likelihood for stay_id: {self.stay_id}")
        stay_data = self.merge_final[self.merge_final["stay_id"] == self.stay_id]

        if stay_data.empty:
            return ReadmissionPredictionResult(
                stay_id=self.stay_id,
                success=False,
                readmission_probability=None,
                icu_intime=None,
                last_abs_event_time=None,
                days_between=None,
                message="No data found for the given stay_id",
                feature_names=None,
            )

        # Prepare the data for prediction
        stay_data = stay_data.drop(columns=["subject_id", "readmitted"], errors="ignore")
        X = stay_data
        numerical_columns = X.select_dtypes(include=["float64", "int64"]).columns.tolist()
        categorical_columns = X.select_dtypes(include=["object"]).columns.tolist()

        # Process the data
        X_imputed = self.imputer.transform(X[numerical_columns])
        X_imputed_df = pd.DataFrame(X_imputed, columns=numerical_columns)
        X_encoded = self.encoder.transform(X[categorical_columns])
        X_encoded_df = pd.DataFrame(
            X_encoded, columns=self.encoder.get_feature_names_out(categorical_columns)
        )
        X_scaled = self.scaler.transform(X_imputed_df)
        X_scaled_df = pd.DataFrame(X_scaled, columns=X_imputed_df.columns)
        X_processed = pd.concat([X_scaled_df, X_encoded_df], axis=1)
        X_final = X_processed[self.top_features]
        X_final_scaled = self.scaler_final.transform(X_final)

        # Predict the readmission likelihood
        readmission_prob = self.best_rf_model.predict_proba(X_final_scaled)[:, 1][0]

        # Extract ICU admission time and last event time
        icu_intime = pd.to_datetime(stay_data["icu_intime"].values[0])
        last_abs_event_time = pd.to_datetime(stay_data["abs_event_time"].max())
        icu_intime_str = icu_intime.strftime("%Y-%m-%d %H:%M:%S")
        last_abs_event_time_str = last_abs_event_time.strftime("%Y-%m-%d %H:%M:%S")

        # Calculate the number of days between icu_intime and last_abs_event_time
        delta = last_abs_event_time - icu_intime
        days_between = delta.days + delta.seconds / (3600 * 24)

        return ReadmissionPredictionResult(
            stay_id=self.stay_id,
            success=True,
            readmission_probability=readmission_prob,
            icu_intime=icu_intime_str,
            last_abs_event_time=last_abs_event_time_str,
            days_between=days_between,
            message="Prediction successful!",
            feature_names=self.top_features,
        )


def get_readmission_prediction(stay_id: str):
    """Get the readmission prediction for the given stay_id."""
    logger.info(f"Attempting to fetch patient information for stay_id: {stay_id}")
    readmission_rate = ReadmissionRate(stay_id)
    prediction_result = readmission_rate.predict_readmission()
    if not prediction_result:
        abort(404, description="Could not find any patient with that associated stay id")
    return jsonify(prediction_result.to_dict())
