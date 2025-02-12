import hashlib
import json
import logging
import os
import pickle
from pathlib import Path
from typing import Any, List, Callable, Optional

import pandas as pd
from sklearn.model_selection import train_test_split
from tqdm import tqdm
import numpy as np


def split_train_test(dataset: pd.DataFrame, ratio_or_start: float | str):
    assert_feature_existence(dataset, ["ds"])
    if isinstance(ratio_or_start, str):
        # assuming timestamp
        test_date = pd.Timestamp(ratio_or_start)
        print(f"debug: received test split start fixed date: {test_date}")
    else:
        n_usable_steps = dataset.ds.nunique()
        usable_step_idx = np.arange(n_usable_steps)
        test_size = round(n_usable_steps * ratio_or_start)
        test_start = np.sort(usable_step_idx)[-test_size]
        test_date = dataset.iloc[test_start]["ds"].floor("d")

    # no gap, no Lookback or Horizon consideration, NF *should* take care of all that.
    train = dataset[dataset.ds < test_date].copy()
    test = dataset[dataset.ds >= test_date].copy()
    return train, test


def find_last_modified_file(path: Path, pattern: str) -> Path:
    data_files = sorted(
        list(path.glob(pattern)),
        key=os.path.getmtime,
        reverse=True,
    )
    if len(data_files) > 0:
        return data_files[0]
    else:
        raise FileNotFoundError(f"no file found in {path} matching pattern {pattern}")


def process_feather_chunks(processed_dir: Path, fn_regex: str, num_chunks: int):
    # loop over the saved chunks and concat them into a single dataframe
    chunk_list = []
    # find the latest date the chunks were saved in case multiple files still exist in directory

    for i, chunk_path in tqdm(
        enumerate(sorted(processed_dir.glob(fn_regex))),
        desc=f"Loading {fn_regex} chunks from feather files.",
        total=num_chunks,
    ):
        if i > num_chunks:
            # this is the empirical limit of how many chunks we can load \
            # into memory on my machine.
            break
        chunk = pd.read_feather(chunk_path, use_threads=True)
        chunk_list.append(chunk)
    df = pd.concat(chunk_list)
    del chunk_list
    logging.info(
        f"Finished building table from chunks.\
            \n Shape: \t\t{df.shape}"
    )
    return df


def assert_feature_existence(df: pd.DataFrame | pd.Series, col_names: list[str]):
    for col in col_names:
        if isinstance(df, pd.DataFrame):
            assert col in df.columns, f"Column '{col}' not found. Given: {df.columns}"
        elif isinstance(df, pd.Series):
            assert col in df.index, f"Series Index '{col}' not found. Given: {df.index}"
        else:
            raise TypeError(f"Received '{type(df)}'. Expected pandas DataFrame or Series.")


def save_processed_dataframe(
    df: pd.DataFrame,
    base_path: Path,
    name: str,
    config: dict | None = None,
    add_file_ending: bool = False,
    subdir: str | None = None,
):
    processed_dir = base_path.parent.parent / "processed"
    if subdir is not None:
        processed_dir = processed_dir / subdir

    filename = name
    # Add additional identifiers to the file ending
    if add_file_ending:
        length = len(df) // 1_000_000
        # get a unique hash reflecting the configuration values
        confighash = hashlib.md5((str(config).encode())).hexdigest()
        filename = filename + f"_{length}M_{confighash}"

    processed_dir.mkdir(parents=True, exist_ok=True)
    save_feather(df, processed_dir, filename)


# TODO make this wrapper
def load_or_build(
    base_path: Path,
    name: str,
    func: Callable,
    force_rebuild: bool,
    subdir: Optional[str | None] = None,
    **kwargs,
) -> Any:
    """Tries to load processed feather file, if not found or force_rebuild is True, will call
    func(base_path, **kwargs) instead.

    Args:
        base_path (Path): data directory
        name (str): name or regex of the dataframe to load or build
        func (Callable): builder function callable. Must accept kwargs
        force_rebuild (bool): if True, calls func
        subdir (str | None, optional): subdir of base_path to look for name. Defaults to None.

    Returns:
        Any: return type of `func`. usually one or more pandas dataframes
    """

    kwargs["force_rebuild"] = force_rebuild

    logging.info(f"trying to load or build `{name}` dataframe")
    if force_rebuild:
        logging.info("Build dataframe")
        ret = func(base_path=base_path, **kwargs)
    else:
        try:
            ret = load_processed_dataframe(base_path, name, subdir)
        except FileNotFoundError:
            logging.info("dataframe not found -> rebuilding")
            ret = func(base_path=base_path, **kwargs)
    return ret


def save_json(data: dict, base_path: Path, name: str, subdir: str | None = None):
    processed_dir = base_path
    if subdir is not None:
        processed_dir = processed_dir / subdir
    processed_dir.mkdir(parents=True, exist_ok=True)
    curr_date = pd.Timestamp.now().strftime("%Y%m%d")
    new_filename = (processed_dir / f"{name}_{curr_date}").with_suffix(".json")
    with open(new_filename, "w") as f:
        json.dump(data, f)
    logging.info(f"Saved to {new_filename}")


def save_yaml(data: dict, base_path: Path, name: str, subdir: str | None = None):
    import yaml

    if subdir is not None:
        out_dir = base_path / subdir
    else:
        out_dir = base_path
    out_dir.mkdir(parents=True, exist_ok=True)
    curr_date = pd.Timestamp.now().strftime("%Y%m%d")
    new_filename = (out_dir / f"{name}_{curr_date}").with_suffix(".yaml")
    with open(new_filename, "w") as yaml_file:
        yaml.dump(data, yaml_file, default_flow_style=False)
    logging.info(f"Saved to {new_filename}")


def save_csv(data: pd.DataFrame, base_path: Path, name: str, subdir: str | None = None):
    if subdir is not None:
        out_dir = base_path / subdir
    else:
        out_dir = base_path
    out_dir.mkdir(parents=True, exist_ok=True)
    curr_date = pd.Timestamp.now().strftime("%Y%m%d")
    new_filename = (out_dir / f"{name}_{curr_date}").with_suffix(".csv")
    data.to_csv(new_filename)
    logging.info(f"Saved to {new_filename}")


def save_pickle(data: dict, base_path: Path, name: str, subdir: str | None = None):
    processed_dir = base_path.parent.parent / "processed"
    if subdir is not None:
        processed_dir = processed_dir / subdir
    processed_dir.mkdir(parents=True, exist_ok=True)
    curr_date = pd.Timestamp.now().strftime("%Y%m%d")
    new_filename = (processed_dir / f"{name}_{curr_date}").with_suffix(".pkl")
    pickle.dump(data, open(new_filename, "wb"))
    logging.info(f"Saved to {new_filename}")


def save_model_pickle(model: Any, processed_dir: Path, name: str, subdir: str | None = None):
    processed_dir = processed_dir
    if subdir is not None:
        processed_dir = processed_dir / subdir
    processed_dir.mkdir(parents=True, exist_ok=True)
    new_filename = (processed_dir / f"{name}").with_suffix(".pkl")
    pickle.dump(model, open(new_filename, "wb"))
    logging.info(f"Saved to {new_filename}")


def load_processed_dataframe(
    base_path: Path, name: str, subdir: str | None = None
) -> pd.DataFrame:
    logging.info(f"Load Dataframe {name}")
    processed_dir = base_path.parent.parent / "processed"
    if subdir is not None:
        processed_dir = processed_dir / subdir
    processed_dir.mkdir(parents=True, exist_ok=True)

    try:
        latest_file = find_last_modified_file(processed_dir, name)
        df = pd.read_feather(latest_file)
        return df
    except FileNotFoundError:
        raise


def save_feather(df: pd.DataFrame, path: Path, name: str):
    curr_date = pd.Timestamp.now().strftime("%Y%m%d")
    new_filename = path / f"{name}_{curr_date}"

    # we do not need the custom index, and feather does not support it.
    df.reset_index(drop=True, inplace=True)
    df.to_feather(new_filename.with_suffix(".feather"))
    logging.info(f"Saved to {new_filename}.feather")


def split_data(
    df: pd.DataFrame,
    target: str,
    test_size: float,
    validation_size: float | None = None,
    split_by: str | None = None,
    random_state=123,
    stratify=False,
) -> tuple[tuple[pd.DataFrame, pd.DataFrame], ...]:
    """Split data into train, validation and test sets."""

    def split_df(df: pd.DataFrame, ids: List[str | int | float], id_field: str, target: str):
        """Selects the subset from the complet dataset and splits it by input and target features.

        Args:
            df (pd.DataFrame): Datafram with all elements
            ids (pd.Series): ids to select
            id_field (str): id field in dataframe
            target (str): target dataframe

        Returns:
            X_set (pd.DataFrame): input values
            y_set (pd.DataFrame): target values
        """
        # select the subset
        sub_set = df[df[id_field].isin(ids)]
        # split into input and target feature sets
        X_set, y_set = sub_set.drop(columns=[target]), sub_set[target]
        return (X_set, y_set)

    # Split dataframe by a spefic column
    if split_by is not None:
        # get the values with which the split is performed
        ids = df[split_by].unique()
        # split the ids in train & test ids
        train, test = train_test_split(ids, test_size=test_size, random_state=random_state)
        val = []
        if validation_size is not None:
            # split the train_ids in train & validation ids
            train, val = train_test_split(
                train, test_size=validation_size, random_state=random_state
            )

        train = split_df(df, train, split_by, target)
        test = split_df(df, test, split_by, target)
        # is emtpy if no validation_size was given
        val = split_df(df, val, split_by, target)
        if validation_size is not None:
            return (train, test, val)
        else:
            return (train, test)

    X = df.drop(columns=target)
    y = df[target]

    # test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y if stratify else None
    )
    if validation_size is not None:
        # validation split
        X_train, X_val, y_train, y_val = train_test_split(
            X_train,
            y_train,
            test_size=validation_size,
            random_state=random_state,
            stratify=y_train if stratify else None,
        )
        return (X_train, y_train), (X_test, y_test), (X_val, y_val)
    else:
        return (X_train, y_train), (X_test, y_test)
