"use client";

import { useEffect, useRef, useState } from "react";

export default function Home() {
  const [socket, setSocket] = useState<WebSocket | null>(null); //websocket connection instance
  const [recording, setRecording] = useState(false); //show start or end button
  const mediaRecordRef = useRef<MediaRecorder | null>(null); //stores media recorder

  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8000/ws"); //connect to fastapi websocket endpoint
    //connect successful
    ws.onopen = () => {
      console.log("Connected to backend");
    };
    setSocket(ws); //set ws for sending data to backend

    return () => {
      ws.close(); //close connection when page refreshes
    };
  }, []);

  const startRecording = async () => {
    //check for ws
    if (!socket) return;
    //browser asks permission for microphone
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true }); //get only microphone access
    const mediaRecorder = new MediaRecorder(stream); //set up recorder by connecting to stream
    mediaRecordRef.current = mediaRecorder; //store data in ref so that stoprecording can access it too
    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0 && socket.readyState === WebSocket.OPEN) {
        socket.send(event.data);
      }
    };
    mediaRecorder.start(2000); //start recording and break it into chunks of 2 secs
    setRecording(true);
  };

  return (
    <div style={{ padding: 20 }}>
      <h1>SupportScribe WebSocket Test</h1>
      {/*recording */}
      {!recording ? (
        <button onClick={startRecording}>Start Call</button>
      ) : (
        <button onClick={stopRecording}>End Call</button>
      )}
    </div>
  );
}
