import json
from pathlib import Path


def collect_json(json_folder: Path) -> dict:
    result = {}
    for file in json_folder.rglob('*.json'):
        result.update(json.load(open(file)))
    return result
