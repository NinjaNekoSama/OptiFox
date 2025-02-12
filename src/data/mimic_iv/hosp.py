import logging
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

from src.data import utils as data_utils
from src.features.mimic_iv import hosp as features_hosp

# Path to data directory
mimic_dir = (
    Path(__file__).parent.parent.parent
    / "data"
    / "external"
    / "mimic-iv-clinical-database-demo-2.2"
)
ed_dir = mimic_dir / "ed"
hosp_dir = mimic_dir / "hosp"
icu_dir = mimic_dir / "icu"


def build_surgeries(
    base_path: Path = mimic_dir, save: bool = False, **kwargs
) -> pd.DataFrame | None:
    # get data
    hosp_dir = base_path / "hosp"
    services = pd.read_csv(
        hosp_dir / "services.csv.gz",
        parse_dates=["transfertime"],
        dtype={"prev_service": "category", "curr_service": "category"},
    )

    # filter for only surgery and remove unused data
    surgery_stays = filter_and_clean_services(services)
    # validate data
    try:
        validate_services(surgery_stays)
    except AssertionError as e:
        logging.error(e)
        return None
    # return data
    if save:
        data_utils.save_processed_dataframe(surgery_stays, base_path, "surgeries")
    return surgery_stays


def filter_and_clean_services(df: pd.DataFrame, surgery_types: list | None = None) -> pd.DataFrame:
    # get stays where service includes surgery
    if surgery_types is None:
        surgery_types = ["ORTHO", "CSURG", "NSURG", "PSURG", "SURG", "TSURG", "VSURG"]
    df = (
        df[df["curr_service"].isin(surgery_types)]
        .drop(columns=["prev_service"])
        .rename(columns={"curr_service": "service", "transfertime": "transfer_to_surgery"})
        .assign(service=lambda x: x.service.cat.remove_unused_categories())
    )

    # remove surgery entries within one hour of each other
    df = clean_duplicate_surgeries(df)

    logging.info(f"Remove duplicate surgeries:\t\t{df.shape}")
    dups = (
        df.loc[:, ["subject_id", "hadm_id"]]
        .groupby(["subject_id", "hadm_id"])
        .size()
        .reset_index(name="count")
        .query("count > 1")
        .__len__()
        / df.__len__()
    )
    logging.info(f"percentage of admissions with multiple surgeries:\t\t{dups:.2%}")

    return df


def validate_services(df: pd.DataFrame):
    # check that there are no missing values
    assert df.isna().sum().sum() == 0, "There are missing values in the data."
    # TODO any other validation? fixed number of columns? etc.
    assert len(df.columns) == 4, "There are more columns than expected."
    assert len(df) > 0, "There are no rows in the data."
    assert df["service"].nunique() <= 7, "There are more services than expected."


def merge_surgeries_hospitalizations_icu_omr(
    surgeries: pd.DataFrame,
    hospitalizations: pd.DataFrame,
    icu_stays: pd.DataFrame,
    omr: pd.DataFrame,
    icu_stay_timedelta: pd.Timedelta | None = None,
) -> pd.DataFrame:
    logging.info(f"OMR:\t\t{omr.shape}")
    df = merge_surgeries_hospitalizations_icu(
        surgeries, hospitalizations, icu_stays, icu_stay_timedelta
    )

    df = merge_omr_by_date(df, omr, tolerance=None)
    logging.info(f"Hosp-Surgery-ICU-OMR df:\t\t{df.shape}")

    return df


def merge_surgeries_hospitalizations_icu(
    surgeries: pd.DataFrame,
    hospitalizations: pd.DataFrame,
    icu_stays: pd.DataFrame,
    icu_stay_timedelta: pd.Timedelta | None = None,
) -> pd.DataFrame:
    logging.info(f"Surgeries:\t\t{surgeries.shape}")
    logging.info(f"Hospitalizations:\t\t{hospitalizations.shape}")
    logging.info(f"ICU stays:\t\t{icu_stays.shape}")

    df = merge_surgeries_hospitalizations(surgeries, hospitalizations)

    # merge with icu stays
    df = merge_hospitalizations_icu_stays(df, icu_stays, tolerance=icu_stay_timedelta)

    logging.info(f"Hosp-Surgery-ICU df:\t\t{df.shape}")

    return df


def merge_hospitalizations_icu_stays(
    df: pd.DataFrame, icu_stays: pd.DataFrame, tolerance: pd.Timedelta | None = None
) -> pd.DataFrame:
    # find the next icu stay that is closest to the surgery
    df = pd.merge_asof(
        df.sort_values("transfer_to_surgery"),
        icu_stays.sort_values("icu_intime"),
        left_on="transfer_to_surgery",
        right_on="icu_intime",
        by=["subject_id", "hadm_id"],
        tolerance=tolerance,
        direction="forward",
    )
    # add indicator column
    df["icu_stay"] = df["icu_stay_id"].notnull()
    # and another column just giving the hours between surgery and icu stay.
    df["icu_stay_hours_after_surgery"] = (
        df["icu_intime"] - df["transfer_to_surgery"]
    ).dt.total_seconds() / 3600

    if tolerance is not None:
        tolerance_name = int(tolerance.total_seconds() / 3600)
        col_name = f"icu_stay_after_{tolerance_name}_hours"
        df.rename(columns={"icu_stay": col_name}, inplace=True)

    # sort by icuintime
    df = df.sort_values(["subject_id", "hadm_id", "icu_intime"])
    return df


def merge_surgeries_hospitalizations(
    surgeries: pd.DataFrame, hospitalizations: pd.DataFrame
) -> pd.DataFrame:
    logging.info("Merging surgeries and hospitalizations.")
    data_utils.assert_feature_existence(
        surgeries, ["subject_id", "hadm_id", "transfer_to_surgery"]
    )
    data_utils.assert_feature_existence(
        hospitalizations, ["subject_id", "hadm_id", "admittime", "dischtime"]
    )
    df = pd.merge(
        surgeries,
        hospitalizations,
        on=["subject_id", "hadm_id"],
        how="inner",
        validate="many_to_one",
    )
    # drop rows where the surgery happened before the hospitalization
    df = df[df["transfer_to_surgery"] >= df["admittime"]]
    # drop rows where the surgery happened after the discharge
    df = df[df["transfer_to_surgery"] <= df["dischtime"]]

    logging.info(f"Merged dataframe:\t\t{df.shape}")

    return df


def clean_duplicate_surgeries(df: pd.DataFrame) -> pd.DataFrame:
    # sort `transfer_to_surgery` descending.
    # When calculating diff, this only works on second entry,
    # which will then be deleted. so the second, earlier, entry will be dropped.
    df = df.sort_values(by=["subject_id", "hadm_id", "transfer_to_surgery"], ascending=False)

    # select the stays with multiple surgery-entries within one hour, keep only the latter one
    diffs_less_than_hour = (
        df.groupby(["subject_id", "hadm_id"], group_keys=False)
        .agg({"transfer_to_surgery": ["diff"]})
        .abs()
        .dropna()
        .rename(columns={"transfer_to_surgery": "diff"})
    )
    # reset column names
    diffs_less_than_hour.columns = diffs_less_than_hour.columns.droplevel(1)
    # get entries with less than 1 hour diff
    diffs_less_than_hour = diffs_less_than_hour[
        diffs_less_than_hour["diff"] < pd.Timedelta(hours=1)
    ]
    df = df.drop(diffs_less_than_hour.index)

    logging.info(
        f"Removed {diffs_less_than_hour.shape[0]} duplicate surgeries with \
            start time within one hour."
    )

    return df


def standardize_icd(
    mapping: pd.DataFrame,
    df: pd.DataFrame,
    root=False,
    map_code_colname="diagnosis_code",
    only_icd10=True,
) -> pd.DataFrame:
    """Takes an ICD9 -> ICD10 mapping table and a modulenosis dataframe; adds column with converted
    ICD10 column."""

    def icd_9to10(icd):
        # If root is true, only map an ICD 9 -> 10 \
        # according to the ICD9's root (first 3 digits)
        if root:
            icd = icd[:3]
        try:
            # Many ICD-9's do not have a 1-to-1 mapping; get first index of mapped codes
            return mapping.loc[mapping[map_code_colname] == icd].icd10cm.iloc[0]
        except IndexError:
            # logging.error("Error on code", icd)
            return np.nan

    # Create new column with original codes as default
    col_name = "icd10_convert"
    if root:
        col_name = "icd10_root_convert"
    df[col_name] = df["icd_code"].values

    # Group identical ICD9 codes, then convert all ICD9 codes within a group to ICD10
    logging.info("Converting ICD9 codes to ICD10")
    for code, group in tqdm(df.loc[df.icd_version == 9].groupby(by="icd_code")):
        new_code = icd_9to10(code)
        for idx in group.index.values:
            # Modify values of original df at the indexes in the groups
            df.at[idx, col_name] = new_code

    if only_icd10:
        # Column for just the roots of the converted ICD10 column
        df["icd10_root"] = df[col_name].apply(lambda x: x[:3] if isinstance(x, str) else np.nan)

    return df


def build_icd_diagnoses(base_path: Path = mimic_dir, save: bool = False, **kwargs) -> pd.DataFrame:
    """Preprocesses a module by adding ICD10 codes and standardizing ICD9 codes.

    Modified from MIMIC-IV-Data-Pipeline
    """

    hosp_dir = base_path / "hosp"
    fn_icd = hosp_dir / "diagnoses_icd.csv.gz"
    icd = pd.read_csv(fn_icd)
    detailed = kwargs.get("detailed", True)
    if detailed:
        # adds description. not really needed for prediction, but useful for debugging
        fn_d_icd = hosp_dir / "d_icd_diagnoses.csv.gz"
        d_icd = pd.read_csv(fn_d_icd)
        icd = icd.merge(d_icd, on=["icd_version", "icd_code"], how="left")

    icd = icd.rename(columns={"seq_num": "icd_seq_num"})

    icd_map_path = base_path.parent / "ICD9_to_ICD10_mapping.txt"

    def read_icd_mapping(path):
        mapping = pd.read_csv(path, header=0, delimiter="\t")
        mapping.diagnosis_description = mapping.diagnosis_description.apply(str.lower)
        return mapping

    # logging.info(icd.shape)
    # logging.info(icd['icd_code'].nunique())

    icd_map = read_icd_mapping(icd_map_path)
    # logging.info(icd_map)
    icd = standardize_icd(icd_map, icd, root=True)
    logging.info(
        f"# unique ICD-9 codes: \
                    {icd[icd['icd_version']==9]['icd_code'].nunique()}"
    )
    logging.info(
        f"# unique ICD-10 codes: \
                    {icd[icd['icd_version']==10]['icd_code'].nunique()}"
    )
    logging.info(
        f"# unique ICD-10 codes (After converting ICD-9 to ICD-10): \
        {icd['icd10_root_convert'].nunique()}"
    )
    logging.info(
        f"# unique 3-Digit ICD-10 codes (After clinical grouping ICD-10 codes) \
        {icd['icd10_root'].nunique()}"
    )
    logging.info(f"# Admissions:{icd.hadm_id.nunique()}")

    # create features by aggregating comorbidities
    icd = features_hosp.build_icd_features(icd)

    if save:
        data_utils.save_processed_dataframe(icd, base_path, "icd_diagnoses")

    return icd


def build_drg(base_path: Path = mimic_dir, save: bool = False, **kwargs) -> pd.DataFrame:
    hosp_dir = base_path / "hosp"
    fn = hosp_dir / "drgcodes.csv.gz"
    drg = (
        pd.read_csv(
            fn,
            dtype={
                "drg_type": "category",
                "drg_code": "category",
            },
        )
        # only keep APR DRGs
        .pipe(lambda df: df[df["drg_type"] == "APR"])
        .drop(columns=["drg_type"])
        .assign(
            drg_severity=lambda df: df["drg_severity"].astype("int64"),
            drg_mortality=lambda df: df["drg_mortality"].astype("int64"),
        )
    )
    # get the 199 most common codes and assign all less common ones to "other"
    # create new category
    drg["drg_code"] = drg["drg_code"].cat.add_categories("other")
    most_common_codes = drg["drg_code"].value_counts().index[:199]
    drg["drg_code"] = drg["drg_code"].where(drg["drg_code"].isin(most_common_codes), "other")

    logging.info(f"Read {fn}.\nDRGs:\t\t{drg.shape}")
    if save:
        # just to have the same API. not really necessary since no processing has happened.
        logging.warning("saving drg data not supported.")

    return drg


def build_patients(base_path: Path = mimic_dir, save: bool = False, **kwargs) -> pd.DataFrame:
    hosp_dir = base_path / "hosp"
    fn = hosp_dir / "patients.csv.gz"
    patients = pd.read_csv(
        fn,
        usecols=["subject_id", "gender", "anchor_age", "anchor_year", "anchor_year_group"],
        dtype={
            "gender": "category",
            "anchor_age": "int64",
            "anchor_year": "int64",
            "subject_id": "int64",
            "anchor_year_group": "category",
        },
    )
    logging.info(f"Read {fn}.\nPatients:\t\t{patients.shape}")
    if save:
        # just to have the same API. not really necessary since no processing has happened.
        logging.warning("saving patients data not supported.")

    return patients


def validate_admissions(df: pd.DataFrame) -> pd.DataFrame:
    # drop rows where LOS is < 0
    # there are a few data-entry errors where the total_los is negative. drop those.
    df.drop(df[df["ed_los"] < 0].index, inplace=True)
    assert (df[df["ed_los"].notna()]["ed_los"] >= 0).all()
    df.drop(df[df["total_los"] < 0].index, inplace=True)
    assert (df[df["total_los"].notna()]["total_los"] >= 0).all()
    return df


def build_admissions(base_path: Path = mimic_dir, save: bool = False, **kwargs) -> pd.DataFrame:
    hosp_dir = base_path / "hosp"
    fn = hosp_dir / "admissions.csv.gz"
    df = pd.read_csv(
        fn,
        usecols=[
            "subject_id",
            "hadm_id",
            "admittime",
            "dischtime",
            "admission_type",
            "admission_location",
            "insurance",
            "language",
            "marital_status",
            "race",
            "edregtime",
            "edouttime",
        ],
        dtype={
            "admission_type": "category",
            "admission_location": "category",
            "insurance": "category",
            "language": "category",
            "marital_status": "category",
            "race": "category",
        },
        parse_dates=["admittime", "dischtime", "edregtime", "edouttime"],
    )

    data_utils.assert_feature_existence(df, ["edregtime", "edouttime", "admittime", "dischtime"])

    df = features_hosp.build_admission_features(df)
    df = validate_admissions(df)

    # TODO remove features probably not present in UKA data?
    # admissions.drop(columns=["race", "marital_status"], inplace=True)
    logging.info(f"Read {fn}.\nAdmissions:\t\t{df.shape}")
    if save:
        # just to have the same API. not really necessary since no processing has happened.
        logging.warning("saving admissions data not supported.")
    return df


def merge_patients_admissions(patients: pd.DataFrame, admissions: pd.DataFrame) -> pd.DataFrame:
    logging.info("Merging patients and admissions.")

    df = pd.merge(admissions, patients, on="subject_id", how="inner", validate="many_to_one")

    logging.info(f"Merged dataframe:\t\t{df.shape}")

    return df


def merge_admissions_drg(admissions: pd.DataFrame, drg: pd.DataFrame) -> pd.DataFrame:
    logging.info("Merging admissions and their DRG codes.")

    df = pd.merge(admissions, drg, on=["subject_id", "hadm_id"], how="left", validate="one_to_one")

    logging.info(f"Merged dataframe:\t\t{df.shape}")

    return df


def merge_admissions_icd(admissions: pd.DataFrame, icd: pd.DataFrame) -> pd.DataFrame:
    logging.info("Merging admissions and their ICD diagnoses.")

    df = pd.merge(admissions, icd, on=["subject_id", "hadm_id"], how="left", validate="one_to_one")
    logging.info(f"Merged dataframe:\t\t{df.shape}")

    return df


def validate_hospitalizations(df: pd.DataFrame) -> bool:
    # TODO validate hospitalizations
    df = df[df.age >= 18]
    return True


def build_hospitalizations(
    base_path: Path = mimic_dir, save: bool = False, **kwargs
) -> pd.DataFrame:
    patients = build_patients(base_path=base_path)
    admissions = build_admissions(base_path=base_path)
    drg_codes = build_drg(base_path=base_path)
    icd_diagnoses = build_icd_diagnoses(base_path=base_path)

    df = merge_patients_admissions(patients, admissions)
    df = merge_admissions_drg(df, drg_codes)
    df = merge_admissions_icd(df, icd_diagnoses)
    # set age_at_admission as the age at the time of admission
    # and remove anchor_age and anchor_year
    df = features_hosp.build_age_group_feature(df)
    df = features_hosp.build_holiday_feature(df)
    logging.warning("Holiday feature cannot be used with MIMIC-IV due to the year shift")
    # TODO any filtering necessary? e.g. by age?
    validate_hospitalizations(df)

    if save:
        data_utils.save_processed_dataframe(df, base_path, "hospitalizations")
    return df


def clean_omr(df: pd.DataFrame) -> pd.DataFrame:
    """Clean the OMR data.

    Check for extreme values and drop rows with extreme values.
    """
    # very broad ranges are excepted right now!

    # 155 is extremely extreme already...
    extreme_bmi_rows = df[(df["BMI (kg/m2)"] < 10) | (df["BMI (kg/m2)"] > 155)]
    if extreme_bmi_rows.shape[0] > 0:
        logging.warning(
            f"Found {extreme_bmi_rows.shape[0]} rows with extreme BMI values. Dropping these rows."
        )
        df.drop(extreme_bmi_rows.index, inplace=True)

    extreme_height_rows = df[(df["Height (cm)"] < 50) | (df["Height (cm)"] > 250)]
    if extreme_height_rows.shape[0] > 0:
        logging.warning(
            f"Found {extreme_height_rows.shape[0]} rows with extreme height values.\
                  Dropping these rows."
        )
        df.drop(extreme_height_rows.index, inplace=True)

    # TODO: not sure if children are present in the data - should probably be removed
    extreme_weight_rows = df[(df["Weight (kg)"] < 30) | (df["Weight (kg)"] > 250)]
    if extreme_weight_rows.shape[0] > 0:
        logging.warning(
            f"Found {extreme_weight_rows.shape[0]} rows with extreme weight values.\
                  Dropping these rows."
        )
        df.drop(extreme_weight_rows.index, inplace=True)

    # remove mostly empty columns. should be eGFR only at this point.
    na_thresh = int(df.shape[0] * 0.01)
    df.dropna(axis=1, thresh=na_thresh, inplace=True)
    df.drop(columns=["seq_num"], inplace=True)

    return df


def build_omr(base_path: Path = mimic_dir, save: bool = False, **kwargs) -> pd.DataFrame:
    hosp_dir = base_path / "hosp"
    fn = hosp_dir / "omr.csv.gz"
    df = pd.read_csv(fn, parse_dates=["chartdate"])
    logging.info(f"Read {fn}.\nOMR:\t\t{df.shape}")
    # reshape from long (row-based, (key, value)) to wide (column-based) format
    df = df.pivot(
        index=["chartdate", "subject_id", "seq_num"],
        columns=["result_name"],
        values=["result_value"],
    ).reset_index(col_level=1)
    # remove outer multiindex
    df = df.droplevel(0, axis=1)
    # reset index name
    df.rename_axis(None, axis=1, inplace=True)
    # sort by chartdate, subject_id, seq_num
    df = df.sort_values(["chartdate", "subject_id", "seq_num"])

    bp_col_names = [
        "Blood Pressure",
        "Blood Pressure Lying",
        "Blood Pressure Sitting",
        "Blood Pressure Standing",
        "Blood Pressure Standing (1 min)",
        "Blood Pressure Standing (3 mins)",
    ]
    bp_col_names = [col for col in bp_col_names if col in df.columns]
    #
    data_utils.assert_feature_existence(
        df, ["Blood Pressure"] + ["BMI (kg/m2)", "Height (Inches)", "Weight (Lbs)"]
    )

    logging.info(f"Reshaped long-to-wide:\t\t{df.shape}")

    df = features_hosp.process_omr_height_weight(df)
    # TODO filter Blood Pressure columns for reasonable values beforehand
    df = features_hosp.create_blood_pressure_feature(df, bp_col_names)
    # create Mean Arterial Pressure (MAP) from systolic and diastolic blood pressure
    df["MAP"] = (df["Blood Pressure (systolic)"] + 2 * df["Blood Pressure (diastolic)"]) / 3
    df = clean_omr(df)

    # create daily averaged values by taking mean for each chartdate and subject_id
    df = df.groupby(["chartdate", "subject_id"]).mean().reset_index()
    # TODO calculate BMI from height and weight or vice versa
    logging.info(f"Finished OMR preprocessing:\t\t{df.shape}")

    if save:
        data_utils.save_processed_dataframe(df, base_path, "omr")

    return df


def merge_omr_by_date(
    left_df: pd.DataFrame, omr: pd.DataFrame, tolerance: pd.Timedelta | None = None
) -> pd.DataFrame:
    data_utils.assert_feature_existence(
        left_df, ["subject_id", "admittime", "transfer_to_surgery"]
    )

    # TODO since the daily values often contain NaNs, one could also average
    # the chart measurements to e.g. weekly (within a tolerance) to get less sparse data

    # left-join on main df, find closest chartdate before surgery
    df = pd.merge_asof(
        left_df.sort_values("transfer_to_surgery"),
        omr.sort_values("chartdate"),
        left_on="transfer_to_surgery",
        right_on="chartdate",
        by="subject_id",
        tolerance=tolerance,
    )

    df.rename(columns={"chartdate": "last_omr_measurement_date"}, inplace=True)

    return df


def build_services(base_path: Path = mimic_dir) -> pd.DataFrame:
    # get data
    hosp_dir = base_path / "hosp"
    services = pd.read_csv(
        hosp_dir / "services.csv.gz",
        parse_dates=["transfertime"],
        dtype={"prev_service": "category", "curr_service": "category"},
    )
    return services


def load_diagnoses(base_path: Path) -> pd.DataFrame:
    fn_icd = base_path / "hosp" / "diagnoses_icd.csv.gz"
    diagnoses = pd.read_csv(fn_icd)
    return diagnoses


def create_scores_features(base_path: str) -> pd.DataFrame:
    admissions = build_admissions(Path(base_path))
    patients = build_patients(Path(base_path))[["subject_id", "anchor_age"]]
    services = build_services(Path(base_path))

    admissions["is_planed"] = admissions["admission_type"] == "ELECTIVE"
    services["is_surg"] = services["curr_service"].str.contains("surg", case=False)
    services = services.sort_values("is_surg", ascending=[False]).drop_duplicates(
        ["subject_id", "hadm_id"]
    )

    scores = patients.merge(
        admissions[["subject_id", "hadm_id", "is_planed"]], on=["subject_id"], how="left"
    )
    scores = scores.merge(
        services[["subject_id", "hadm_id", "is_surg"]], on=["subject_id", "hadm_id"], how="left"
    )

    del patients, admissions, services

    return scores


def create_diagnose_features(base_path: Path) -> pd.DataFrame:
    diagnose_df = load_diagnoses(base_path)

    diagnose_df["subcode03"] = diagnose_df["icd_code"].str.slice(start=0, stop=3)

    diagnose_df["aids"] = (
        # ICD Version 9
        ((diagnose_df["subcode03"].between("042", "044")) & (diagnose_df["icd_version"] == 9))
        |
        # Icd Version 10
        ((diagnose_df["subcode03"].between("B20", "B22")) & (diagnose_df["icd_version"] == 10))
    )

    # Hämatologische Neoplasie
    diagnose_df["subcode05"] = diagnose_df["icd_code"].str.slice(start=0, stop=5)

    diagnose_df["neoplasie"] = (
        # ICD Version 9
        (
            (diagnose_df["icd_version"] == 9)
            & (
                (diagnose_df["subcode05"].between("20000", "20238"))  # lymphoma
                | (diagnose_df["subcode05"].between("20240", "20248"))  # leukemia
                | (diagnose_df["subcode05"].between("20250", "20302"))  # lymphoma
                | (diagnose_df["subcode05"].between("20310", "20312"))  # leukemia
                | (diagnose_df["subcode05"].between("20302", "20382"))  # lymphoma
                | (diagnose_df["subcode05"].between("20400", "20522"))  # chronic leukemia
                | (diagnose_df["subcode05"].between("20580", "20702"))  # other myeloid leukemia
                | (diagnose_df["subcode05"].between("20720", "20892"))  # other myeloid leukemia
                | (diagnose_df["subcode05"].between("23860", "23869"))  # lymphoma
                | (diagnose_df["subcode05"].between("27330", "27339"))  # lymphoma
            )
        )
        |
        # Icd Version 10
        ((diagnose_df["subcode03"].between("C81", "C96")) & (diagnose_df["icd_version"] == 10))
    )

    # Neoplasie mit Metastase
    diagnose_df["metastatic_cancer"] = (
        # ICD Version 9
        (
            (diagnose_df["icd_version"] == 9)
            & (
                (diagnose_df["subcode05"].between("19600", "19619"))
                | (diagnose_df["subcode05"].between("20970", "20975"))
                | (diagnose_df["subcode05"].isin(["20979", "78951"]))
            )
        )
        |
        # Icd Version 10
        (
            (diagnose_df["icd_version"] == 10)
            & (
                (diagnose_df["subcode03"].between("C77", "C79"))
                | (diagnose_df["subcode05"].between("C800", "C800"))
            )
        )
    )

    aids = diagnose_df[diagnose_df["aids"]].drop_duplicates(["subject_id", "hadm_id"])[
        ["subject_id", "hadm_id", "aids"]
    ]
    neoplasie = diagnose_df[diagnose_df["neoplasie"]].drop_duplicates(["subject_id", "hadm_id"])
    metastatic_cancer = diagnose_df[diagnose_df["metastatic_cancer"]].drop_duplicates(
        ["subject_id", "hadm_id"]
    )

    fields = aids.merge(
        neoplasie[["subject_id", "hadm_id", "neoplasie"]], on=["subject_id", "hadm_id"], how="left"
    )
    fields = fields.merge(
        metastatic_cancer[["subject_id", "hadm_id", "metastatic_cancer"]],
        on=["subject_id", "hadm_id"],
        how="left",
    )

    del aids, neoplasie, metastatic_cancer
    return fields[["subject_id", "hadm_id", "aids", "neoplasie", "metastatic_cancer"]]
