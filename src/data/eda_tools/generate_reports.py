from pathlib import Path
from typing import Dict

from pandas import DataFrame
from ydata_profiling import ProfileReport


def generate_profiling_report_file(
    dataframe: DataFrame, module_name: str, title: str, folder_path: Path
) -> None:
    """Generates a single pandas profiling report html file that can be used for the exploratory
    data analysis.

    Args:
        dataframe (DataFrame): dataframe that should be reported
        module_name (str): name of the data module
        title (str): title of the report
        folder_path (Path): report folder path
    """
    profile = ProfileReport(dataframe, title=title)
    profile.to_file(folder_path / f"{module_name}_{title}.html")


def generate_profiling_report_files(data: Dict, module_name: str, folder_path: Path) -> None:
    """Generates a pandas profiling report html files that can be used for the exploratory data
    analysis.

    Args:
        data (Dict): dictionary with dataframe that should be reported
        module_name (str): name of the data module
        folder_path (Path): report folder path
    """
    for key, df in data.items():
        title = f"{key}_report"
        generate_profiling_report_file(df, module_name, title, folder_path)
