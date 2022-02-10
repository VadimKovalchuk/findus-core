import logging

from time import sleep
from typing import Union

import pytest

from django.utils.timezone import now

from common.broker import Task
from task.lib.commands import COMMANDS, Command
from task.lib.network_client import NetworkClient
from task.lib.task_processor import TaskProcessor
from task.models import NetworkTask

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.django_db


def test_task_queues():
    pass


def test_postponed_task():
    pass


def test_task_start():
    pass


def test_child_task_creation():
    pass


def test_task_finalization():
    pass


def test_task_lifecycle():
    pass
