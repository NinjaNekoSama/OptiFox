"""This file contains the util code required to support the optifox REST API framework."""

import os
import glob
import math
import logging
from logging.handlers import RotatingFileHandler

LOGGER_NAME = "optifox_logger"


def create_log():
    """Creates a logger for the application.

    If the logs directory does not exist, it creates one.
    Configures the logger to write logs to a rotating file handler.

    Returns:
    --------
    logger : logging.Logger
        Configured logger instance.
    """
    if not os.path.exists("./logs"):
        os.makedirs("./logs")

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.DEBUG)

    handler_local = RotatingFileHandler(
        f"./logs/{LOGGER_NAME}.log", mode="a", maxBytes=50000, backupCount=10
    )
    logger.addHandler(handler_local)
    return logger


logger = create_log()


def find_matching_file(file_pattern, processed_data):
    """Finds a file matching the given pattern in the processed data directory.

    Instead of hardcoding the file name, this function detects
    whatever version of the required file is available.

    Parameters:
    -----------
    file_pattern : str
        The pattern to match files.
    processed_data : str
        The directory where processed data files are stored.

    Returns:
    --------
    file_path : str or None
        The path of the first matching file if found, otherwise None.
    """
    matching_files = glob.glob(file_pattern)
    if matching_files:
        matching_file = os.path.basename(matching_files[0])
        file_path = os.path.join(processed_data, matching_file)
        logger.info("Found file: %s", file_path)
        return file_path
    logger.error("No matching file found for pattern: %s", file_pattern)
    return None


def replace_nan_with_none(data):
    """Recursively replaces NaN values with None in a data structure.

    Parameters:
    -----------
    data : dict, list, or float
        The data structure to process.

    Returns:
    --------
    data : dict, list, or None
        The data structure with NaN values replaced by None.
    """
    if isinstance(data, dict):
        return {k: replace_nan_with_none(v) for k, v in data.items()}
    if isinstance(data, list):
        return [replace_nan_with_none(item) for item in data]
    if isinstance(data, float) and math.isnan(data):
        return None
    else:
        return data


logger = create_log()
