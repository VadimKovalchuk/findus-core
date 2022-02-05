import logging

import pytest

from task.lib.commands import COMMANDS, COMMANDS_JSON

logger = logging.getLogger(__name__)


def test_commands_catalog():
    logger.info("\n".join([str(cmd) for cmd in COMMANDS.values()]))
    logger.info("\n".join([str(cmd) for cmd in COMMANDS_JSON.values()]))
