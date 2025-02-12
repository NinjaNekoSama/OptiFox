import hashlib
import logging
import os
from pathlib import Path
from typing import Iterator
from omegaconf import DictConfig

import pandas as pd
from tqdm import tqdm

from src.data.mimic_iv.hosp import create_diagnose_features, create_scores_features
from src.data.utils import (
    assert_feature_existence,
    load_or_build,
    load_processed_dataframe,
    process_feather_chunks,
    save_pickle,
    save_processed_dataframe,
)
from src.features.mimic_iv import icu as features_icu


def build_or_load_chartevents(
    base_path: Path, force_rebuild: bool, config: DictConfig, **kwargs
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if force_rebuild:
        logging.info("Build charevents dataframes")
        column_dict, features = build_chartevents_chunked(base_path, config, **kwargs)
        chartevents_tabular, chartevents_timeseries = features[1], features[2]
        # Memory managment free memory of not used tables
        del column_dict, features
    else:
        confighash = hashlib.md5(str(config).encode()).hexdigest()
        logging.info("Load chartevents dataframes")
        tabular_filename = f"icu_chartevents_tabular_*_{confighash}_*.feather"
        timeseries_filename = f"icu_chartevents_timeseries_*_{confighash}_*.feather"
        try:
            chartevents_tabular = load_processed_dataframe(base_path, tabular_filename)
            chartevents_timeseries = load_processed_dataframe(base_path, timeseries_filename)
        except FileNotFoundError:
            # if the dataframe could not be loaded build it
            logging.info("Build chartevents dataframes")
            column_dict, features = build_chartevents_chunked(base_path, config, **kwargs)
            chartevents_tabular, chartevents_timeseries = features[1], features[2]
            # Memory managment free memory of not used tables
            del column_dict, features
    return chartevents_tabular, chartevents_timeseries


def build_chartevents_chunked(
    base_path: Path, config: DictConfig, **filter_kwargs
) -> tuple[dict[str, set[str]], list[pd.DataFrame]]:
    """Build chartevents from chunks and save them to disk.

    Args:
        base_path (Path): path to MIMIC-IV dir.
        save (bool, optional): if the processed data should be saved to feather file.\
              Defaults to True.
        detailed (bool, optional): joins item descriptions. Defaults to True.
        **filter_kwargs: keyword arguments to early-filter the data. \
            See get_chartevents_chunk for details.
    """
    # do loop where the chunked chartevents are saved to disk and ram is cleared inbetween.
    # then load all the chunks and concat them.
    # there are about 320M rows in total, but the kernel crashes \
    # if we try to load (and save) them all at once.
    icu_stays = filter_kwargs.get("icu_stays", None)
    cut_off_time = pd.Timedelta(config["cut_off_time"], unit="h")
    save = config["save_processed_dfs"]
    kwargs = {"config": config}

    if icu_stays is None:
        icu_stays_patient_info_df = (
            load_or_build(
                base_path, "icustays_*.feather", build_icu, force_rebuild=False, **kwargs
            )
            .assign(stay_id=lambda x: x["icu_stay_id"].astype(int))
            .drop(columns=["icu_stay_id"])
        )
    else:
        icu_stays_patient_info_df = icu_stays

    # TODO remove magic numbers
    chunksize = 10_000_000
    logging.info(f"Reading chartevents in chunks of {chunksize} (of about 320M).")

    # Load the description for the chartevents
    d_items = build_d_items(base_path).loc[:, ["itemid", "label", "category"]]
    logging.info("Built d_items dataframe.")

    chartevent_generator = get_chartevents_chunk(
        icu_stays_patient_info_df,
        "icu_intime",
        base_path,
        chunksize=chunksize,
        item_details=d_items,
        cut_off_time=cut_off_time,
    )
    num_chunks = 0
    total_rows = 320_000_000  # file size estimate
    fn_prefixes = {
        "base": "chartevents",
        "tabular": "chartevents_tabular",
        "timeseries": "chartevents_timeseries",
    }

    column_dict, labels = {}, []
    for i in config["timeseries_columns"]:
        labels.extend(config["timeseries_columns"][i])

    # iterate over generator, reading CSV in chunks and saving them to disk
    for i, chartevent_chunk in tqdm(
        enumerate(chartevent_generator), total=total_rows // chunksize
    ):
        chartevent_chunk = features_icu.change_fahrenheit_to_celsius(chartevent_chunk)
        # save "raw" chunk to disk
        save_processed_dataframe(chartevent_chunk, base_path, f"{fn_prefixes['base']}_chunk_{i}")

        # create tabular features here already
        (
            tabular_chunk_features,
            column_category_mapping,
        ) = features_icu.create_icu_chartevents_features(chartevent_chunk, config, save_path=None)

        # add new column names to category<->column-list mapping, only if not present
        for col_group, cols in column_category_mapping.items():
            col_set = set(column_dict.get(col_group, []))
            col_set.update(cols)
            col_set.discard("stay_id")
            column_dict[col_group] = col_set

        save_processed_dataframe(
            tabular_chunk_features, base_path, f"{fn_prefixes['tabular']}_chunk_{i}"
        )
        del tabular_chunk_features

        # create timeseries features
        ts_chunk_features = features_icu.create_resampled_features(chartevent_chunk, labels=labels)
        ts_chunk_features = features_icu.calculate_timeseries_feature(ts_chunk_features, config)
        # feather does not support custom indices so move it to a column
        ts_chunk_features = ts_chunk_features.reset_index().rename(
            columns={"index": "abs_event_time"}
        )
        save_processed_dataframe(
            ts_chunk_features, base_path, f"{fn_prefixes['timeseries']}_chunk_{i}"
        )
        del ts_chunk_features, chartevent_chunk
        num_chunks += 1

    # free up memory
    del chartevent_generator, icu_stays_patient_info_df, d_items

    logging.info(f"Saved {num_chunks} chartevents chunks to disk.")
    # save column dict to pickle
    save_pickle(column_dict, base_path, "chartevents_column_dict")
    logging.info("Saved column dict to disk.")

    # now, load all the chunks and concat them
    processed_dir = base_path.parent.parent / "processed"
    # find the latest date the chunks were saved in case multiple files still exist in directory
    fn_0_regex = f"{fn_prefixes['base']}_chunk_0_*.feather"
    latest_fn = sorted(processed_dir.glob(fn_0_regex))[-1]
    # extract date from filename
    date = latest_fn.name.split("_")[-1].split(".")[0]

    data = {}
    # for all chunk types: load each into single dataframe and save to disk, then delete chunks
    for key, fn_prefix in fn_prefixes.items():
        fn_regex = f"{fn_prefix}_chunk_*_{date}.feather"
        # iterate over the list of chunks and load them into a single dataframe
        df = process_feather_chunks(processed_dir, fn_regex, num_chunks)
        data[key] = df

        if save:
            # this is the complete chartevents dataframe
            save_processed_dataframe(df, base_path, f"icu_{fn_prefix}", config, True)

        # now, let's delete the chunks from disk
        for chunk_path in processed_dir.glob(fn_regex):
            os.remove(chunk_path)
        logging.info(f"Deleted {key} chartevents chunks from disk.")

    return column_dict, [data["base"], data["tabular"], data["timeseries"]]


def get_chartevents_chunk(
    icu_stays_df: pd.DataFrame,
    in_time_col: str,
    base_path: Path,
    chunksize: int = 10_000_000,
    limit_rows: int | None = None,
    filter_itemids: list[int] | None = None,
    filter_categories: list[str] | None = None,
    item_details: pd.DataFrame | None = None,
    cut_off_time: pd.Timedelta | None = None,
    # out_time_col: str = "outtime",
) -> Iterator[pd.DataFrame]:
    assert_feature_existence(icu_stays_df, ["stay_id", in_time_col])

    icu_dir = base_path / "icu"
    fn = icu_dir / "chartevents.csv.gz"

    # we do not need subject_id and hadm_id, since once we join with e.g. icustays\
    #  we can get them from there
    # we also only use numerical values for now and ignore warnings.
    for chunk in pd.read_csv(
        fn,
        usecols=["stay_id", "charttime", "itemid", "valuenum", "valueuom", "value"],
        parse_dates=["charttime"],
        dtype={"valueuom": "string", "stay_id": "int", "itemid": "int"},
        compression="gzip",
        nrows=limit_rows,
        chunksize=chunksize,
    ):
        # chunk: pd.DataFrame = chunk.dropna(subset=["valuenum"])
        if filter_itemids is not None:
            chunk = chunk[chunk["itemid"].isin(filter_itemids)]

        if item_details is not None:
            chunk = chunk.merge(item_details, how="left", on="itemid")
            if filter_categories is not None:
                chunk = chunk[chunk["category"].isin(filter_categories)]
        # TODO do some more filtering and validation here.
        # match patient infos on stay_id
        # change code below to use df pipe
        chunk = (
            chunk.merge(
                icu_stays_df[["stay_id", in_time_col]],
                how="inner",
                left_on="stay_id",
                right_on="stay_id",
            )
            .assign(
                **{f"event_time_from_{in_time_col}": lambda df: df["charttime"] - df[in_time_col]}
            )
            .assign(
                abs_event_time=lambda df: pd.Timestamp(0, unit="h")
                + df[f"event_time_from_{in_time_col}"]
            )  # add absolute event time column for easier pandas resampling operations
            # filter where abs_event_time < pd.Timestamp(0)
            .pipe(lambda df: df[df["abs_event_time"] >= pd.Timestamp(0, unit="h")])
        )
        if cut_off_time is not None:
            chunk = chunk[chunk[f"event_time_from_{in_time_col}"] <= cut_off_time]
        # # filter where charttime is after icu_outtime
        # chunk_merged = chunk_merged[
        #     chunk_merged["charttime"] <= chunk_merged["icu_outtime"]
        # ]
        chunk = chunk.drop(columns=[in_time_col]).drop_duplicates()

        yield chunk


def get_labevents_for_icu(
    icu_stays_df: pd.DataFrame,
    save: bool,
    in_time_col: str,
    base_path: Path,
    config: dict,
    **kwargs,
) -> pd.DataFrame:
    assert_feature_existence(icu_stays_df, ["stay_id", in_time_col])
    logging.info("Build labevents timeseries dataframe")

    hosp_dir = base_path / "hosp"
    items = pd.read_csv(hosp_dir / "d_labitems.csv.gz", usecols=["itemid", "label"])

    feature_names = config["lab_features"]
    # Get itemIds for the used features
    ids = items[items["label"].isin(feature_names)]["itemid"].unique().tolist()

    result = pd.DataFrame()
    # use junks to reduce needed Memory
    for chunk in pd.read_csv(
        hosp_dir / "labevents.csv.gz",
        usecols=["hadm_id", "itemid", "storetime", "valuenum"],
        parse_dates=["storetime"],
        compression="gzip",
        chunksize=10_000_000,
    ):
        chunk: pd.DataFrame = chunk.dropna(subset=["valuenum", "hadm_id"])
        # Remove labevents with no associated icu stay
        # Remove labitems which aren't needed
        chunk = chunk[(chunk["hadm_id"].isin(icu_stays_df["hadm_id"])) & chunk["itemid"].isin(ids)]

        chunk = (
            chunk.merge(items, how="inner", on="itemid")
            .merge(
                icu_stays_df[["hadm_id", "stay_id", in_time_col]],
                how="inner",
                on="hadm_id",
            )
            .assign(
                **{f"event_time_from_{in_time_col}": lambda df: df["storetime"] - df[in_time_col]}
            )
            .assign(
                abs_event_time=lambda df: pd.Timestamp(0, unit="h")
                + df[f"event_time_from_{in_time_col}"]
            )  # add absolute event time column for easier pandas resampling operations
            # filter where abs_event_time < pd.Timestamp(0)
            .pipe(lambda df: df[df["abs_event_time"] >= pd.Timestamp(0, unit="h")])
            .drop(columns=[in_time_col])
            .drop_duplicates()
        )
        # only use data to given time
        if cut_off := config.get("cut_off_time"):
            cut_off_time = pd.Timedelta(cut_off, unit="h")
            chunk = chunk[chunk[f"event_time_from_{in_time_col}"] <= cut_off_time]

        result = pd.concat([result, chunk])

    if save:
        # save the processed labevents dataframe
        save_processed_dataframe(result, base_path, "icu_labevents", config, True)

    return result


def get_outputevents(
    icu_stays_df: pd.DataFrame,
    save: bool,
    in_time_col: str,
    base_path: Path,
    config: dict,
    **kwargs,
) -> pd.DataFrame:
    # load events and add detail information
    items = pd.read_csv(base_path / "icu" / "d_items.csv.gz")
    # TODO validate if charttime or storetime ist better and
    # how big the timespane between them is
    outputevents = pd.read_csv(
        base_path / "icu" / "outputevents.csv.gz", parse_dates=["charttime"]
    )
    outputevents = outputevents.merge(items, on="itemid", how="left")

    outputevents = (
        outputevents.merge(
            icu_stays_df[["stay_id", in_time_col]],
            how="inner",
            left_on="stay_id",
            right_on="stay_id",
        )
        .assign(**{f"event_time_from_{in_time_col}": lambda df: df["charttime"] - df[in_time_col]})
        .assign(
            abs_event_time=lambda df: pd.Timestamp(0, unit="h")
            + df[f"event_time_from_{in_time_col}"]
        )  # add absolute event time column for easier pandas resampling operations
        # filter where abs_event_time < pd.Timestamp(0)
        .pipe(lambda df: df[df["abs_event_time"] >= pd.Timestamp(0, unit="h")])
    )

    # only use data to given time
    # so that we free memory which we don't neeed
    if cut_off := config.get("cut_off_time"):
        cut_off_time = pd.Timedelta(cut_off, unit="h")
        outputevents = outputevents[outputevents[f"event_time_from_{in_time_col}"] <= cut_off_time]

    processed_df = features_icu.create_output_featuresd(outputevents, config)
    del outputevents

    if save:
        # save the processed labevents dataframe
        save_processed_dataframe(processed_df, base_path, "icu_outputevents", config, True)

    return processed_df


def build_tabular_featureset(
    base_path: Path, force_rebuild: bool, config: DictConfig
) -> pd.DataFrame:
    # load icu stays for processing
    kwargs = {
        "save": True,
    }

    chartevents_tabular, chartevents_timeseries = build_or_load_chartevents(
        base_path=base_path, force_rebuild=force_rebuild, config=config, kwargs=kwargs
    )
    del chartevents_timeseries

    icu_stays_df = (
        load_or_build(base_path, "icustays_*.feather", build_icu, force_rebuild, **kwargs)
        .assign(stay_id=lambda x: x["icu_stay_id"].astype(int))
        .drop(columns=["icu_stay_id"])
    )

    confighash = hashlib.md5(str(config).encode()).hexdigest()
    # load the labevents which are used to create the timeseries featureset
    kwargs = {
        "icu_stays_df": icu_stays_df,
        "save": True,
        "in_time_col": "icu_intime",
        "config": config,
    }
    lab_events_df = load_or_build(
        base_path,
        f"icu_labevents_*_{confighash}_*.feather",
        get_labevents_for_icu,
        force_rebuild,
        **kwargs,
    )

    # convert list of events to Tabular featureset
    labevents_tabular = features_icu.create_chartevent_agg_features(
        lab_events_df, list(config["aggregation_functions"])
    )

    outputevents_df = load_or_build(
        base_path,
        f"icu_outputevents_*_{confighash}_*.feather",
        get_outputevents,
        force_rebuild,
        **kwargs,
    )
    scores_df = create_scores_features(base_path)
    diagnoses_df = create_diagnose_features(base_path)

    # merge chartevents with labevents
    tabular_features = (
        icu_stays_df[["hadm_id", "subject_id", "stay_id"]]
        .merge(chartevents_tabular, how="left", on="stay_id")
        .merge(labevents_tabular, how="left", on="stay_id")
        .merge(outputevents_df, how="left", on="stay_id")
        .merge(scores_df, how="left", on=["hadm_id", "subject_id"])
        .merge(diagnoses_df, how="left", on=["hadm_id", "subject_id"])
    )

    del chartevents_tabular, labevents_tabular, outputevents_df
    del scores_df, diagnoses_df
    # save processed dataframe
    save_processed_dataframe(tabular_features, base_path, "icu_tabular_features", config, True)

    return tabular_features


def build_timeseries_featureset(
    base_path: Path, force_rebuild: bool, **arg_kwargs
) -> pd.DataFrame:
    config = arg_kwargs.pop("config", None)

    # Get the processed timeseries dataframe for the chartevents
    chartevents_tabular, chartevents_ts = build_or_load_chartevents(
        base_path, force_rebuild, config, **arg_kwargs
    )
    del chartevents_tabular

    # load icu stays for processing
    kwargs = {"save": True, "config": config}
    icu_stays_df = (
        load_or_build(base_path, "icustays_*.feather", build_icu, force_rebuild, **kwargs)
        .assign(stay_id=lambda x: x["icu_stay_id"].astype(int))
        .drop(columns=["icu_stay_id"])
    )

    confighash = hashlib.md5(str(config).encode()).hexdigest()
    # load the labevents which are used to create the timeseries featureset
    kwargs = {
        "icu_stays_df": icu_stays_df,
        "save": True,
        "in_time_col": "icu_intime",
        "config": config,
    }
    labevents_df = load_or_build(
        base_path,
        f"icu_labevents_*_{confighash}_*.feather",
        get_labevents_for_icu,
        force_rebuild,
        **kwargs,
    )

    # Convert single entry table to timeseries table
    # Work exactly like conversion for chartevents
    logging.info("Create labevents timeseries dataframe")
    labevents_ts = features_icu.create_resampled_features(
        labevents_df, labels=config["lab_features"]
    )

    # Merge labevent and chartevent timeseries to get a timeseries with both features
    timeseries_features = chartevents_ts.merge(
        labevents_ts, how="left", on=["stay_id", "abs_event_time"]
    )

    # this is the timeseries labevents dataframe
    save_processed_dataframe(labevents_ts, base_path, "icu_timeseries_labevents", config, True)

    # this is the complete timeseries dataframe with all the feature from chatevents and labevents
    save_processed_dataframe(
        timeseries_features, base_path, "icu_timeseries_features", config, True
    )
    del labevents_ts, labevents_df

    return timeseries_features


def filter_and_clean_icu_stays(df: pd.DataFrame):
    df = (
        df.rename(
            columns={
                "intime": "icu_intime",
                "outtime": "icu_outtime",
                "los": "icu_los",
                "stay_id": "icu_stay_id",
            }
        )
        .drop(columns=["last_careunit"])
        .astype({"icu_stay_id": str})
    )

    # TODO check for duplicate entries in icu stays close to each other

    # TODO: Check if this code is still needed
    dups = (
        df.loc[:, ["subject_id", "hadm_id"]]
        .groupby(["subject_id", "hadm_id"])
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
        .query("count > 1")
        .__len__()
        / df.__len__()
    )
    logging.info(f"percentage of admissions with multiple ICU stays:\t\t{dups:.2%}")

    # clip values to 95th percentile of ICU LOS to remove outliers
    len_before = len(df)
    df = df[df["icu_los"] <= df["icu_los"].quantile(0.95)]
    delta_perc = 1 - (len(df) / len_before)
    logging.info(f"Clipped LOS to 95th percentile. Removed {delta_perc:%} of rows")
    return df


# TODO split getting data - pre-processing - feature engineering - saving data


def validate_icu_stays(df: pd.DataFrame):
    logging.info("Validating ICU stays.")
    logging.warning("Not Implemented yet.")
    # TODO: check missing values, make sure percentage is at least low enough.
    return True


def build_icu(base_path: Path, **kwargs):
    icu_dir = base_path / "icu"
    fn = icu_dir / "icustays.csv.gz"
    icu_stays = pd.read_csv(
        fn,
        dtype={"first_careunit": "category", "last_careunit": "category"},
        parse_dates=["intime", "outtime"],
        compression="gzip",
    )
    # TODO this default value will raise exception
    configuration = kwargs.get("config", None)
    # TODO validate input data
    icu_stays = features_icu.create_icu_readmission_features(
        icu_stays, configuration["readmission"]["max_readmission_time"]
    )
    icu_stays = filter_and_clean_icu_stays(icu_stays)
    # TODO validate data
    validate_icu_stays(icu_stays)
    logging.info(f"Read {fn}.\nICU stays:\t\t{icu_stays.shape}")

    save_processed_dataframe(icu_stays, base_path, "icustays")

    return icu_stays


def build_d_items(base_path: Path):
    icu_dir = base_path / "icu"
    fn = icu_dir / "d_items.csv.gz"
    d_items = pd.read_csv(
        fn,
        dtype={
            "label": "string",
            "abbreviation": "string",
            "linksto": "category",
            "unitname": "category",
            "category": "category",
            "param_type": "category",
            "lownormalvalue": "float",
            "highnormalvalue": "float",
        },
        compression="gzip",
    )
    # there's not much more to do here before joining with other tables.
    logging.info(f"Read {fn}.\nD_ITEMS:\t\t{d_items.shape}")
    # also no reason in saving the dataframe
    return d_items
