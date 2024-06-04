// initial test component - could be plugged into App.js, if needed

import React, { useEffect, useState } from 'react';

const WebsocketTest = () => {
  const [socket, setSocket] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [models, setModels] = useState([]);
  let [selectedModel, setSelectedModel] = useState("");

  const connectWebSocket = () => {
    const ws = new WebSocket('ws://localhost:8765');

    ws.onopen = () => {
      console.log('Connected to WebSocket server');
      setIsConnected(true);
      ws.send(JSON.stringify({
        type: 'query_request',
        message: {
          query: 'Hi, this is the query.',
          model: selectedModel,
          parameters: {},
          file_data: 'base64 string',
        }
      }));
    };

    ws.onmessage = (event) => {
      const serverMsgs = JSON.parse(event.data);
      console.log('Received message:', serverMsgs);
      setSelectedModel(serverMsgs.message.current_model)

      console.log(selectedModel)

      const availableModels = serverMsgs.message && serverMsgs.message.available_models;

      if (Array.isArray(availableModels)) {
        setModels([...availableModels]);
      } 

      setMessages((prevMessages) => [...prevMessages, event.data]);
    };

    ws.onclose = (event) => {
      console.log('Disconnected from WebSocket server', event);
      setIsConnected(false);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    setSocket(ws);
  };

  useEffect(() => {
    connectWebSocket();

    return () => {
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.close();
      }
    };
  }, []); 
  
  const sendMessage = () => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      console.log('Sending message to WebSocket server');
      socket.send(JSON.stringify({
        type: 'query_request',
        message: {
          query: 'Hi, this is the query.',
          model: selectedModel || 'mixtral-8x7b-instruct-v0.1.Q4_K_M',
          parameters: {},
          file_data: 'base64 string',
        }
      }));
    } else {
      console.error('WebSocket is not open:', socket ? socket.readyState : 'No socket');
      if (!socket || socket.readyState !== WebSocket.CONNECTING) {
        connectWebSocket();
      }
    }
  };

  const handleModelChange = (event) => {
    setSelectedModel(event.target.value);
  };

  return (
    <div>
      <h1>WebSocket Test</h1>
      <p>Status: {isConnected ? 'Connected' : 'Disconnected'}</p>
      <div>
        <h2>Messages</h2>
        <ul>
          {messages.map((msg, index) => (
            <li key={index}>{msg}</li>
          ))}
        </ul>
      </div>
      <div>
        <h2>Models</h2>
        <select onChange={handleModelChange} value={selectedModel}>
          {models.map((model, index) => (
            <option key={index} value={model}>{model}</option>
          ))}
        </select>
        <button onClick={sendMessage}>
          Send Test Message
        </button>
      </div>
    </div>
  );
};

export default WebsocketTest;