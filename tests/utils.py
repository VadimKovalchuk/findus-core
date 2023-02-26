from datetime import datetime, timedelta


def get_date_by_delta(time_delta: timedelta):
    date_obj = datetime.today() - time_delta
    return date_obj.strftime('%Y-%m-%d')
