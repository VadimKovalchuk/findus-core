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

UNIFORM_DISTRIBUTION_DATA = {str(idx): idx * 2 for idx in range(0, 11)}
NORMAL_DISTRIBUTION_DATA = {"1": 1, "2": 3, "3": 4, "4": 4, "5": 5, "6": 5, "7": 6, "8": 6, "9": 7, "10": 9}
# UNIFORM_DATA_WITH_OUTLIER = {"11": 21}
# UNIFORM_DATA_WITH_OUTLIER.update(UNIFORM_DISTRIBUTION_DATA)


@pytest.mark.parametrize("normalization_method, data, expected", [
        pytest.param(
            "minmax",
            UNIFORM_DISTRIBUTION_DATA,
            {"min": 0.0, "max": 20.0},
            id="minmax"
        ),
        pytest.param(
            "minmax_inverted",
            UNIFORM_DISTRIBUTION_DATA,
            {"min": 0.0, "max": 20.0},
            id="minmax_inverted"
        ),
        pytest.param(
            "z_score",
            NORMAL_DISTRIBUTION_DATA,
            {"mean": 5.0, "std": 2.0976176963403033},
            id="z_score"
        ),
        pytest.param(
            "robust",
            UNIFORM_DISTRIBUTION_DATA,
            {"median": 10.0, "iqr": 10.0},
            id="robust"
        ),
])
def test_normalization_parameters(
        client_on_dispatcher: Client,
        normalization_method: str,
        data: dict,
        expected: dict
):
    logger.info(data)
    client = client_on_dispatcher
    test_task = deepcopy(task_body)
    test_task['client'] = client.broker.queue
    test_task['module'] = 'findus_edge.algo.normalization'
    test_task['function'] = 'normalization'
    args = {
        "input_data": data,
        "norm_method": normalization_method,
        "parameters": {}
    }
    test_task['arguments'] = args
    client.broker.publish(test_task)
    # Validating result on client
    _, result = next(client.broker.pull())
    result = json.loads(result['result'])
    logger.info(json.dumps(result, indent=4))
    assert result['parameters'] == expected, f'Normalization parameters differs from expected'


@pytest.mark.parametrize("normalization_method, parameters, data, expected", [
        pytest.param(
            "minmax",
            {"min": 0.0, "max": 20.0},
            {"SMPL": 6},
            {"SMPL": 0.3},
            id="minmax"
        ),
        pytest.param(
            "minmax_inverted",
            {"min": 0.0, "max": 20.0},
            {"SMPL": 6},
            {"SMPL": 0.7},
            id="minmax_inverted"
        ),
        pytest.param(
            "z_score",
            {"mean": 5.0, "std": 2.0976176963403033},
            {"SMPL": 4},
            {"SMPL": -0.4767},
            id="z_score"
        ),
        pytest.param(
            "robust",
            {"median": 10.0, "iqr": 10.0},
            {"SMPL": 6},
            {"SMPL": -0.4},
            id="robust"
        ),
])
def test_apply_normalization_params(
        client_on_dispatcher: Client,
        normalization_method: str,
        parameters: dict,
        data: dict,
        expected: dict
):
    logger.info(data)
    client = client_on_dispatcher
    test_task = deepcopy(task_body)
    test_task['client'] = client.broker.queue
    test_task['module'] = 'findus_edge.algo.normalization'
    test_task['function'] = 'normalization'
    args = {
        "input_data": data,
        "norm_method": normalization_method,
        "parameters": parameters
    }
    test_task['arguments'] = args
    client.broker.publish(test_task)
    # Validating result on client
    _, result = next(client.broker.pull())
    result = json.loads(result['result'])
    logger.info(json.dumps(result, indent=4))
    assert result['result'] == expected, f'Normalization parameters differs from expected'
