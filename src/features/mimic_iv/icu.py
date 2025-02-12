import logging
from typing import Callable, Iterable, Tuple

import numpy as np
import pandas as pd

from src.data import utils as data_utils


def create_chartevent_agg_features(
    df: pd.DataFrame, aggfunc: str | Callable | Iterable[str | Callable] = "count"
) -> pd.DataFrame:
    data_utils.assert_feature_existence(df, ["stay_id", "label", "itemid"])
    if isinstance(aggfunc, (str, Callable)):
        pivot = pd.pivot_table(
            df, values="valuenum", index=["stay_id"], columns=["label"], aggfunc=aggfunc
        ).reset_index()
        pivot.columns.name = None
    else:
        pivot = pd.pivot_table(
            df, values="valuenum", index=["stay_id"], columns=["label"], aggfunc=aggfunc
        ).swaplevel(axis=1)  # swap (aggfunc, label) to (label, aggfunc)
        # flatten multiindex
        pivot.columns = pivot.columns.to_series().str.join("_")  # turn col to label_aggfunc
        # sort columns
        pivot = pivot.reindex(sorted(pivot.columns), axis=1)

        # reset index to have stay_id as column
        pivot = pivot.reset_index()

    if aggfunc == "count":
        # fill NaNs with 0
        pivot = pivot.fillna(0)
        # convert to int
        pivot = pivot.astype(int)
    else:
        # drop na rows ?
        # then there'll be nothing left...
        pass

    return pivot


def create_num_alarms_features(df: pd.DataFrame) -> pd.DataFrame:
    # TODO: add filter for alarms in the last X hours since given datetime
    df_filtered = df[df["category"] == "Alarms"]
    logging.info(f"Alarms data has shape {df_filtered.shape} after filtering")
    pivot = create_chartevent_agg_features(df_filtered, "count")
    pivot = pivot.astype(int)
    logging.info(f"Alarms data has shape {df_filtered.shape} after aggregation")
    return pivot


def filter_routine_vital_signs(df: pd.DataFrame) -> pd.DataFrame:
    df = df[df["category"] == "Routine Vital Signs"]

    feature_names_patterns = ["non invasive", "arterial", "heart rate", "temperature "]
    not_contain = ["Blood Temperature CCO (C)"]
    # only keep rows where label contains one of the patterns
    # first collect matching label values and then drop the rest
    feat_labels = df["label"].unique()
    feat_labels = [
        label
        for label in feat_labels
        if any(pattern in label.lower() for pattern in feature_names_patterns)
    ]
    feat_labels = [
        label for label in feat_labels if not any(pattern in label for pattern in not_contain)
    ]
    df = df[df["label"].isin(feat_labels)]

    # drop rows where valuenum is null or <= 0
    df = df[df["valuenum"].notnull()]
    df = df[df["valuenum"] > 0]
    # TODO drop unrealistic outliers

    # check that there are no Fahrenheit rows left
    logging.debug(
        f"Remaining Fahrenheit rows (should be 0):\
             {len(df[df['label'] == 'Temperature Fahrenheit'])}"
    )

    return df


def change_fahrenheit_to_celsius(df: pd.DataFrame) -> pd.DataFrame:
    # use numpy to convert fahrenheit entries to celsius
    # conversion with a numpy function is really fast because the uses vektors
    def fahrenheit_to_celsius(x):
        return round((x - 32) * 5 / 9, 1)

    # Make function compatible with vectors
    fahrenheit_to_celsius_v = np.vectorize(fahrenheit_to_celsius)

    # select entries which need to be converted
    temperatur_values = df[df["label"] == "Temperature Fahrenheit"].copy()
    # remove entries which have to be conveted
    df = df[df["label"] != "Temperature Fahrenheit"].copy()

    # convert the values to celsius
    temperatur_values["valuenum"] = fahrenheit_to_celsius_v(
        temperatur_values["valuenum"].to_numpy()
    )
    temperatur_values["itemid"] = 223762
    temperatur_values["valueuom"] = "°C"
    temperatur_values["label"] = "Temperature Celsius"

    df = pd.concat([df, temperatur_values])
    return df


def calculate_bmi_feature(df: pd.DataFrame) -> pd.DataFrame:
    weigth_and_height = df.reset_index(0)

    # TODO: Use other Height Columns later
    data_utils.assert_feature_existence(
        weigth_and_height, ["abs_event_time", "Daily Weight", "stay_id", "Height (cm)"]
    )
    weigth_and_height = weigth_and_height[
        ["abs_event_time", "stay_id", "Daily Weight", "Height (cm)"]
    ]
    weigth_and_height = weigth_and_height[
        (weigth_and_height["Daily Weight"] > 0.0) & (weigth_and_height["Height (cm)"] > 0.0)
    ]

    def calculate_bmi(x, y):
        return round(y / (x * x), 1)

    # Make function compatible with vectors
    calculate_bmi_v = np.vectorize(calculate_bmi)

    x = weigth_and_height["Height (cm)"].to_numpy() / 100
    y = weigth_and_height["Daily Weight"].to_numpy()

    # convert the values to celsius
    weigth_and_height["daily bmi"] = calculate_bmi_v(x, y)
    weigth_and_height.set_index("abs_event_time")

    df = df.merge(
        weigth_and_height[["abs_event_time", "stay_id", "daily bmi"]],
        on=["abs_event_time", "stay_id"],
        how="left",
    )
    return df


def create_routine_vital_signs_features(df: pd.DataFrame) -> pd.DataFrame:
    data_utils.assert_feature_existence(
        df, ["category", "stay_id", "label", "itemid", "valuenum", "valueuom"]
    )
    # keep only the columns we care about
    df_filtered = filter_routine_vital_signs(df)
    logging.info(f"Vital signs data has shape {df_filtered.shape} after filtering")
    pivot = create_chartevent_agg_features(df_filtered, ("mean", "min", "max", "std"))
    logging.info(f"Vital signs data has shape {pivot.shape} after aggregation")
    return pivot


def create_respiratory_features(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    df_filtered = df[df["category"] == "Respiratory"]
    df_filtered = df_filtered[
        df_filtered["label"].isin(config["timeseries_columns"]["respiratory"])
    ]
    pivot = create_chartevent_agg_features(df_filtered, ("mean", "min", "max", "std"))
    logging.info(f"Respiratory data has shape {pivot.shape} after aggregation")
    return pivot


def create_timeseries_features(
    df: pd.DataFrame,
    lag_periods: list[int] | None,
    window: str | int | Callable | list[int] | list[str],
    functions: str | list[str] = "mean",
):
    raise NotImplementedError("TODO")


def create_lag_features(
    df: pd.DataFrame,
    variables: int | str | list[str | int] | None = None,
    periods: int | list[int] = 1,
    freq: str | list[str] | None = None,
):
    raise NotImplementedError("TODO")


def create_resampled_features(df: pd.DataFrame, labels: list) -> pd.DataFrame:
    data_utils.assert_feature_existence(
        df, ["stay_id", "event_time_from_icu_intime", "label", "valuenum"]
    )

    # TODO maybe this would be better to do separately for each `stay_id`
    # to keep it computable on a single machine
    # create time series features
    df = (
        df[df["label"].isin(labels)]
        .assign(
            abs_event_time=lambda x: pd.Timestamp(0, unit="h") + x["event_time_from_icu_intime"]
        )  # add absolute event time column for easier pandas resampling operations
        .drop(columns=["event_time_from_icu_intime"])
        .pivot_table(  # convert long to wide
            index=["stay_id", "abs_event_time"],
            columns="label",
            values="valuenum",
        )
        .reset_index()  # put stay_id back into columns
        .rename_axis(None, axis=1)  # remove "label" axis name
        .set_index("abs_event_time")
        .sort_index(ascending=True)
        .groupby("stay_id")  # separately for each stay, resample to 1 hour intervals
        .resample(
            "1H", label="right", closed="right", origin="epoch"
        )  # from right to not take future information
        .mean()
        .drop(columns=["event_time_from_icu_intime", "stay_id"], errors="ignore")
        # Important only forward values with a icu stay
        .groupby(["stay_id"], group_keys=False)
        # forward fill missing values
        .apply(lambda x: x.ffill())
        .reset_index(0)
    )
    # TODO normalize (not clear where and how)

    return df


def calculate_timeseries_feature(df: pd.DataFrame, configuration: dict) -> pd.DataFrame:
    """This function calculates feature on the timeseries Dataset.

    Args:
        df (pd.DataFrame): the timeseries Dataset
        configuration (dict): the configuration of the feature engineering

    Returns:
        pd.DataFrame: the Dataframe with the additional features
    """
    df["Braden Score"] = 0
    for i in configuration["timeseries_columns"]["braden_fields"]:
        df["Braden Score"] += df[i]

    # drop columns which are only need for the calculation
    df = df.drop(columns=configuration["timeseries_columns"]["braden_fields"])
    # TODO: improve BMI calculate and evaluate
    # df = calculate_bmi_feature(df)
    # print(df.reset_index(0).columns)
    return df


def create_icu_chartevents_features(
    df: pd.DataFrame, config: dict, save_path: str | None = None
) -> Tuple[pd.DataFrame, dict[str, list[str]]]:
    logging.info("Creating features from ICU chartevents")
    column_dict = {}
    vital_signs = create_routine_vital_signs_features(df)
    column_dict["vital_signs"] = vital_signs.columns.to_list()
    logging.info("Created Routine Vital Signs features")

    alarms = create_num_alarms_features(df)
    column_dict["alarms"] = alarms.columns.to_list()
    logging.info("Created Alarms features")

    respiratory = create_respiratory_features(df, config)
    column_dict["respiratory"] = respiratory.columns.to_list()
    logging.info("Created Respiratory features")

    calculate_fields = calculate_chartevents_feature(df)
    column_dict["calculate_fields"] = calculate_fields.columns.to_list()
    logging.info("Calculate custom fields")

    labels = []
    labels.extend(config["timeseries_columns"]["pain_sedation"])
    labels.extend(config["timeseries_columns"]["pulmonary"])
    labels.extend(config["timeseries_columns"]["treatments"])
    labels.extend(config["timeseries_columns"]["labs"])
    labels.extend(["Strength R Arm", "Strength L Arm", "Strength R Leg", "Strength L Leg"])
    df_filtered = df[df["label"].isin(labels)]
    fields = create_chartevent_agg_features(df_filtered, list(config["aggregation_functions"]))
    logging.info("Created neurological, treatments, pain_sedation, labs, pulmonary features")

    # join all on stay_id
    features = (
        vital_signs.merge(alarms, on="stay_id", how="outer")
        .merge(respiratory, on="stay_id", how="outer")
        .merge(calculate_fields, on="stay_id", how="outer")
        .merge(fields, on="stay_id", how="outer")
    )
    logging.info(f"Total shape of ICU chartevents features: {features.shape}")
    if save_path is not None:
        data_utils.save_processed_dataframe(
            features, save_path, "icu_chartevents_features", "features"
        )

    return features, column_dict


def calculate_chartevents_feature(df: pd.DataFrame) -> pd.DataFrame:
    result: pd.DataFrame = df[["stay_id"]].drop_duplicates()

    def calculate_bmi(height, weight):
        return round(weight / (height * height), 1)

    # Make function compatible with vectors
    calculate_bmi_v = np.vectorize(calculate_bmi)

    # height_df = df[df["label"] == "Height (cm)"]
    feature_df = (
        df[df["label"].isin(["Daily Weight", "Height (cm)"])]
        .sort_values("charttime", ascending=[False])
        .drop_duplicates(["stay_id", "label"])
    )
    tmp = pd.pivot_table(
        feature_df, values="valuenum", index=["stay_id"], columns=["label"]
    ).reset_index()
    tmp = tmp[(tmp["Daily Weight"] > 0.0) & (tmp["Height (cm)"] > 0.0)]

    # calculate the bmi
    tmp["daily bmi"] = calculate_bmi_v(
        tmp["Height (cm)"].to_numpy() / 100, tmp["Daily Weight"].to_numpy()
    )
    result = result.merge(tmp[["stay_id", "daily bmi"]], on="stay_id", how="left")

    # calculate braden_score
    braden_df = df[df["label"].str.contains("Braden")]
    braden_df = braden_df.sort_values("charttime", ascending=[False]).drop_duplicates(
        ["stay_id", "label"]
    )
    tmp = pd.pivot_table(
        braden_df, values="valuenum", index=["stay_id"], columns=["label"]
    ).reset_index()

    tmp["Braden Score"] = (
        tmp["Braden Sensory Perception"]
        + tmp["Braden Moisture"]
        + tmp["Braden Activity"]
        + tmp["Braden Mobility"]
        + tmp["Braden Nutrition"]
        + tmp["Braden Friction/Shear"]
    )

    result = result.merge(tmp[["stay_id", "Braden Score"]], on="stay_id", how="left")
    gcs_fields = ["GCS - Eye Opening", "GCS - Motor Response", "GCS - Verbal Response"]

    gcs_df = df[df["label"].isin(gcs_fields)]
    gcs_df = gcs_df.sort_values("charttime", ascending=[False]).drop_duplicates(
        ["stay_id", "label"]
    )

    tmp = pd.pivot_table(
        gcs_df, values="valuenum", index=["stay_id"], columns=["label"]
    ).reset_index()

    tmp["GCS score"] = (
        tmp["GCS - Eye Opening"] + tmp["GCS - Motor Response"] + tmp["GCS - Verbal Response"]
    )
    result = result.merge(tmp[["stay_id", "GCS score"]], on="stay_id", how="left")

    return result


def create_common_icu_features(df: pd.DataFrame) -> list:
    # find features that are available that appear at least twice per stay
    data_utils.assert_feature_existence(df, ["stay_id", "itemid"])

    return (
        df.groupby("stay_id")["itemid"]
        .value_counts()
        .loc[lambda x: x >= 2]
        .index.get_level_values("itemid")
        .unique()
        .tolist()
    )


def drop_unavailable_columns_icu_classification(df: pd.DataFrame) -> pd.DataFrame:
    # TODO drop columns that are not available in real-life conditions
    # TODO these might be interesting to visualize (e.g. stay after x hours)
    # but cannot be used for modelling.
    return df.drop(
        columns=[
            "icu_stay_id",
            "first_careunit",
            "last_careunit",
            "subject_id",
            "hadm_id",
            "icu_los",
            "icu_stay_hours_after_surgery",
            "icu_intime",
            "icu_outtime",
            "total_los",
        ],
        errors="ignore",
    )


def drop_unavailable_columns_icu_los_prediction(df: pd.DataFrame) -> pd.DataFrame:
    # TODO drop columns that are not available in real-life conditions
    # TODO these might be interesting to visualize (e.g. stay after x hours)
    # but cannot be used for modelling.
    df = df.drop(
        columns=[
            "icu_stay_id",
            "first_careunit",
            "last_careunit",
            "subject_id",
            "hadm_id",
            "icu_los",
            "icu_outtime",
            "total_los",
            "stay_id",
            "icd_main",  # remove it for now, since there's not timestamp associated \
            # and we do not know when it was diagnosed
            "icd_main_3",
            "icd_chapter",
        ],
        errors="ignore",
    )
    # drop columns starting with "icu_stay_"
    df = df.loc[:, ~df.columns.str.startswith("icu_stay_")]
    return df


# TODO: LOS discretization


def clip_icu_los(df: pd.DataFrame, percentile=0.9):
    data_utils.assert_feature_existence(df, ["icu_los"])
    raise NotImplementedError("TODO")


# based on Rocheteau TPC paper flat_features.sql
# not used right now
def create_extra_vars_rocheteau(df: pd.DataFrame):
    raise NotImplementedError("TODO")
    # strange that she chose to use (kg) and (cm) as units,
    # since those columns are sparsely populated
    feat_labels = [
        "Admission Weight (Kg)",
        "GCS - Eye Opening",
        "GCS - Motor Response",
        "GCS - Verbal Response",
        "Height (cm)",
    ]
    # value_not_zero = df["valuenum"] > 0
    df_filtered = df.loc[df["label"].isin(feat_labels)].query("valuenum > 0")
    pivot = create_chartevent_agg_features(df_filtered, ("mean", "min", "max", "std"))
    pivot = pivot.astype(int)
    logging.info(f"Extra Vars data has shape {df_filtered.shape} after aggregation")
    return pivot


def create_lab_features_rocheteau(df: pd.DataFrame):
    raise NotImplementedError("TODO")


def create_icu_readmission_features(
    icu_df: pd.DataFrame, max_readmission_time: int
) -> pd.DataFrame:
    """Adds the readmission feature to the dataframe.

    Args:
        icu_df (pd.DataFrame): dataframe containing the icustays
        max_readmission_time (int, optional): The time in hours until a second stay in the ICU is
        no longer considered a readmission

    Returns:
        pd.DataFrame: dataframe which has additional flag for readmission
    """
    merged_df = icu_df.merge(
        icu_df[["subject_id", "stay_id", "intime"]], on=["subject_id"], how="left"
    )

    # Remove elements which are joined with them self
    merged_outer_df = merged_df[
        merged_df[["stay_id_x", "stay_id_y"]].apply(pd.Series.nunique, axis=1) == 2
    ]
    del merged_df

    # caclulate time to readminssion
    merged_outer_df["hours_until_readmission"] = (
        merged_outer_df["intime_y"] - merged_outer_df["outtime"]
    ) / pd.Timedelta(hours=1)
    merged_outer_df = merged_outer_df.drop(
        columns=[
            "last_careunit",
            "first_careunit",
            "subject_id",
            "hadm_id",
            "los",
            "intime_x",
            "outtime",
        ]
    )

    # Only keep readmission wíth positiv readmission time
    icu_with_readmission = merged_outer_df[
        merged_outer_df["hours_until_readmission"].between(0, max_readmission_time)
    ]

    del merged_outer_df

    # only keep earliest readmission for every ICU stay
    icu_with_readmission = (
        icu_with_readmission.sort_values("hours_until_readmission", ascending=True)
        .drop_duplicates(subset=["stay_id_x"], keep="first")
        .sort_values("intime_y", ascending=True)
        .drop(columns=["intime_y"])
    )

    icu_df = icu_df.merge(
        icu_with_readmission[["stay_id_x", "hours_until_readmission"]],
        left_on=["stay_id"],
        right_on=["stay_id_x"],
        how="left",
    )
    # set indecator that Patient will be readmitted after the ICU stay
    icu_df["will_be_readmitted"] = icu_df["stay_id_x"].notna().astype(bool)

    icu_with_readmission.rename(
        columns={"hours_until_readmission": "hours_to_readmission"}, inplace=True
    )
    icu_df = icu_df.merge(
        icu_with_readmission[["stay_id_y", "hours_to_readmission"]],
        left_on=["stay_id"],
        right_on=["stay_id_y"],
        how="left",
    )
    # set indicator that icu stay is readmission
    icu_df["stay_is_readmission"] = icu_df["stay_id_y"].notna().astype(bool)

    del icu_with_readmission

    icu_df.drop(columns=["stay_id_y", "stay_id_x"], inplace=True)

    return icu_df


def create_output_featuresd(output_events, config: dict) -> pd.DataFrame:
    features = pd.DataFrame()

    if cut_off := config.get("cut_off_time"):
        cut_off_time = pd.Timedelta(cut_off, unit="h")
        mintime = cut_off_time - pd.Timedelta(24, unit="h")
        output_events = output_events[(output_events["event_time_from_icu_intime"] >= mintime)]

    # values for mimic github
    urine_events_itemids = [
        226559,  # Foley
        226560,  # Void
        226561,  # Condom Cath
        226584,  # Ileoconduit
        226563,  # Suprapubic
        226564,  # R Nephrostomy
        226565,  # L Nephrostomy
        226567,  # Straight Cath
        226557,  # R Ureteral Stent
        226558,  # L Ureteral Stent
        227488,  # GU Irrigant Volume In
        227489,  # GU Irrigant/Urine Volume Out
    ]
    urine_events = output_events[output_events["itemid"].isin(urine_events_itemids)]

    # feature engenerging
    features = pd.pivot_table(
        urine_events,
        values="value",
        index=["stay_id"],
        aggfunc="sum",
    ).reset_index()

    features = features.rename(columns={"value": "urine_last_1d"})[["stay_id", "urine_last_1d"]]

    return features
