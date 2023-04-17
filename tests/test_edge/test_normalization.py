import json
import logging

from copy import deepcopy
from datetime import datetime, timedelta
from time import sleep
from typing import Union, Tuple

import pytest

from dcn.client.client import Client
from dcn.common.data_structures import task_body

logger = logging.getLogger(__name__)

MINMAX_DATA = {str(idx): idx * 2 for idx in range(0, 11)}


@pytest.mark.parametrize("normalization_method", [
        "minmax",
        "minmax_inverted",
        "z_score",
        "robust"
])
def test_normalization_parameters(client_on_dispatcher: Client, normalization_method: str):
    client = client_on_dispatcher
    test_task = deepcopy(task_body)
    test_task['client'] = client.broker.queue
    test_task['module'] = 'findus_edge.algo.normalization'
    test_task['function'] = 'normalization'
    args = {
        "input_data": MINMAX_DATA,
        "norm_method": normalization_method
    }
    test_task['arguments'] = args
    client.broker.publish(test_task)
    # Validating result on client
    _, result = next(client.broker.pull())
    result = json.loads(result['result'])
    logger.info(json.dumps(result, indent=4))
