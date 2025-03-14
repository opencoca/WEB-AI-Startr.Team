import yaml
from enum import Enum
import logging


class ConfigLoader:
    def __init__(self, config_path="config/model_config.yaml"):
        self.config_path = config_path
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.config = self.load_config()
        self.ModelType = self.create_model_type_enum()

    def load_config(self):
        self.logger.debug(f"Loading config from {self.config_path}")
        with open(self.config_path, "r") as file:
            config = yaml.safe_load(file)
        self.logger.debug(f"Config loaded: {config}")
        self.logger.debug(f"*" * 50)
        return config

    def get_model_config(self, model_name):
        self.logger.debug(f"Retrieving config for model: {model_name}")
        model_config = self.config["models"].get(model_name)
        if model_config is None:
            self.logger.error(f"No configuration found for model: {model_name}")
            raise ValueError(f"No configuration found for model: {model_name}")
        return model_config

    def get_all_model_configs(self):
        return self.config["models"]

    def get_default_config(self):
        return self.config["default_config"]

    def create_model_type_enum(self):
        return Enum(
            "ModelType",
            {key: value["name"] for key, value in self.config["models"].items()},
        )


# Create a single instance of ConfigLoader
config_loader = ConfigLoader()

# Use the dynamically created ModelType enum
ModelType = config_loader.ModelType
