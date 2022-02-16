import logging
import shutil

from pathlib import Path
from threading import Thread
from time import sleep

import docker
import pytest

from client.client import Client
from common.broker import Broker
from common.constants import SECOND
from common.data_structures import compose_queue
from common.defaults import RoutingKeys
from task.lib.network_client import NetworkClient
from tests.settings import CLIENT_TEST_TOKEN, DISPATCHER_PORT

logger = logging.getLogger(__name__)


BROKER_HOST = 'localhost'
DISPATCHER_LISTEN_TIMEOUT = 0.01

log_file_formatter = None
cur_log_handler = None
cur_artifacts_path = None

task_queue = compose_queue(RoutingKeys.TASK)


def flush_queue(broker: str,
                queue: dict = task_queue,
                assert_non_empty: bool = True):
    with Broker(broker) as br:
        br.connect()
        br.declare(queue)
        br._inactivity_timeout = 0.1  # seconds
        empty = True
        logger.info(f'Flushing queue: {queue}')
        for task in br.pulling_generator():
            empty = False
            br.set_task_done(task)
        if assert_non_empty:
            assert empty, f'Flushed queue {queue} is not empty'


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
    with Broker(BROKER_HOST) as broker:
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
        sleep(10)
    client.broker.connect()
    client.broker.declare()
    client.broker._inactivity_timeout = 10 * SECOND
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
            input_queue = network_client.broker.input_queue
        else:
            return
    flush_queue(host, input_queue)


@pytest.fixture()
def network_client_on_dispatcher(dispatcher, network_client: NetworkClient):
    while not network_client.get_client_queues():
        sleep(10)
    network_client.broker.connect()
    network_client.broker.declare()
    network_client.broker._inactivity_timeout = 0.1 * SECOND
    yield network_client


@pytest.fixture()
def network_client_service(network_client_on_dispatcher: NetworkClient):
    def processing_loop():
        logger.debug('Network Task processing loop is started')
        while active:
            pending_task = next(client.pending_tasks)
            if pending_task:
                client.push_task_to_network(pending_task)
            processed_task = next(client.task_results)
            if processed_task:
                client.append_task_result_to_db(processed_task)
            logger.debug('Processing cycle finished')
    client = network_client_on_dispatcher
    active = True
    listener = Thread(target=processing_loop)
    listener.start()
    yield client
    active = False
    listener.join()


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
