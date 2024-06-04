import asyncio
import websockets
import threading
import aioconsole
import json
import base64
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("-ip", "--ip_address", help="IP address of the server.", default="localhost", type=str)
parser.add_argument("-p", "--port", help="Port of the server.", default=8765, type=int)
parser.add_argument("-t", "--testing_mode", help="Enable printing of full reply jsons", action="store_true")
args = parser.parse_args()


attached_file = False           # Set to true if there is file attached
attached_file_encoded = ""      # Countains base64 encoded string of attached file
receiving_query_reply = False   # True if client is in the process of receiving query reply word by word
server_changing_model = False   # True if server is currently changing model, not used in python client

async def send_messages(websocket):
    while True:
        global attached_file
        global attached_file_encoded
        # Provide two options to the user, he can choose to send query or to attach file
        option = await aioconsole.ainput("Enter option [query(to send query) file(to attach file) close(to close connection)]: ")
        if(option == "query"):
            # User wants to send query, ask for query string
            message = await aioconsole.ainput("Enter a message to send to the server: ")
            # Try to parse it as json to check if its valid json file then send it to the server
            try:
                json_message = json.loads(message)
                # In case there is attached file add "file_data" field to json containing base64 encoded file
                if(attached_file):
                    json_message["message"]["file_data"] = attached_file_encoded
                # Send query to the server
                await websocket.send(json.dumps(json_message))
                json_message["message"]["file_data"] = "Large base64 encoded string" #Only for printing
                print(f"Sent message to server: {json.dumps(json_message)}")
            except ValueError as e:
                print(f"Could not parse query as a json: {e}")
        elif(option == "file"):
            # User wants to attach file, ask for file path
            path = await aioconsole.ainput("Enter file path: ")
            # Try to read file and enccode as base64
            try:
                with open(path, 'rb') as file_to_attach:
                    # Encode as base64, base64.b64encode returns bytes for some reason so decode() has to be called to convert to string
                    attached_file_encoded = base64.b64encode(file_to_attach.read()).decode()
            except IOError as e:
                print(f"Error reading file {path}: {e}")
            attached_file = True
        elif(option == "close"):
            print(f"Closing conncion.")
            await websocket.close()
        else:
            print(f"Option {option} not recognized.")

async def receive_messages(websocket):
    global args
    global receiving_query_reply
    global server_changing_model
    while True:
        response = await websocket.recv()
        if (args.testing_mode):
            print(f"Received message from server: {response}")
            try:
                json_response = json.loads(response, strict=False)
                print(f"Succesfully parsed as json: {json_response}")
            except ValueError as e:
                print(f"Error, cannot parse json string: {e}")
        else:
            try:
                json_response = json.loads(response, strict=False)
                if (json_response['type'] == "query_request_update"):
                    print(f"Request update: {json_response['message']['update']}")
                elif (json_response['type'] == "query_response"):
                    if (receiving_query_reply):
                        print(json_response['message']['token'], end='', flush=True)
                    else:
                        receiving_query_reply = True
                        print(f"LLM Response: {json_response['message']['token']}", end='', flush=True)
                    if(json_response['message']['last_token']):
                        receiving_query_reply =  False
                        print("")
                elif (json_response['type'] == "server_state_update"):
                    if(json_response['message']['update_type'] == "model_change"):
                        if(json_response['message']['state'] == "CHANGING_MODEL"):
                            print(f"Server started changing model to {json_response['message']['current_model']}")
                        elif(json_response['message']['state'] == "READY"):
                            print(f"Server finished changing model to {json_response['message']['current_model']}")
                        else:
                            print(f"Server in unknown state: {json_response['message']['state']}")
                    elif(json_response['message']['update_type'] == "active_client_update"):
                        print(f"Active clients number update: {json_response['message']['current_active_clients']}")
                    else:
                        print(f"Server sent unknown status update type: {json_response['message']['update_type']}")
                elif (json_response['type'] == "server_state"):
                    server_state_string = ""
                    if(json_response['message']['llm_state'] == "READY"):
                         server_state_string = f"Currently loaded model is {json_response['message']['current_model']}. Server llm is ready."
                    elif(json_response['message']['llm_state'] == "CHANGING_MODEL"):
                         server_state_string = f"Server is currently loading new model: {json_response['message']['current_model']}"
                    else:
                        server_state_string = f"Currently loaded model is {json_response['message']['current_model']}. Server llm is in unknown state {json_response['message']['llm_state']}."
                    server_state_string += f" Number of active clients connected to server is {json_response['message']['current_active_clients']}."
                    print("Received initial server info:")
                    print("   Avilable models on the server:")
                    for model in json_response['message']['available_models']:
                        print(f"      {model}")
                    print(f"   {server_state_string}")
                elif (json_response['type'] == "heartbeat"):
                    print(f"Received heartbeat from server: server time({json_response['message']['server_time']})")
                else:
                    print(f"Received uknown message type from server: {json_response}")
            except ValueError as e:
                print(f"Error, cannot parse json string: {response} error:{e}")
       

async def connect_and_run():
    global args
    async with websockets.connect(f'ws://{args.ip_address}:{args.port}') as websocket:
        # Start the sending and receiving threads
        receive_task = asyncio.create_task(receive_messages(websocket))
        send_task = asyncio.create_task(send_messages(websocket))
        await asyncio.gather(receive_task, send_task)

def main():
    asyncio.run(connect_and_run())

if __name__ == "__main__":
    main()
