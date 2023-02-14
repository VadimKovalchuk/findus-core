from copy import deepcopy
from pathlib import Path

from lib.file_processing import collect_json

TEMPLATES_FOLDER = Path('data/event')
EVENTS_JSON = collect_json(TEMPLATES_FOLDER)


def get_event_template(name: str):
    event = EVENTS_JSON.get(name, {})
    if event:
        event = deepcopy(event)
    return event
