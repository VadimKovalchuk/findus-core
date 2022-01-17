import os

import yaml

from common.logging_tools import get_datetime_stamp

with open("settings.yaml", 'r') as fh:
    try:
        yaml_dict = yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        raise SystemError('YAML settings load failed') from exc


instance_type = os.getenv('INSTANCE_TYPE', 'docker')
env_db_settings = os.getenv('DB_HOST', '127.0.0.1')

db_host = 'database' if instance_type == 'docker' else env_db_settings
db_creds = yaml_dict['database']
log_path = f'/src/log/django/log_{get_datetime_stamp()}.txt' if instance_type == 'docker' else f'log/log_{get_datetime_stamp()}.txt'

secret_key = yaml_dict['django']['secret_key']
