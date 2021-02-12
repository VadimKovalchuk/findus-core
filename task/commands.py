from copy import deepcopy

from task.processing import append_daily_data, append_fundamentals,\
    process_ticker_list


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
]


update_sp500_ticker_list = deepcopy(template)
update_sp500_ticker_list['dcn_task'] = True
update_sp500_ticker_list['module'] = 'findus-collector.tickers'
update_sp500_ticker_list['function'] = 'get_sp500_ticker_list'
update_sp500_ticker_list['run_on_done'] = process_ticker_list.__name__


update_sp400_ticker_list = deepcopy(update_sp500_ticker_list)
update_sp400_ticker_list['function'] = 'get_sp400_ticker_list'


update_sp600_ticker_list = deepcopy(update_sp500_ticker_list)
update_sp600_ticker_list['function'] = 'get_sp600_ticker_list'


update_all_daily_parameters = deepcopy(template)
update_all_daily_parameters['dcn_task'] = True
update_all_daily_parameters['module'] = 'findus-collector.yahoo'
update_all_daily_parameters['function'] = 'ticker_history'
update_all_daily_parameters['arguments'] = '{"ticker": "MSFT", "start": "2021-01-01"}'
update_all_daily_parameters['run_on_done'] = append_daily_data.__name__


update_all_fundamental_parameters = deepcopy(template)
# update_all_fundamental_parameters['dcn_task'] = True
update_all_fundamental_parameters['run_on_done'] = append_fundamentals.__name__


commands = {
    'update_all': update_all,
    'update_ticker_list': update_ticker_list,
    'update_sp500_ticker_list': update_sp500_ticker_list,
    'update_sp400_ticker_list': update_sp400_ticker_list,
    'update_sp600_ticker_list': update_sp600_ticker_list,
    # 'update_all_daily_parameters': update_all_daily_parameters,
    # 'update_all_fundamental_parameters': update_all_fundamental_parameters
}
