"use client";

import { useEffect, useState } from "react";

export default function Home() {
  const [socket, setSocket] = useState<WebSocket | null>(null); //websocket connection instance
  const [messages, setMessages] = useState<string[]>([]); //all messages from backend
  const [input, setInput] = useState(""); //input from frontend

  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8000/ws"); //connect to fastapi websocket endpoint

    ws.onopen = () => {
      //run when connects
      console.log("Connected to backend");
    };

    ws.onmessage = (event) => {
      //run when backend send sth
      setMessages((prev) => [...prev, event.data]);
    };

    setSocket(ws); //for sending msg to backend

    return () => {
      ws.close(); //close connection when page refreshes
    };
  }, []);

  const sendMessage = () => {
    if (socket && input) {
      socket.send(input); //send msg to backend thru ws
      setInput(""); //clear data
    }
  };

  return (
    <div style={{ padding: 20 }}>
      <h1>SupportScribe WebSocket Test</h1>
      {/*message sending to backend */}
      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="Type message"
      />
      <button onClick={sendMessage}>Send</button>
      {/*messages received from backend */}
      <div>
        {messages.map((msg, index) => (
          <p key={index}>{msg}</p>
        ))}
      </div>
    </div>
  );
}
