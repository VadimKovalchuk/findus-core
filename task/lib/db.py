import logging
from time import sleep

from django.db import connection, OperationalError

logger = logging.getLogger('task_processor')


def wait_for_db_active():
    logger.info('Waiting for database')
    db_conn = None
    while not db_conn:
        try:
            connection.ensure_connection()
            db_conn = True
        except OperationalError:
            logger.info('Database unavailable, waiting 1 second...')
            sleep(1)
    logger.info('Database connection reached')


class DatabaseMixin:

    def wait_for_db(self, retry: bool = True, timeout: int = 10):
        if not self.db_connected:
            logger.info('Waiting for database')
        else:
            logger.info('Validating db connection')
        self.db_connected = False
        retry_left = 10  # TODO: Move to sutable place
        while not self.db_connected and retry_left > 0:
            try:
                connection.ensure_connection()
                self.db_connected = True
                break
            except OperationalError:
                logger.info(f'Database unavailable, waiting {timeout} seconds')
                if not retry:
                    break
                sleep(timeout)
        logger.info('Database connection reached')
