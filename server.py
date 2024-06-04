import asyncio
import websockets
import uuid
import threading
import argparse
from time import sleep
from queue import Queue
from pathlib import Path
import server_state
import json_reqest_helper
import utils
from loguru import logger
import signal
from functools import partial
import sys

# Dictionary to store session IDs and corresponding WebSocket objects
sessions = {}
# Needed because of using threading and asyncio
loop = None

# Request queue
rqueue = Queue()

parser = argparse.ArgumentParser()
parser.add_argument("-p", "--port", help="Port number for the server to use. (default: %(default)d)", default=8765, type=int)
parser.add_argument("-hb", "--heartbeat_interval", help="Time between hearbeats to clients. (default: %(default)f)", default=20.0, type=float)
parser.add_argument("-du", "--disable_user_tracking", help="Disable active user tracking.", action="store_true")
parser.add_argument("-s", "--simulation_mode", help="Enable simulation mode that simulates all llm calls and disables hardware requirements.", action="store_true")
parser.add_argument("-c", "--change_model_time", help="Time for simulating model change in seconds. (default: %(default)f)", default=10.0, type=float)
parser.add_argument("-t", "--time_between_tokens", help="Time for pause between sending tokens in seconds. This is simulating llm token generation. (default: %(default)f)", default=0.3, type=float)
parser.add_argument("-m", "--model_directory", help="Directory containing llamacpp models. Overwrites llamacpp_config.json model_directory. (default: llamacpp_configs.model_directory)", type=str)
args = parser.parse_args()

# Import different files depending on if we want to run on radware or simulate, same as regular import it can just be done programatically
llm_interface = None
if(args.simulation_mode):
    llm_interface = utils.importByName("llm_interface_sim")
    logger.info("Using simulation llm module.")
    
else:
    llm_interface = utils.importByName("llm_interface_sim")
    logger.info("Using hardware llm module.")

# Load model configs from config file, check if model gguf file exists
def load_models():
    server_state.config = json_reqest_helper.load_json('llamacpp_configs.json')
    
    if(server_state.config == None):
        logger.critical("Config llamacpp_configs.json empty.")
        exit(1)
    
    # If other model_directory is provided through command line arguments, overwrite existing one
    if(args.model_directory):
        logger.warning(f"Replacing config model directory ({server_state.config['model_directory']}) with directory provided through command line argument ({args.model_directory}).")
        server_state.config['model_directory'] = args.model_directory
    
    # Remove models which dont have llamacpp files
    to_remove = []
    for model, model_config in server_state.config['models'].items():
        file_path =  Path(f"{server_state.config['model_directory']}/{model_config['name']}.gguf")
        if not file_path.is_file():
            to_remove.append(model)
            logger.warning(f"Could not find model {model_config['name']} llama cpp file, removing it from list.")
        else:
            logger.info(f"Model {model_config['name']} llama cpp file found.")
    for model in to_remove:
        del server_state.config['models'][model]

    if len(server_state.config['models'].values()) == 0:
        logger.critical(f"No model files found in folder {server_state.config['model_directory']}.") #TODO maybe not critical, just create dummy files
        exit(1)
    
    # Update state with list of available models
    server_state.state['available_models'] = list(server_state.config['models'].keys())
    
    # Set initial model, check if it was removed
    if server_state.config['default_model'] in server_state.config['models']:
        logger.info(f"Initial model set to {server_state.config['default_model']}.")
    else:  
        logger.error(f"Default model {server_state.config['default_model']} does not exist in config file. Initial model set to {list(server_state.config['models'].values())[0]['name']}.")
        server_state.config['default_model'] = list(server_state.config['models'].values())[0]['name']

    # Load initial model onto gpu
    logger.info(f"Loading inital model {server_state.config['default_model']}.")
    server_state.state['current_model'] = server_state.config['default_model']
    llm_interface.load_llm(server_state.state['current_model'])

def switch_model(new_model : str):
    #broadcast to all clients that model is cahnging -> current model changes, grays out and spinner appears
    #change model
    #broadcast to all clients that model changed -> current model enables and spinner disappears
    server_state.state['current_model'] = new_model
    server_state.state['llm_state'] = "CHANGING_MODEL"
    broadcast(json_reqest_helper.server_state_upate_json(server_state.StateChange.CHANGING_MODEL))
    #change model here
    llm_interface.change_llm(server_state.state['current_model'])
    broadcast(json_reqest_helper.server_state_upate_json(server_state.StateChange.MODEL_CHANGED))


def query_request_handler(query : str, model : str, file_data : str, parameters : dict):
    #There should be enable rag switch and llm model that is selected
    #Check if model is the one that is requested, if not call change model
    #Call llm query function (with or without rag)
    #Return message to specific client
    if model != server_state.state['current_model']:
        logger.info(f"Client asked to run query on model that is not loaded. Requested {model}, loaded {server_state.state['current_model']}. Changing model.")
        switch_model(model)
    
    # Not used currently, might look something like this
    rag_database = False
    if parameters != None:
        rag_database = parameters.get("use_rag")
        
    return llm_interface.queryLlm(query, file_data, rag_database)
    
def request_handling_loop():
    global loop
    while True:
        # Get new request from qeue
        queued_request = rqueue.get()
        request = queued_request['request']
        client = queued_request['client']
        request_type = request['type']

        printable_request = utils.pruneLargeObjectForPrinting(request)
        logger.info(f"Processing request from queue: {printable_request}")
        send_threadsafe(client, json_reqest_helper.queue_position_update_json(0))
                        
        # Update clients with new queue position
        for idx, elem in enumerate(list(rqueue.queue)):
            send_threadsafe(elem['client'], json_reqest_helper.queue_position_update_json(idx + 1))
            
        # Process the request
        if(request_type == "query_request"):    # Request for 
            #print(f"Processing query from client {client}: {printable_request}")
            client_request = request['message']
            reply = query_request_handler(client_request['query'], client_request['model'], client_request.get('file_data'), client_request['parameters'])
            # Run in for loop to stream tokens - Delay by one with prev token so we know when we are sending last token.
            prev_token = None
            for llm_reply in reply:
                if(prev_token != None):
                    send_threadsafe(client, json_reqest_helper.query_response_json(prev_token, False))
                prev_token = llm_reply['choices'][0]['text']
            send_threadsafe(client, json_reqest_helper.query_response_json(prev_token, True))
                
        elif(request_type == "add_to_rag"):
            # Placeholder
            print("Rceived rag request. Not yet implemented.")


def heartbeat_loop():
    global loop
    while True:
        logger.info(f"Sedning heartbeat to all clients. Interval({args.heartbeat_interval} seconds)")
        broadcast(json_reqest_helper.heartbeat_json())
        sleep(args.heartbeat_interval)
        
def send_threadsafe(client : str, message : str):
    asyncio.run_coroutine_threadsafe(websocket_send(client, message), loop)

def broadcast(message : str):
    for client in sessions.keys():
         asyncio.run_coroutine_threadsafe(websocket_send(client, message), loop)

async def websocket_send(client:str, message:str):
    try:
        await sessions[client].send(message)
    except websockets.exceptions.ConnectionClosedOK as e:
        logger.info(f"Client {client} disconnected gracefully.")
        await disconnect_handler(client)
    except websockets.exceptions.ConnectionClosedError as e:
        logger.warning(f"Client {client} disconnected with error: {e}")
        await disconnect_handler(client)
    except websockets.exceptions.ConnectionClosed as e:
        logger.warning(f"Client {client} disconnected with unknown error: {e}")
        await disconnect_handler(client)

async def disconnect_handler(client:str):
    logger.info(f"Client {client} disconnected. Sending broadcast to all clients.")
    # Remove the session ID from the dictionary upon disconnection
    del sessions[client]
    server_state.state['current_active_clients'] -= 1
    if(not args.disable_user_tracking):
        broadcast(json_reqest_helper.server_state_upate_json(server_state.StateChange.ACTIVE_CLIENTS_NUMBER))

async def handle_client(websocket, path):
    global loop 
    loop = asyncio.get_running_loop()
    
    # Generate a unique session ID for the client
    session_id = str(uuid.uuid4())
    
    try:
        # Broadcast new active clients number to connected clients
        server_state.state['current_active_clients'] += 1
        if(not args.disable_user_tracking):
            broadcast(json_reqest_helper.server_state_upate_json(server_state.StateChange.ACTIVE_CLIENTS_NUMBER))
        
        # Store the WebSocket object with its session ID
        sessions[session_id] = websocket
        
        logger.info(f"New client connected. Session ID: {session_id}")
        await websocket.send(json_reqest_helper.server_state_json())
        
        # Main loop to handle communication with the client
        async for message in websocket:
            logger.info(f"Received message from client {session_id}: {utils.pruneLongTextForPrinting(message)}")
            # Create request from client message and put into synchronization queue
            request = json_reqest_helper.parse_client_request(message)
            queue_request = {'client':session_id, 'request':request}
            await websocket.send(json_reqest_helper.queue_position_update_json(rqueue.qsize() + 1))
            rqueue.put(queue_request)
            logger.info(f"Enqueued request from client {session_id}: {utils.pruneLargeObjectForPrinting(request)}")
    except websockets.exceptions.ConnectionClosedOK as e:
        logger.info(f"Client {session_id} disconnected gracefully.")
        await disconnect_handler(session_id)
    except websockets.exceptions.ConnectionClosedError as e:
        logger.warning(f"Client {session_id} disconnected with error: {e}")
        await disconnect_handler(session_id)
    except websockets.exceptions.ConnectionClosed as e:
        logger.warning(f"Client {session_id} disconnected with unknown error: {e}")
        await disconnect_handler(session_id)

async def start_server():
    # Initial setup of the server
    load_models()
    server_state.state['llm_state'] = "READY"
    server_state.state['current_active_clients'] = 0
    
    # For sim
    server_state.time_between_tokens = args.time_between_tokens
    server_state.change_model_time = args.change_model_time

    # Start request handling thread
    request_thread = threading.Thread(target=request_handling_loop)
    request_thread.start()
    
    # Start heartbeat thread
    heartbeat_thread = threading.Thread(target=heartbeat_loop)
    heartbeat_thread.start()
    
    # Start the WebSocket server
    async with websockets.serve(handle_client, "localhost", args.port, ping_interval=20, ping_timeout=10):
        logger.info("Server started.")
        await asyncio.Future()  # Run forever
    request_thread.join()

def stop_server():
    global loop
    logger.info("Unloading LLM Model from GPU.")
    llm_interface.unload_llm()
    sys.exit(1)
    
def catchSignint():
    original_sigint = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, partial(exit_gracefully, original_sigint))

def exit_gracefully(original_sigint, signum, frame):
    # restore the original signal handler as otherwise evil things will happen
    # in raw_input when CTRL+C is pressed, and our signal handler is not re-entrant
    signal.signal(signal.SIGINT, original_sigint)
    try:
        logger.info("Caught SIGINT. Trying to stop the server.")
        stop_server()
        logger.info("Server stopped successfully.")
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(1)
    # restore the exit gracefully handler here
    sys.exit(1) 
    signal.signal(signal.SIGINT, partial(exit_gracefully, original_sigint))
        
# Start the server
catchSignint()
asyncio.run(start_server())