import yaml
from pathlib import Path


def load_prompt(prompt_path: str) -> dict:
    path = Path(prompt_path)

    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    with open(path, "r", encoding="utf-8") as file:
        prompt_config = yaml.safe_load(file)

    return prompt_config