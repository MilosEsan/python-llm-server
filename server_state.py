from enum import Enum
import sys
import os
from loguru import logger

# State of the server, ui uses this for dropdowns
state = {} #current model, available models, changing model currently

# List of the models and their configurations, server uses this for loading models
config = None

# Set of defined client requests
client_requests_set = {"query_request", "error"}

class StateChange(Enum):
    CHANGING_MODEL = 1
    MODEL_CHANGED = 2
    ACTIVE_CLIENTS_NUMBER = 3
    
# Server command line arguments for simulation
time_between_tokens = 0.0
change_model_time = 0.0

# Setup logger
logger.remove(0)
logger.add(sys.stderr, level="INFO")
logger.add("logs/webserver.log", 
           format="{time:MMMM D, YYYY > HH:mm:ss!UTC} | {level} | {message} | {extra}",
           rotation="1 hour", retention="7 days",
           level="INFO")