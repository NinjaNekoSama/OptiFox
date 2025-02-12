import pandas as pd

from src.data import utils as data_utils


def process_omr_height_weight(df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "BMI (kg/m2)",
        "Height (Inches)",
        "Weight (Lbs)",
        "Height",
        "Weight",
        "BMI",
        "Height (cm)",
        "Weight (kg)",
    ]
    available_cols = [col for col in cols if col in df.columns]
    # convert  to numeric
    df[available_cols] = df[available_cols].apply(pd.to_numeric, errors="coerce")

    # convert height from inches to cm and fill missing values using available columns
    df["Height (cm)"] = (
        df["Height (Inches)"].combine_first(df.get("Height", pd.Series(dtype="float64"))) * 2.54
    )

    # convert weight from lbs to kg and fill missing values using available columns
    df["Weight (kg)"] = (
        df["Weight (Lbs)"].combine_first(df.get("Weight", pd.Series(dtype="float64"))) * 0.45359237
    )

    df["BMI (kg/m2)"] = df["BMI (kg/m2)"].fillna(df.get("BMI", pd.Series(dtype="float64")))

    # drop old columns
    df = df.drop(
        columns=["BMI", "Height", "Weight", "Height (Inches)", "Weight (Lbs)"], errors="ignore"
    )

    return df


def create_blood_pressure_feature(df: pd.DataFrame, bp_col_names: list[str]) -> pd.DataFrame:
    """Create a blood pressure feature from the different blood pressure measurements."""

    # split the string into systolic and diastolic for all columns.
    def split_bp_col(df, col_name):
        split_bp = df[col_name].str.split("/", n=1, expand=True)
        suffix_col_name = col_name.replace("Blood Pressure", "").strip()
        # the BP variant columns are renamed
        if suffix_col_name:
            split_bp.columns = [f"systolic ({suffix_col_name})", f"diastolic ({suffix_col_name})"]
        else:
            # this is the non-specific BP column, which will be our output
            split_bp.columns = ["Blood Pressure (systolic)", "Blood Pressure (diastolic)"]
        return split_bp

    new_bp_cols = [split_bp_col(df, col) for col in bp_col_names]
    all_bps = pd.concat(new_bp_cols, axis=1)
    all_bps = all_bps.astype("float64")

    # fill missing values in columns systolic and diastolic with mean of
    # remaining columns starting with "systolic " or "diastolic" respectively

    # fill nan with mean of remaining columns starting with systolic
    all_bps["Blood Pressure (systolic)"] = all_bps["Blood Pressure (systolic)"].fillna(
        all_bps.loc[:, all_bps.columns.str.startswith("systolic")].mean(axis=1)
    )
    # fill nan with mean of remaining columns starting with diastolic
    all_bps["Blood Pressure (diastolic)"] = all_bps["Blood Pressure (diastolic)"].fillna(
        all_bps.loc[:, all_bps.columns.str.startswith("diastolic")].mean(axis=1)
    )
    # drop all columns starting with systolic or diastolic
    all_bps.drop(all_bps.columns[all_bps.columns.str.startswith("systolic")], axis=1, inplace=True)
    all_bps.drop(
        all_bps.columns[all_bps.columns.str.startswith("diastolic")], axis=1, inplace=True
    )

    # remove all old blood pressure columns
    df.drop(columns=bp_col_names, inplace=True)
    # add new blood pressure columns
    df = pd.concat([df, all_bps], axis=1)
    return df


def parse_icd10_code_to_chapter(icd10_code):
    chapters = {
        ("A00", "B99"): "I",
        ("C00", "D48"): "II",
        ("D50", "D89"): "III",
        ("E00", "E90"): "IV",
        ("F00", "F99"): "V",
        ("G00", "G99"): "VI",
        ("H00", "H59"): "VII",
        ("H60", "H95"): "VIII",
        ("I00", "I99"): "IX",
        ("J00", "J99"): "X",
        ("K00", "K93"): "XI",
        ("L00", "L99"): "XII",
        ("M00", "M99"): "XIII",
        ("N00", "N99"): "XIV",
        ("O00", "O99"): "XV",
        ("P00", "P96"): "XVI",
        ("Q00", "Q99"): "XVII",
        ("R00", "R99"): "XVIII",
        ("S00", "T98"): "XIX",
        ("V01", "Y98"): "XX",
        ("Z00", "Z99"): "XXI",
        ("U00", "U99"): "XXII",
    }

    for (start_code, end_code), chapter in chapters.items():
        if start_code <= icd10_code <= end_code:
            return chapter
    return None


def build_icd_features(df: pd.DataFrame) -> pd.DataFrame:
    """Build features from ICD codes."""
    # use either "icd10_convert" or "icd10_root_convert"
    code_col = "icd10_convert"
    if code_col not in df.columns:
        code_col = "icd10_root_convert"
    data_utils.assert_feature_existence(df, [code_col, "icd_seq_num"])
    # get number of diagnoses per (subject_id, hadm_id)
    # decrement by one and (floor 0) to get number of comorbidities
    # get diagnoses with seq_num == 1 as main diagnosis

    df = (
        df.sort_values("icd_seq_num")
        .groupby(["subject_id", "hadm_id"])
        .agg(
            num_icd_comorbidities=(code_col, "count"),
            icd_main=(code_col, "first"),
            icd_main_desc=("long_title", "first"),
            # add second diagnosis, too, see table doc for more information.
            icd_secondary=(code_col, lambda x: x.iloc[1] if len(x) > 1 else None),
            icd_secondary_desc=("long_title", lambda x: x.iloc[1] if len(x) > 1 else None),
            # all_diagnoses=(code_col, lambda x: " ".join(x)),
        )  # decrease comorbidities by 1, but clip at 0
        .dropna(subset=["icd_main"])
        .assign(num_icd_comorbidities=lambda x: x.num_icd_comorbidities - 1)
        .assign(num_icd_comorbidities=lambda x: x.num_icd_comorbidities.clip(lower=0))
        .assign(icd_main_3=lambda x: x.icd_main.str[:3])
        .assign(icd_secondary_3=lambda x: x.icd_secondary.str[:3])
        .assign(icd_chapter=lambda x: x.icd_main_3.apply(parse_icd10_code_to_chapter))
        .reset_index()
    )

    return df


def build_admission_features(df: pd.DataFrame) -> pd.DataFrame:
    df = (
        df.assign(
            admit_hour_of_day=lambda x: x.admittime.dt.hour,
            admit_month=lambda x: x.admittime.dt.month,
            admit_season=lambda x: x.admittime.dt.quarter,
            ed_los=lambda x: (x.edouttime - x.edregtime).dt.total_seconds() / 3600 / 24,
            total_los=lambda x: (x.dischtime - x.admittime).dt.total_seconds() / 3600 / 24,
        )
        # set as categorical, so it can be encoded ordinally
        .assign(
            admit_season=lambda x: x.admit_season.astype("category"),
            admit_month=lambda x: x.admit_month.astype("category"),
            admit_hour_of_day=lambda x: x.admit_hour_of_day.astype("category"),
        )
    )

    # TODO add cyclical encoding

    return df


def build_age_group_feature(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate age at admission and bin into age-group."""

    data_utils.assert_feature_existence(df, ["anchor_age", "anchor_year", "admittime"])
    df = df.assign(
        # age at admission
        age=lambda x: x.anchor_age + (x.admittime.dt.year - x.anchor_year),
        # 10 year age groups as string categories
        age_group=lambda x: pd.cut(x.age, bins=range(0, 90, 10), right=False)
        .astype(str)
        .astype("category"),
    ).drop(columns=["anchor_age", "anchor_year"])
    return df


def build_holiday_feature(df: pd.DataFrame, date_col: str = "admittime", **kwargs):
    import holidays

    col = df.index if date_col == "index" else df[date_col]
    assert col.dtype == "datetime64[ns]"
    year = col.year if date_col == "index" else col.dt.year
    country = kwargs.get("country", "US")
    state = kwargs.get("state", "MA")
    holiday = holidays.country_holidays(country, subdiv=state, years=year)
    # create a column with 1 if it's a holiday, 0 otherwise
    df["is_holiday"] = col.isin(holiday)
    return df
