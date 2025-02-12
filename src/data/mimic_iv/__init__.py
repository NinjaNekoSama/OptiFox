import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Callable

import pandas as pd

from src.data.mimic_iv.hosp import (
    build_admissions,
    build_drg,
    build_hospitalizations,
    build_icd_diagnoses,
    build_omr,
    build_patients,
    build_surgeries,
)
from src.data.mimic_iv.icu import build_chartevents_chunked, build_icu
from src.data.utils import find_last_modified_file

DATA_BUILDERS: dict[str, Callable] = {
    "admissions": build_admissions,
    "patients": build_patients,
    "drg": build_drg,
    "icd_diagnoses": build_icd_diagnoses,
    "hospitalizations": build_hospitalizations,
    "surgeries": build_surgeries,
    "omr": build_omr,
    "icustays": build_icu,
    "icu_chartevents_tabular": build_chartevents_chunked,
}


def build_or_load(
    base_data_path: Path,
    processed_data_path: Path,
    data_name: str,
    save: bool,
    data_max_age: datetime,
    force_build=False,
    **kwargs,
) -> pd.DataFrame | tuple[dict[str, set[str]], list[pd.DataFrame]]:
    # check if an existing file exists
    # if not, build it
    # if yes, check if it is recent enough
    # if yes, load it
    # if no, build it

    def build_dataset(
        data_name, save, **kwargs
    ) -> pd.DataFrame | tuple[dict[str, set[str]], list[pd.DataFrame]]:
        try:
            return DATA_BUILDERS[data_name](base_path=base_data_path, save=save, **kwargs)
        except KeyError as e:
            logging.error(e)
            raise NotImplementedError(f"Could not build {data_name}, function not implemented.")
        except Exception as e:
            logging.exception(e)
            raise e

    if force_build:
        logging.info(f"Forcing new build of {data_name}")
        return build_dataset(data_name, save, **kwargs)

    cut_off: pd.Timedelta | None = kwargs.get("cut_off_time", None)
    if data_name == "icu_chartevents_tabular":
        # special case, since multiple files are saved.
        if cut_off is not None:
            # special case ICU events: check if timedelta matches
            cutoffiso = cut_off.isoformat()
            fn = f"{data_name}_[0-9][0-9]*M_*{cutoffiso}*.feather"
        else:
            fn = f"{data_name}_[0-9][0-9]*M_*.feather"
    else:
        fn = f"{data_name}*.feather"

    try:
        # get latest file and check if it is recent enough
        latest_file = find_last_modified_file(processed_data_path, fn)
    except FileNotFoundError:
        logging.info(f"Could not find {data_name}, building it")
        return build_dataset(data_name, save, **kwargs)

    data_file_age = datetime.fromtimestamp(os.path.getmtime(latest_file))
    if data_file_age > data_max_age:
        logging.info(f"Found {data_name} at {latest_file}, but it is too old ({data_file_age})")
        return build_dataset(data_name, save, **kwargs)
    else:
        logging.info(f"Found {data_name} at {latest_file}, loading it")
        return pd.read_feather(latest_file)


def build_data(
    raw_data_path: Path,
    processed_data_path: Path | None = None,
    save=False,
    load_preprocessed_data=True,
    skip: list[str] = [],
    data_max_age: datetime = datetime.max,
    **kwargs,
) -> dict[str, pd.DataFrame | tuple[dict[str, set[str]], list[pd.DataFrame]]]:
    if processed_data_path is None:
        processed_data_path = raw_data_path.parent.parent / "processed"
    # for each type, check if file exists, if not, build it
    data_functions: dict[str, Callable] = DATA_BUILDERS.copy()
    for k in skip:
        data_functions.pop(k)

    # optionally, more feather file names can be supplied to be loaded
    extra_data = kwargs.get("extra_data", [])
    data_values: dict[str, None | pd.DataFrame | tuple[pd.DataFrame, ...]] = {
        k: None for k in data_functions.keys()
    }
    for name in extra_data:
        data_values[name] = None  # no function associated with it

    for data_name in data_values.keys():
        try:
            data_values[data_name] = build_or_load(
                raw_data_path,
                processed_data_path,
                data_name,
                save,
                data_max_age,
                force_build=(not load_preprocessed_data),
                **kwargs,
            )
        except NotImplementedError:
            continue

    # remove None entries
    data_values_clean = {k: v for k, v in data_values.items() if v is not None}

    return data_values_clean
