import hashlib
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from omegaconf import DictConfig

from src.data import utils
from src.data.datamodule import DataModule
from src.data.mimic_iv import icu as icu_data
from src.utils import get_logger

log = get_logger(__name__)


@dataclass
class MimicDataModuleProps:
    path: str
    batch_size: int
    shuffle: bool
    save_loaded_data: bool
    load_preprocessed_data: bool
    force_rebuild: bool
    preprocessing: DictConfig


class MimicDataModule(DataModule):
    def __init__(self, props: MimicDataModuleProps) -> None:
        super().__init__()
        self.config = props

    def pipeline(self, data_type: str, feature_list: list[str], target: str) -> pd.DataFrame:
        """Loads or generates the feature dataframe.

        Args:
            name (str): defines the dataframe which should be generated
            feature_list (list[str]): the feature the Dataframe should contain
            target (str): the target variable

        Raises:
            ValueError: if the dataframe can't be generated

        Returns:
            pd.DataFrame: feature set
        """
        if data_type == "tabular":
            print("building MIMIC-IV tabular features")
            return self.get_tabular_data(feature_list, target)
            # I would not split here since the dataset may be re-used or
            # split by the model (e.g. when using CV)
        elif data_type == "timeseries":
            print("building MIMIC-IV timeseries features")
            return self.get_timeseries_data(target)
        else:
            raise ValueError(f"Unknown experiment name: {data_type}")

    # TODO: split up in seperate functions
    def get_tabular_data(self, feature_list: list[str], target: str) -> pd.DataFrame:
        """Generates a dataframe where every sample is a icu stay.

        Args:
            feature_list (list[str]): the feature the Dataframe should contain
            target (str): the target variable

        Returns:
            pd.DataFrame: feature set
        """
        base_path = Path(self.config.path)

        # get tabular featureset with chart- and labevents
        chartevents_tabular = icu_data.build_tabular_featureset(
            base_path=base_path,
            force_rebuild=self.config.force_rebuild,
            config=self.config.preprocessing,
        )

        target_df = self.get_target_variables(target)

        # check if the dataframe contains all columns which are used be the model
        missing_cols = set(feature_list) - set(chartevents_tabular.columns)
        if len(missing_cols) > 0:
            log.warning(f"Missing feature columns: {missing_cols}")

        not_used = set(chartevents_tabular.columns) - set(feature_list)
        # check if the dataframe contains columns which are not used be the model
        if len(not_used) > 0:
            log.warning(f"not used feature columns: {not_used}")

        # todo shouldn't this be generic?
        chartevents_with_icu_los = (
            target_df.merge(chartevents_tabular, left_on="stay_id", right_on="stay_id")
            # make sure that all feature and target columns are existing
            # also drop not used columns
            .reindex(columns=(feature_list + [target]))
        )
        log.info(f"Chartevents with ICU LOS shape: {chartevents_with_icu_los.shape}")
        log.debug(chartevents_with_icu_los.head())
        return chartevents_with_icu_los

    def get_windowed_data(self) -> pd.DataFrame:
        raise NotImplementedError()

    def get_timeseries_data(self, target: str) -> pd.DataFrame:
        """Generates a dataframe where every sample is a hour of an icu stay.

        Args:
            feature_list (list[str]): the feature the Dataframe should contain
            target (str): the target variable

        Returns:
            pd.DataFrame: feature set
        """
        base_path = Path(self.config.path)
        force_build = self.config.force_rebuild
        kwargs = {"config": self.config.preprocessing}

        confighash = hashlib.md5(str(self.config.preprocessing).encode()).hexdigest()

        timeseries = utils.load_or_build(
            base_path,
            f"icu_timeseries_features_*_{confighash}_*.feather",
            icu_data.build_timeseries_featureset,
            force_build,
            **kwargs,
        )
        # add the targetsvaribales to the feature dataset
        timeseries = self.add_timeseries_target_variables(target, timeseries)

        return timeseries

    def add_timeseries_target_variables(
        self, target: str, timeseries: pd.DataFrame
    ) -> pd.DataFrame:
        """Generates the target variables for a timeseries dataset.

        Args:
            target (str): target variable
            timeseries (pd.DataFrame): timeseries dataframe

        Raises:
            NotImplementedError: if the target variable is not defined

        Returns:
            pd.DataFrame: timeseries dataframe with the target variables added
        """
        kwargs = {"config": self.config.preprocessing}
        base_path = Path(self.config.path)

        confighash = hashlib.md5(str(self.config.preprocessing).encode()).hexdigest()

        dataframe = None
        icu_los_targets = ["icu_los", "icu_los_hour_int", "remaining_icu_los_hour"]
        if target in icu_los_targets:
            feature = ["subject_id", "hadm_id", "icu_stay_id", "icu_los"]
            # get data for icu los prediction
            target_df = (
                utils.load_or_build(
                    base_path,
                    f"icustays_*_{confighash}_*.feather",
                    icu_data.build_icu,
                    self.config.force_rebuild,
                    **kwargs,
                )[feature]
                .assign(stay_id=lambda x: x["icu_stay_id"].astype(int))
                .drop(columns=["icu_stay_id"])
                .assign(icu_los_hour_int=lambda df_: (df_["icu_los"] * 24).astype(int))
            )

            # calculate "Time in the ICU" from start
            timeseries["Time in the ICU"] = (
                pd.to_timedelta(
                    timeseries["abs_event_time"] - pd.Timestamp(0, unit="h")
                ).dt.total_seconds()
                / 3600
            )
            dataframe = (
                timeseries.merge(target_df, on="stay_id", how="inner")
                .assign(
                    remaining_icu_los_hour=lambda x: (x["icu_los_hour_int"]) - x["Time in the ICU"]
                )
                .drop(columns=["hadm_id"])
            ).set_index("subject_id")
        else:
            raise NotImplementedError("target not supported.")

        del timeseries
        return dataframe

    def get_target_variables(self, target: str) -> pd.DataFrame:
        """Generates the target variables for a tabular dataset.

        Args:
            target (str): defines target variable

        Raises:
            NotImplementedError: if the target variable is not defined

        Returns:
            pd.DataFrame: target variables
        """
        kwargs = {"config": self.config.preprocessing}
        base_path = Path(self.config.path)

        target_df = None
        icu_los_targets = ["icu_los", "icu_los_hour_int", "remaining_icu_los_hour"]
        if target in icu_los_targets:
            feature = ["subject_id", "hadm_id", "icu_stay_id", "icu_los"]
            cuf_off_time = self.config.preprocessing.cut_off_time
            # get data for icu los prediction
            target_df = (
                utils.load_or_build(
                    base_path,
                    "icustays_*.feather",
                    icu_data.build_icu,
                    self.config.force_rebuild,
                    **kwargs,
                )[feature]
                .assign(stay_id=lambda x: x["icu_stay_id"].astype(int))
                .drop(columns=["icu_stay_id"])
                .assign(icu_los_hour_int=lambda x: (x["icu_los"] * 24).round(0).astype(int))
                .assign(
                    remaining_icu_los_hour=lambda x: (x["icu_los_hour_int"] - cuf_off_time).clip(
                        0, None
                    )
                )
            )
        else:
            raise NotImplementedError(
                f"received target {target}. expected one of {icu_los_targets}"
            )

        return target_df
