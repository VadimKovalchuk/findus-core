import logging

from client.client import Client
from task.lib.db import DatabaseMixin

logger = logging.getLogger(__name__)


class NetworkClient(DatabaseMixin):
    def __init__(self,
                 name: str = 'findus-core',
                 dsp_host: str = 'dispatcher',
                 dsp_port: int = 9999,
                 token: str = 'docker'):
        self.db_connected = False
        self.dcn = Client(name, token, dsp_host, dsp_port)

    def __enter__(self):
        self.dcn.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.dcn.__exit__()
