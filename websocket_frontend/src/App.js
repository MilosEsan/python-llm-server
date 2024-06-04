import React, { useState, useEffect } from 'react';
import Chat from './components/Chat';
import ModelSelection from './components/ModelSelection';
import './App.css'; 
import 'bootstrap/dist/css/bootstrap.min.css';
import 'bootstrap/dist/js/bootstrap.bundle.min.js';

const App = () => {
  const [socket, setSocket] = useState(null);
  const [messages, setMessages] = useState([]);
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState("");
  const [currentModel, setCurrentModel] = useState("");
  const [isLoadingModel, setIsLoadingModel] = useState(false);

  //auth process place
  localStorage.setItem('user_name', 'Ryan Graff')
  localStorage.setItem('user_image_url', null)


  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8765');


    ws.onmessage = (event) => {
      const serverMsgs = JSON.parse(event.data);
      console.log(event)

      if (serverMsgs.type === "server_state") {
        setModels(serverMsgs.message.available_models);
        setCurrentModel(serverMsgs.message.current_model);
        setSelectedModel(serverMsgs.message.current_model);
        setIsLoadingModel(serverMsgs.message.llm_state === "CHANGING_MODEL");
      } else if (serverMsgs.type === "server_state_update") {
        setCurrentModel(serverMsgs.message.current_model);
        setIsLoadingModel(serverMsgs.message.state === "CHANGING_MODEL");
      } else if (serverMsgs.type === "query_request_update" || serverMsgs.type === "query_response") {
        setMessages((prevMessages) => [
          ...prevMessages,
          { type: 'server', text: serverMsgs.message.update || serverMsgs.message.response, last_token: serverMsgs.message.last_token }
        ]);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    setSocket(ws);

    return () => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    };
  }, []);

  const sendMessage = (query, fileData) => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      const message = {
        type: 'query_request',
        message: {
          query,
          model: selectedModel,
          parameters: {},
          ...(fileData ? { file_data: fileData } : { file_data: 'base64 string' }),
        },
      };
      setMessages((prevMessages) => [
        { type: 'user', text: query },
        ...prevMessages
      ]);
      socket.send(JSON.stringify(message));
    } else {
      console.error('WebSocket is not open:', socket ? socket.readyState : 'No socket');
    }
  };

  return (
    <div className="container">
      <header>
        <div className='header-container'>
          <h3>New Chat</h3>
          <nav>
            <div className="nav nav-tabs" id="nav-tab" role="tablist">
              <button className="nav-link active" id="nav-home-tab" data-bs-toggle="tab" data-bs-target="#nav-home" type="button" role="tab" aria-controls="nav-home" aria-selected="true">Chat</button>
              <button className="nav-link" id="nav-profile-tab" data-bs-toggle="tab" data-bs-target="#nav-profile" type="button" role="tab" aria-controls="nav-profile" aria-selected="false">Results</button>
            </div>
          </nav>
        </div>
      </header>
      <div className="tab-content" id="nav-tabContent">
        <div className="tab-pane fade show active" id="nav-home" role="tabpanel" aria-labelledby="nav-home-tab">
          <div className='model-selection-container'>
            <ModelSelection
              models={models}
              selectedModel={selectedModel}
              setSelectedModel={setSelectedModel}
              className={'model_selection'}
              currentModel={currentModel}
              isLoadingModel={isLoadingModel}
            />
          </div>
          <div>
            <button type="button" className="btn btn-secondary new-chat-button">NEW CHAT</button>
            <Chat messages={messages} sendMessage={sendMessage} />
          </div>
        </div>
        <div className="tab-pane fade text-center" id="nav-profile" role="tabpanel" aria-labelledby="nav-profile-tab">Content under preparation</div>
      </div>
    </div>
  );
};

export default App;
