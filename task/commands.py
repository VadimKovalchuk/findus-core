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


update_all_daily_parameters = deepcopy(template)
update_all_daily_parameters['dcn_task'] = True
update_all_daily_parameters['module'] = 'findus-edge.yahoo'
update_all_daily_parameters['function'] = 'ticker_history'
update_all_daily_parameters['arguments'] = '{"ticker": "MSFT", "start": "2021-01-01"}'
update_all_daily_parameters['run_on_done'] = 'append_daily_data'


update_all_fundamental_parameters = deepcopy(template)
# update_all_fundamental_parameters['dcn_task'] = True
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


commands = {
    'update_all': update_all,
    'update_ticker_list': update_ticker_list,
    'update_sp500_ticker_list': update_sp500_ticker_list,
    'update_sp400_ticker_list': update_sp400_ticker_list,
    'update_sp600_ticker_list': update_sp600_ticker_list,
    # 'update_all_daily_parameters': update_all_daily_parameters,
    # 'update_all_fundamental_parameters': update_all_fundamental_parameters
    'get_full_ticker_data': get_full_ticker_data,
    'get_full_daily_history': get_full_daily_history,
    # 'get_full_quarterly_history': get_full_quarterly_history,
}
