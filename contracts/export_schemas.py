"""Write one JSON schema per contract to contracts/schemas/."""
import json
from pathlib import Path

from contracts.models import ALL_MODELS

OUT = Path(__file__).parent / "schemas"


def main():
    OUT.mkdir(exist_ok=True)
    for model in ALL_MODELS:
        path = OUT / f"{model.__name__}.json"
        path.write_text(json.dumps(model.model_json_schema(), indent=2) + "\n", encoding="utf-8")
        print(path.name)


if __name__ == "__main__":
    main()
