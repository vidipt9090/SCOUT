"""Load versioned prompts from configs/prompts/prompts.yaml."""
from pathlib import Path

import yaml

PATH = Path(__file__).parents[1] / "configs/prompts/prompts.yaml"


def prompt(version: str) -> str:
    return yaml.safe_load(PATH.read_text(encoding="utf-8"))[version]
