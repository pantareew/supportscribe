from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from openai import OpenAI
import os
import io
import asyncio

load_dotenv()

app = FastAPI()

ai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

#frontend connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#test backend connection
@app.get("/")
async def root():
    return {"status": "SupportScribe backend running"}

#transcribe audio byte to text
async def transcribe_audio(audio_bytes: bytes) -> str: #returning a string (transcribed text)
    audio_file = io.BytesIO(audio_bytes) #convert bytes into file to send to ai
    audio_file.name = "audio.webm"
    transcript = await asyncio.to_thread( #run the function in separate thread so it doesn't block async ws loop
        ai.audio.transcriptions.create, #ai creates speech to text
        model="whisper-1", #use OpenAI Whisper
        file=audio_file 
    )
    return transcript.text
#websocket connection
@app.websocket("/ws") #websocket endpoint
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept() #server accept connection
    audio_chunk = bytearray() #array to hold audio data
    webm_header = None #to store frist chunk header
    try:
        while True: #while connected
            data = await websocket.receive_bytes() #await for frontend to send data
            #extract header from first chunk
            if webm_header is None:
                webm_header = data[:2000] #first 2 kb contains headers 
            audio_chunk.extend(data) #add received data to array
            print("Chunk size:", len(audio_chunk))
            if len(audio_chunk) > 200_000: #receive enough data to transcribe (200_000 bytes)
                try:
                    chunk_to_transcribe = webm_header + audio_chunk #add header to audio chunk to prevent type error
                    text = await transcribe_audio(chunk_to_transcribe) #call whisper to get convert bytes to text
                    await websocket.send_text(text) #send transcribed text back to frontend
                except Exception as e:
                    await websocket.send_text(f"[Error transcribing: {e}]")
                audio_chunk.clear() #clear chunk array
    #call is ended
    except Exception as e:
        print("connection closed", e)
        #if there's leftover data
        if audio_chunk and webm_header:
            try: 
                print("Printing last transcript")
                final_chunk = webm_header + audio_chunk
                text = await transcribe_audio(final_chunk)
                await websocket.send_text(text)
            except Exception as e:
                print("Last transcript error:", e)