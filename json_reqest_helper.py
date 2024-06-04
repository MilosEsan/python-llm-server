import json
from server_state import client_requests_set
from server_state import state
from server_state import StateChange
from loguru import logger
from datetime import datetime

def load_json(file : str) -> dict:
    try:
        with open(file) as f:
            return json.load(f)
    except ValueError as e:
        logger.error(f"Error reading config file {file}: {e}")
        return None
    except IOError as e:
        logger.error(f"Error parsing config file {file} as json: {e}")
        return None
        
def parse_json_string(json_string : str) -> dict:
    try:
        return json.loads(json_string)
    except ValueError as e:
        return json.loads(error_json(e, f"Error parsing json: {json_string}"))
        
def error_json(error_code : str, error_description : str) -> str:
    return (f"{{"
                f"\"type\":\"error\","
                f"\"message\":"
                f"{{\""+\
                    f"\"error\":\"{error_code}\","
                    f"\"description\":\"{error_description}"
                f"}}"
             f"}}")

def parse_client_request(request_string : str) -> dict:
    request_json = parse_json_string(request_string)
    if request_json['type'] in client_requests_set:
        return request_json
    else:
        return json.loads(error_json("Invalid request.", f"Request type {request_json['type']} is not supported by the server."))

def server_state_json() -> str:
    return (f"{{"
                f"\"type\":\"server_state\","
                f"\"message\":{json.dumps(state)}"
             f"}}")
             
def server_state_upate_json(update_type : StateChange) -> str:
    message = ""
    if(update_type == StateChange.CHANGING_MODEL):
        message = f"{{\"update_type\":\"model_change\", \"state\":\"CHANGING_MODEL\", \"current_model\":\"{state['current_model']}\"}}"
    if(update_type == StateChange.MODEL_CHANGED):
        message = f"{{\"update_type\":\"model_change\", \"state\":\"READY\", \"current_model\":\"{state['current_model']}\"}}"
    if(update_type == StateChange.ACTIVE_CLIENTS_NUMBER):
        message = f"{{\"update_type\":\"active_client_update\", \"current_active_clients\":\"{state['current_active_clients']}\"}}"
    return (f"{{"
                f"\"type\":\"server_state_update\","
                f"\"message\":{message}"
             f"}}")
             
def queue_position_update_json(position_in_queue : int) -> str:
    message = ""
    if(position_in_queue == 0):
        message = "Your request is being executed"
    else:
        message = f"Current position in queue: {position_in_queue}"
    return (f"{{"
                f"\"type\":\"query_request_update\","
                f"\"message\":"
                f"{{"
                    f"\"update\":\"{message}\""
                f"}}"
             f"}}")
             
def query_response_json(token: str, last_token : bool) -> str:
    return (f"{{"
                f"\"type\":\"query_response\","
                f"\"message\":"
                f"{{"
                    f"\"token\":\"{token}\","
                    f"\"last_token\":{str(last_token).lower()}"
                f"}}"
             f"}}")
    
def disconnect_json() -> str:
    return (f"{{"
                f"\"type\":\"server_state_update\","
                f"\"message\":{{\"update_type\":\"disconnect\"\"}}"
             f"}}")
    
def heartbeat_json() -> str:
    return (f"{{"
                f"\"type\":\"heartbeat\","
                f"\"message\":{{\"server_time\":\"{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\"}}"
             f"}}")