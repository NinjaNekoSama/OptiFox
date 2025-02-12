from typing import Any, Tuple

import hydra
import pandas as pd
from omegaconf import DictConfig
from pandas import DataFrame

from .data import utils as utils
from .data.datamodule import DataModule
from .models.evaluation import evaluate_model
from .utils import get_logger, seed_everything
from .utils.types import IcuBaseModel, TrainTestMetrics


log = get_logger(__name__)


def train_pipeline(cfg: DictConfig) -> TrainTestMetrics:
    dataset, model, logger = init(cfg)

    log.info("start training model")
    train_metrics, test_metrics = run_training_pipe(cfg, dataset, model, logger)

    log.info("finished training")

    return train_metrics, test_metrics


def resolve_config(cfg):
    log.info("Loaded Config:", cfg)

    # Set seed for random number generators in pytorch, numpy and python.random
    if cfg.get("seed"):
        seed_everything(cfg.seed)

    # initiate dataset specific DataModule Preprocessor
    log.info(f"Instantiating datamodule <{cfg.dataset.datamodule._target_}>")
    datamodule: DataModule = hydra.utils.instantiate(cfg.dataset.datamodule)

    log.info(f"Instantiating model <{cfg.model.model._target_}>")

    try:
        early_stopping = hydra.utils.instantiate(cfg.model.early_stopping)
        pl_trainer_kwargs = {"callbacks": [early_stopping]}
    except KeyError:
        pl_trainer_kwargs = None
        pass
    # BaseAuto instantiation does not accept the model config as DictConfig,
    # so ensure it is returned as a dict by _convert_='partial'.
    model = hydra.utils.instantiate(
        cfg.model.model, _convert_="partial", pl_trainer_kwargs=pl_trainer_kwargs
    )

    log.info("No logger has been initialized.")
    _logger = None
    return datamodule, model, _logger


def run_training_pipe(
    cfg: DictConfig,
    dataset: DataFrame,
    model: IcuBaseModel,
    logger: Any | None,
):
    print("dataset:")
    # first and last rows
    print(
        pd.concat(
            [
                dataset.iloc[:, :5],
                dataset.iloc[:, -10:],
            ],
            axis=1,
        )
        .head(10)
        .to_markdown()
    )
    train_metrics, test_metrics = fit_and_evaluate(cfg, dataset, model, logger)

    return train_metrics, test_metrics


def init(
    cfg: DictConfig,
) -> Tuple[DataFrame, IcuBaseModel, Any | None]:
    log.info("Loaded Config:", cfg)

    # Set seed for random number generators in pytorch, numpy and python.random
    if cfg.get("seed"):
        seed_everything(cfg.seed)

    # initiate dataset specific DataModule Preprocessor
    log.info(f"Instantiating datamodule <{cfg.dataset._target_}>")
    datamodule: DataModule = hydra.utils.instantiate(cfg.dataset)
    # TODO this should be done as part of the instantiation
    dataset: DataFrame = datamodule.pipeline(
        # TODO dataset name should not be tied to experiment name
        cfg.data_type,
        cfg.feature_list,
        cfg.target,
    )
    log.info(f"Instantiating model <{cfg.model._target_}>")
    model: IcuBaseModel = hydra.utils.instantiate(cfg.model)
    logger: Any | None = None
    log.info("No logger has been initialized.")
    return dataset, model, logger


def fit_and_evaluate(
    cfg: DictConfig,
    dataset: DataFrame,
    model: IcuBaseModel,
    logger: Any | None,
) -> TrainTestMetrics:
    train_set, test_set, val_set = utils.split_data(
        dataset, cfg.target, cfg.test_split, cfg.val_split, cfg.split
    )
    log.info(
        f"num features: {train_set[0].shape[1]}"
        f"\t|\ttrain size: {len(train_set[0])}\t|\t"
        f"val size: {len(val_set[0])}"
    )

    model.fit(*train_set)

    train_metrics = {}  # TODO
    log.info("finished training model")

    log.info("start evaluation")
    # TODO since we do not have a Trainer object connecting things,
    # we have to pass the model, data and logger around
    test_metrics = evaluate_model(model, *val_set, cfg.evaluation, logger=logger)
    # TODO we should use model.score instead, which is automatically tracked
    # by mlflow autolog
    return train_metrics, test_metrics
