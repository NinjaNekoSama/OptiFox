# -*- coding: utf-8 -*-
import logging
from pathlib import Path
from typing import Optional

# import typer
from dotenv import find_dotenv, load_dotenv
from typing_extensions import deprecated

from src.data import build_data


@deprecated
def main(input_filepath: Optional[Path] = None, output_filepath: Optional[Path] = None):
    """Runs data processing scripts to turn raw data from (../external) into cleaned data ready to
    be analyzed (saved in ../processed)."""
    logger = logging.getLogger(__name__)
    logger.info("making final data set from raw data")
    if input_filepath is None:
        input_filepath = (
            Path.cwd().parent.parent / "data" / "external" / "mimic-iv-clinical-database-demo-2.2"
        )
    if output_filepath is None:
        output_filepath = Path.cwd().parent.parent / "data" / "processed"
    logger.info(f"input_filepath: {input_filepath}")
    logger.info(f"output_filepath: {output_filepath}")
    data_dict = build_data(
        input_filepath, output_filepath, save=True, load_preprocessed_data=False
    )
    for key, value in data_dict.items():
        logger.info(f"{key}: {value.shape}")


if __name__ == "__main__":
    log_fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(level=logging.INFO, format=log_fmt)

    # not used in this stub but often useful for finding various files
    project_dir = Path(__file__).resolve().parents[2]

    # find .env automagically by walking up directories until it's found, then
    # load up the .env entries as environment variables
    load_dotenv(find_dotenv())

    # typer.run(main)
