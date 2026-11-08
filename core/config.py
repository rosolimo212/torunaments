# coding: utf-8
"""Чтение settings.yaml."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_config(path=None):
    config_path = Path(path) if path is not None else ROOT / "settings.yaml"
    with open(config_path, encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    config["_root"] = config_path.resolve().parent
    return config


def ratings_path(config):
    return Path(config["_root"]) / config["data"]["ratings"]
