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



def test_minmax(client_on_dispatcher: Client):
    client = client_on_dispatcher
    test_task = deepcopy(task_body)
    test_task['client'] = client.broker.queue
    test_task['module'] = 'findus_edge.algo.normalization'
    test_task['function'] = 'normalization'
    args = {
        "input_data": MINMAX_DATA,
        "norm_method": "minmax"
    }
    test_task['arguments'] = args
    client.broker.publish(test_task)
    # Validating result on client
    _, result = next(client.broker.pull())
    data = json.loads(result['result'])
    logger.info(json.dumps(data, indent=4))
    price_count = len(data['prices'])
    # dividend_count = len(data['dividends'])
    # logger.info(f'Price rows: {price_count}, Dividend rows: {dividend_count}')
    # _min, _max = calculate_boundaries(62, 5)
    # assert _min <= price_count <= _max, f'Price count does not fit expected boundaries({_min},{_max})'
    # assert dividend_count, 'Dividend rows are missing'