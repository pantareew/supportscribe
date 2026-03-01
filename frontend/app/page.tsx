"use client";

import { useEffect, useRef, useState } from "react";

export default function Home() {
  const [socket, setSocket] = useState<WebSocket | null>(null); //websocket connection instance
  const [recording, setRecording] = useState(false); //show start or end button
  const mediaRecordRef = useRef<MediaRecorder | null>(null); //stores media recorder
  const [transcript, setTranscript] = useState<string>(""); //transcribed text

  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8000/ws"); //connect to fastapi websocket endpoint
    //connect successful
    ws.onopen = () => {
      console.log("Connected to backend");
    };

    //receive data from backend
    ws.onmessage = (event) => {
      setTranscript((prev) => prev + " " + event.data);
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
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true }); //connect to mic access
      const mediaRecorder = new MediaRecorder(stream); //set up recorder by connecting to stream
      mediaRecordRef.current = mediaRecorder; //store data in ref so that stoprecording can access it too
      //event handler to run every time the recorder has a new chunk
      mediaRecorder.ondataavailable = (event) => {
        //check for data blob and ws state
        if (event.data.size > 0 && socket.readyState === WebSocket.OPEN) {
          socket.send(event.data); //send audio blob to backend immediately
        }
      };
      mediaRecorder.start(2000); //start recording and break it into chunks of 2 secs
      setRecording(true); //ui shows end call btn
    } catch (err) {
      console.error("Microphone access denied", err);
      alert("Please allow microphone access to use SupportScribe");
    }
  };

  const stopRecording = () => {
    mediaRecordRef.current?.stop(); //stop recording
    setRecording(false); //ui switch to start call btn
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
      {/*transcript */}
      <div style={{ marginTop: 20 }}>
        <h2>Live Transcript:</h2>
        <p>{transcript}</p>
      </div>
    </div>
  );
}
