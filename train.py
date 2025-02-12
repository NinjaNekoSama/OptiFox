import logging
import os
import sys

from omegaconf import OmegaConf

from src.pipelines import train_pipeline

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
log = logging.getLogger(__name__)


def main() -> None:
    conf = OmegaConf.load("train_config.yaml")
    # Output is identical to the YAML file
    print(OmegaConf.to_yaml(conf))
    train_pipeline(conf)


if __name__ == "__main__":
    os.environ["HYDRA_FULL_ERROR"] = "1"
    print(sys.path)
    print(os.getcwd())
    main()
