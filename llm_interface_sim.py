import utils
from time import sleep
from loguru import logger
import server_state

llm = None
model_family = ""
model_category = ""
vectordb = None

def load_llm(model_name:str): #TODO what to do when error occurs
    global llm
    global model_family
    global model_category
    parameters = None
    try:
        parameters = server_state.config['models'][model_name]['parameters']
        model_family = server_state.config['models'][model_name]['family']
        model_category = server_state.config['models'][model_name]['specialization']
        if(parameters):
            path = server_state.config['model_directory'] + "/" + model_name + ".gguf"
            logger.info(f"Loading model from path: {path}")
            logger.info(f"Info: Loading model({model_name}) with following parameters: n_ctx={parameters['n_ctx']}, n_threads={parameters['n_threads']}, n_gpu_layers={parameters['n_gpu_layers']}")
        else:
            logger.error(f'Model {model_name} doesnt have configuration.')
    except ValueError as e:
        logger.info(f"Llm config json parsing error: {e}")

def unload_llm():
    global llm
    llm = None
    
def change_llm(model_name:str):
    unload_llm()
    load_llm(model_name)
    #Moved simulation her not to trigger on initial llm loading
    logger.info(f"Loading model simulation started. Sleeping for {server_state.change_model_time}s")
    sleep(server_state.change_model_time)
    logger.info(f"Loading model simulation finishd.")

def retreiveFromRag(query:str, enable_print:bool, num_results:int = 3):
    logger.warning("Rag retreival not implemented yet")
    
def queryLlm(query:str, file:str, enable_rag:bool):
    global llm
    global model_family
    global model_category
    
    match model_family:
        case "llama":
            return llama3(query, file, enable_rag)
        case "mixtral":
            return mixtral(query, file, enable_rag)

def mixtral(query:str, file:str, use_rag:bool):
    global llm
    information = ""
    if(use_rag):
        information = "\n\n".join(retreiveFromRag(query, True, 3))
    
    header = "You are a helpful Serbian Computer Science expert. Your users are asking questions about computer science in Serbian language."
    query_with_rag = ""
    file_text = ""
    if(file):
        file_text = utils.parseBase64PdfText(file)
    if(file and use_rag):
        header = header + " Answer following question using only provided information and attached file. Answer only in Serbian language."
        query_with_rag = f"{header}\nQuestion: {query}\nAttached File:{file_text}\nInformation: {information}"
    elif(file and not use_rag):
        header = header + " Answer following question using your knowledge and attached file. Answer only in Serbian language."
        query_with_rag = f"{header}\nAttached File:{file_text}\nQuestion: {query}\n"
    elif(not file and use_rag):
        header = header + "Answer following question using only provided information. Answer only in Serbian language."
        query_with_rag = f"{header}\nQuestion: {query}\nInformation: {information}"
    else:
        header = header + "Answer following question using your knwoledge. Answer only in Serbian language."
        query_with_rag = f"{header}\nQuestion: {query}"
        
    logger.info(f"Querying mixtral llm with following formatted query:\n[INST] {utils.pruneLongTextForPrinting(query_with_rag)} [/INST]")
    logger.info(f"Querying mixtral llm with following parameters:\nmax_tokens=1024, stop=[\"</s>\"], echo=True, stream=True")
    
    return llm_simulation(query, file)

def llama3(query:str, file:str, use_rag:bool):
    global llm
    information = ""
    if(use_rag):
        information = "\n\n".join(retreiveFromRag(query, True, 3))
    
    system = "You are a helpful Serbian Computer Science expert. Your users are asking questions about computer science in Serbian language."
    query_with_rag = ""
    
    file_text = ""
    if(file):
        file_text = utils.parseBase64PdfText(file)
    if(file and use_rag):
        system = system + " Answer following question using only provided information and attached file. Answer only in Serbian language."
        query_with_rag = f"Question: {query}\nAttached File:{file_text}\nInformation: {information}"
    elif(file and not use_rag):
        system = system + " Answer following question using your knowledge and attached file. Answer only in Serbian language."
        query_with_rag = f"Attached File:{file_text}\nQuestion: {query}\n"
    elif(not file and use_rag):
        system = system + "Answer following question using only provided information. Answer only in Serbian language."
        query_with_rag = f"Question: {query}\nInformation: {information}"
    else:
        system = system + "Answer following question using your knwoledge. Answer only in Serbian language."
        query_with_rag = f"Question: {query}"
    
    prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
                {system}<|eot_id|><|start_header_id|>user<|end_header_id|>
                {query_with_rag}<|eot_id|><|start_header_id|>assistant<|end_header_id|>"""
    
    logger.info(f"Querying llama3 llm with following formatted query:\n{utils.pruneLongTextForPrinting(prompt)}")
    logger.info(f"Querying llama3 llm with following parameters:\nmax_tokens=1024, stop=[\"<|eot_id|>\"], echo=True, stream=True")
    
    return llm_simulation(query, file)

def llm_simulation(query : str, file : str):
    reply = f"Your query was: {query}; You wanted to run this query on {server_state.state['current_model']} model."
    if file == None:
        reply = reply + " You didnt provide file with query."
    else:
        reply = reply + f" You provided file with query: {utils.parseBase64PdfText(file)}"
    split_reply = reply.split()

    # loop until counter is less than n
    for idx, word in enumerate(split_reply):
        sleep(server_state.time_between_tokens)
        # Simulate token gneration by sending text word by word. Add spaces to words except for last word.
        if(idx == (len(split_reply) - 1)):
            yield {'choices':[{'text':word}]}
        else:
            yield {'choices':[{'text':(word + " ")}]}