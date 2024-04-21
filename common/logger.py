import datetime as dt
import common.timings as tm

app_log_file = 'common/logger.txt'

def now_datetime():
    log_datetime = tm.now_basic_bare()    
    return log_datetime

def now_timestamp():
    log_datetime = tm.now_basic_bare()
    log_timestamp = log_datetime.strftime("%Y-%m-%d %H:%M:%S.%f")
    return log_timestamp

def log_message(message):
    log_timestamp = now_timestamp()
    log_message = f"{log_timestamp}: {message}\n"
    with open(app_log_file, 'a') as file:
        file.write(log_message)

def log_duration_start(function_name):
    log_start_time = now_datetime()
    log_start_timestamp = now_timestamp()
    log_message = f"{log_start_timestamp}: {function_name} STARTS\n"
    with open(app_log_file, 'a') as file:
        file.write(log_message)
    return function_name, log_start_time

def log_duration_end(function_info):
    returned_function_name = function_info[0]
    returned_log_start_time = function_info[1]

    log_end_time = now_datetime() 
    log_end_timestamp = now_timestamp() 
    log_start_time = returned_log_start_time
    
    function_duration = log_end_time - log_start_time
    
    log_message_end = f"{log_end_timestamp}: {returned_function_name} ENDS \n"
    log_function_duration = f"{log_end_timestamp}: {returned_function_name} TOOK {function_duration}\n"
    with open(app_log_file, 'a') as file:
        file.write(log_message_end)
        file.write(log_function_duration)
        return log_end_time