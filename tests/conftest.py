import logging
import shutil

from pathlib import Path
from threading import Thread
from time import sleep

import docker
import pytest

from dcn.client.client import Client
from dcn.common.broker import Broker
from dcn.common.constants import SECOND
from dcn.common.data_structures import compose_queue
from dcn.common.defaults import RoutingKeys
from task.lib.network_client import NetworkClient
from task.lib.task_processor import TaskProcessor
from tests.constants import REFERENCE_TICKER
from tests.settings import CLIENT_TEST_TOKEN, DISPATCHER_PORT
from ticker.models import Ticker

logger = logging.getLogger(__name__)


BROKER_HOST = 'localhost'
DISPATCHER_LISTEN_TIMEOUT = 0.01

log_file_formatter = None
cur_log_handler = None
cur_artifacts_path = None

task_queue = compose_queue(RoutingKeys.TASK)


def flush_queue(broker: str, queue: dict = task_queue):
    broker = Broker(queue=queue, host=broker)
    broker.connect()
    logger.info(f'Flushing queue: {queue}')
    state, task = broker.consume()
    while state and task:
        state, task = broker.consume()


def get_container(client, container_filter: str):
    container_list = client.containers.list(filters={'name': container_filter})
    assert container_list, f'Target container ({container_filter}) is not found'
    container = container_list[0]
    logger.info(f'Container {container.name} found')
    return container


@pytest.fixture(autouse=True, scope='session')
def docker_client():
    client = docker.from_env()
    yield client


@pytest.fixture(autouse=True, scope='session')
def rabbit_mq(docker_client):
    container = get_container(docker_client, 'rabbitmq')
    broker = Broker(BROKER_HOST)
    while not broker.connect():
        sleep(10)
    yield container


@pytest.fixture(autouse=True, scope='session')
def dispatcher(docker_client, rabbit_mq):
    container = get_container(docker_client, 'dispatcher')
    yield container


@pytest.fixture(autouse=True, scope='session')
def agent(docker_client, dispatcher):
    container = get_container(docker_client, 'agent')
    yield container


@pytest.fixture()
def client():
    with Client(name='pytest_client',
                token=CLIENT_TEST_TOKEN,
                dsp_port=DISPATCHER_PORT) as client:
        yield client
        if client.broker:
            host = client.broker.host
            input_queue = client.broker.input_queue
        else:
            return
    flush_queue(host, input_queue)


@pytest.fixture()
def client_on_dispatcher(dispatcher, client: Client):
    while not client.get_client_queues():
        logger.debug('Requesting client queues')
        sleep(10)
    client.broker.connect()
    yield client


@pytest.fixture()
def network_client():
    with NetworkClient(
            name='pytest_client',
            token=CLIENT_TEST_TOKEN,
            dsp_host='localhost',
            dsp_port=DISPATCHER_PORT) as network_client:
        yield network_client
        if network_client.broker:
            host = network_client.broker.host
            input_queue = network_client.broker.queue
        else:
            return
    flush_queue(host, input_queue)


@pytest.fixture()
def network_client_on_dispatcher(dispatcher, network_client: NetworkClient):
    while not network_client.get_client_queues():
        logger.info('Requesting Client queues')
        sleep(3)
    # network_client.get_client_queues()
    network_client.broker.connect()
    yield network_client


@pytest.fixture()
def ticker_sample():
    ticker = Ticker(symbol=REFERENCE_TICKER)
    ticker.save()
    yield ticker


# PYTEST HOOKS
def pytest_sessionstart(session):
    global log_file_formatter
    log_file_formatter = logging.Formatter(
        session.config.getini('log_file_format'),
        session.config.getini('log_file_date_format'))


def pytest_runtest_logstart(nodeid, location):
    global cur_log_handler, cur_artifacts_path
    filename, linenum, testname = location

    testname = testname.replace('/', '_')
    cur_artifacts_path = Path('log', testname)
    if cur_artifacts_path.is_dir():
        shutil.rmtree(cur_artifacts_path)
    cur_artifacts_path.mkdir(exist_ok=True, parents=True)

    cur_log_handler = logging.FileHandler(
        cur_artifacts_path / 'pytest.log.txt', mode='w')
    cur_log_handler.setLevel(logging.DEBUG)
    cur_log_handler.setFormatter(log_file_formatter)

    logging.getLogger().addHandler(cur_log_handler)

    logger.info(f'Start test: {nodeid}')
