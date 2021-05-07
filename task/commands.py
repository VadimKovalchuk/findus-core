from copy import deepcopy


template = {
    'dcn_task': False,
    'run_on_start': '',
    'child_tasks': [],
    'run_on_done': ''
}


update_all = deepcopy(template)
update_all['child_tasks'] = [
    'update_ticker_list',
    # 'update_all_daily_parameters',
    # 'update_all_fundamental_parameters'
]


update_ticker_list = deepcopy(template)
update_ticker_list['child_tasks'] = [
    'update_sp500_ticker_list',
    'update_sp400_ticker_list',
    'update_sp600_ticker_list',
]  # NOTE: In case if new ticker found call get_full_ticker_data shell be added
update_ticker_list['run_on_done'] = 'new_tickers_processing'


update_sp500_ticker_list = deepcopy(template)
update_sp500_ticker_list['dcn_task'] = True
update_sp500_ticker_list['module'] = 'findus-edge.tickers'
update_sp500_ticker_list['function'] = 'get_sp500_ticker_list'
update_sp500_ticker_list['run_on_done'] = 'process_ticker_list'


update_sp400_ticker_list = deepcopy(update_sp500_ticker_list)
update_sp400_ticker_list['function'] = 'get_sp400_ticker_list'


update_sp600_ticker_list = deepcopy(update_sp500_ticker_list)
update_sp600_ticker_list['function'] = 'get_sp600_ticker_list'


append_all_daily_parameters = deepcopy(template)
append_all_daily_parameters['run_on_start'] = 'daily_ticker_schedule'


append_ticker_daily = deepcopy(template)
append_ticker_daily['child_tasks'] = [
    'append_daily_history',
    # 'append_daily_fundamental',
]


update_all_fundamental_parameters = deepcopy(template)
update_all_fundamental_parameters['run_on_done'] = 'append_fundamentals'


get_full_ticker_data = deepcopy(template)
get_full_ticker_data['child_tasks'] = [
    'get_full_daily_history',
]


get_full_daily_history = deepcopy(template)
get_full_daily_history['dcn_task'] = True
get_full_daily_history['module'] = 'findus-edge.yahoo'
get_full_daily_history['function'] = 'ticker_history'
get_full_daily_history['run_on_start'] = 'convert_args_for_dcn'
get_full_daily_history['run_on_done'] = 'append_daily_data'


append_daily_history = deepcopy(template)
append_daily_history['dcn_task'] = True
append_daily_history['module'] = 'findus-edge.yahoo'
append_daily_history['function'] = 'ticker_history'
append_daily_history['run_on_start'] = 'daily_collection_start_date'
append_daily_history['run_on_done'] = 'append_daily_data'


commands = {
    'update_all': update_all,
    'update_ticker_list': update_ticker_list,
    'update_sp500_ticker_list': update_sp500_ticker_list,
    'update_sp400_ticker_list': update_sp400_ticker_list,
    'update_sp600_ticker_list': update_sp600_ticker_list,
    'append_all_daily_parameters': append_all_daily_parameters,
    'append_ticker_daily': append_ticker_daily,
    # 'update_all_fundamental_parameters': update_all_fundamental_parameters
    'get_full_ticker_data': get_full_ticker_data,
    'get_full_daily_history': get_full_daily_history,
    # 'get_full_quarterly_history': get_full_quarterly_history,
    'append_daily_history': append_daily_history,
}
