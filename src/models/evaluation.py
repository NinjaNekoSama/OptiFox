import functools
from typing import Callable, Protocol, Sequence, Any

import numpy as np
import pandas as pd
from omegaconf import DictConfig
from sklearn import metrics

from src.utils import get_logger
from src.utils.types import IcuBaseModel
from numpy.typing import NDArray

log = get_logger(__name__)


class Metric(Protocol):
    def __call__(
        self,
        y: np.ndarray | pd.Series,
        y_hat: np.ndarray | pd.Series,
        weights: np.ndarray | None = None,
        axis: int | None = None,
        **kwargs,
    ) -> float | np.ndarray:
        ...


def get_metric(name: str) -> Metric:
    # from neuralforecast.losses import numpy as nfnp
    from utilsforecast import losses as utl

    try:
        scorer: Metric = getattr(utl, name)
    except KeyError:
        raise ValueError(
            "%r is not a valid metric value. "
            "check neuralforecast library "
            "to get valid options." % name
        )
    return scorer


def smape(A, F):
    # src: https://stackoverflow.com/a/51440114
    return 100 / len(A) * np.sum(2 * np.abs(F - A) / (np.abs(A) + np.abs(F)))


def get_sklearn_metric(name: str) -> Callable[[NDArray, NDArray], NDArray | float] | None:
    # from neuralforecast.losses import numpy as nfnp
    import sklearn.metrics as sklm

    SCORER_MAPPING = {
        "mae": sklm.mean_absolute_error,
        "mape": sklm.mean_absolute_percentage_error,
        "mse": sklm.mean_squared_error,
        "msle": sklm.mean_squared_log_error,
        "rmse": functools.partial(sklm.mean_squared_error, squared=False),
        "smape": smape,
    }
    try:
        fun = SCORER_MAPPING[name]
        return fun
    except KeyError:
        log.warning(
            "%r is not a valid metric value. "
            "check sklearn.get_sco library "
            "to get valid options." % name
        )
        return None


def evaluate_model(
    model: IcuBaseModel,
    X: pd.DataFrame,
    y: pd.DataFrame,
    eval_cfg: DictConfig,
    logger: Any | None,
) -> dict[str, float | np.ndarray]:
    # calculate the prediction for simple models
    y = y.to_numpy()
    y_pred = model.predict(X)
    metrics = regression_results(y, y_pred, eval_cfg.metrics, eval_cfg.round_digits)
    if logger:
        logger.log_metrics(metrics)
    return metrics


def regression_results(
    y_true: np.ndarray, y_pred: np.ndarray, metrics_config: Sequence[str], round_digits: int
) -> dict[str, float | np.ndarray]:
    result: dict[str, float | np.ndarray] = {}
    # TODO we shouldn't mix data types in dict too much if we want to keep logging simple:
    # (metrics -> float, int, ndarray)
    # right now this will probably crash, since you can't simply round everything.

    if "explained_variance" in metrics_config:
        # Regression metrics
        explained_variance = metrics.explained_variance_score(y_true, y_pred)
        result["explained_variance"] = explained_variance
        log.info(f"explained variance: {round(explained_variance, round_digits)}")

    if (
        "mean_squared_log_error" in metrics_config
        and not any(i <= 0 for i in y_true)
        and not any(i <= 0 for i in y_pred)
    ):
        mean_squared_log_error = metrics.mean_squared_log_error(y_true, y_pred)
        result["mean_squared_log_error"] = mean_squared_log_error
        log.info(f"mean squared log error: {round(mean_squared_log_error, round_digits)}")
    else:
        log.warning(
            "mean_squared_log_error could not be calculated cause either the metric is"
            + " missing in the config or the some values are negative!"
        )

    if "mean_absolute_error" in metrics_config:
        mean_absolute_error = metrics.mean_absolute_error(y_true, y_pred)
        result["mae"] = mean_absolute_error
        log.info(f"MAE: {round(mean_absolute_error, round_digits)}")

    if "mean_squared_error" in metrics_config:
        mse = metrics.mean_squared_error(y_true, y_pred)
        result["mse"] = mse
        log.info(f"MSE: {round(mse, round_digits)}")

    if "root_mean_squared_error" in metrics_config:
        mse = result.get("mse", metrics.mean_squared_error(y_true, y_pred))
        rmse = np.sqrt(mse)
        result["rmse"] = rmse
        log.info(f"RMSE: {round(rmse, round_digits)}")

    if "max_error" in metrics_config:
        max_error = metrics.max_error(y_true, y_pred)
        result["max_error"] = max_error
        log.info(f"max error: {round(max_error, round_digits)}")

    if "mean_absolute_percentage_error" in metrics_config:
        value = metrics.mean_absolute_percentage_error(y_true, y_pred)
        result["mean_absolute_percentage_error"] = value
        log.info(f"mean absolute percentage error: {round(value, round_digits)}")

    if "r2_score" in metrics_config:
        r2 = metrics.r2_score(y_true, y_pred)
        result["r2"] = r2
        log.info(f"r2: {round(r2, round_digits)}")

    # View regression as classification
    if "kappa_score" in metrics_config:
        kappa = metrics.cohen_kappa_score(y_true.astype(np.int64), y_pred.astype(np.int64))
        result["kappa"] = kappa
        log.info(f"kappa: {round(kappa, round_digits)}")

    return result


def classification_results(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_score: np.ndarray,
    metrics_config: list,
    round_digits: int,
) -> dict[str, float | np.ndarray | str]:
    result: dict[str, float | np.ndarray] = {}
    # TODO we shouldn't mix data types in dict too much if we want to keep logging simple:
    # (metrics -> float, int, ndarray)

    if "accuracy" in metrics_config:
        # Regression metrics
        explained_variance = metrics.explained_variance_score(y_true, y_pred)
        result["accuracy"] = explained_variance
        log.info(f"accuracy: {round(explained_variance, round_digits)}")

    if "class_likelihood" in metrics_config:
        # Regression metrics
        class_likelihood = metrics.class_likelihood_ratios(y_true, y_pred)
        result["class_likelihood"] = class_likelihood
        log.info(f"class_likelihood: {round(class_likelihood, round_digits)}")

    if "classification_report" in metrics_config:
        classification_report = metrics.classification_report(y_true, y_pred)
        result["classification_report"] = classification_report
        log.info(f"classification_report: {classification_report}")

    if "confusion_matrix" in metrics_config:
        confusion_matrix = metrics.confusion_matrix(y_true, y_pred)
        result["confusion_matrix"] = confusion_matrix
        log.info(f"confusion_matrix: {confusion_matrix}")

    if "kappa" in metrics_config:
        kappa = metrics.cohen_kappa_score(y_true, y_pred)
        result["kappa"] = kappa
        log.info(f"kappa: {round(kappa, round_digits)}")

    if "f1_score" in metrics_config:
        f1_score = metrics.f1_score(y_true, y_pred, average="weighted")
        # TODO: check if wieghted gives back correct score so the it can be used in a Paper
        result["f1_score"] = f1_score
        log.info(f"f1_score: {round(f1_score, round_digits)}")

    if "hamming" in metrics_config:
        hamming = metrics.hamming_loss(y_true, y_pred)
        result["hamming"] = hamming
        log.info(f"hamming: {round(hamming, round_digits)}")

    if "hinge" in metrics_config:
        hinge = metrics.hinge_loss(y_true, y_pred)
        result["hinge"] = hinge
        log.info(f"hinge: {round(hinge, round_digits)}")

    if "jaccard" in metrics_config:
        jaccard = metrics.jaccard_score(y_true, y_pred)
        result["jaccard"] = jaccard
        log.info(f"jaccard: {round(jaccard, round_digits)}")

    if "log_loss" in metrics_config:
        log_loss = metrics.log_loss(y_true, y_pred)
        result["log_loss"] = log_loss
        log.info(f"log_loss: {round(log_loss, round_digits)}")

    if "precision" in metrics_config:
        precision = metrics.precision_score(y_true, y_pred)
        result["precision"] = precision
        log.info(f"precision: {round(precision, round_digits)}")

    if "recall" in metrics_config:
        recall = metrics.recall_score(y_true, y_pred)
        result["recall"] = recall
        log.info(f"recall: {round(recall, round_digits)}")

    return result
