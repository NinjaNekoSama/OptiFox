from typing import Any
from src.models.model import IcuBaseClassifier, IcuBaseRegressor


IcuBaseModel = IcuBaseRegressor | IcuBaseClassifier
Metrics = dict[str, Any]
TrainTestMetrics = tuple[Metrics, Metrics]
