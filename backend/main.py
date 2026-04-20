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

#send transcript to AI to generate summary
async def generate_summary(transcript: str) -> str: #return summary text
    #response return in structured format 
    response = await asyncio.to_thread(     #run function in separate thread so server wont freeze while waiting for ai
        ai.responses.create,
        model="gpt-4.1-mini",
        #prompt
        input=f"""
        You are an AI assistant for IT service desk agents.
        Given this support call transcript:
        {transcript}
        Generate:
        1. Issue Summary
        2. Troubleshooting Steps Taken
        3. Resolution Status
        4. Next Steps (if unresolved)
        Keep it concise and structured.
        """
    ) 
    return response.output[0].content[0].text #first result from output[], first content[], actual text
#websocket connection
@app.websocket("/ws") #websocket endpoint
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept() #server accept connection
    audio_chunk = bytearray() #array to hold audio data
    webm_header = None #to store frist chunk header
    full_transcript = "" #full transcript for summary
    try:
        while True: #while connected
            data = await websocket.receive_bytes() #await for frontend to send data
            #extract header from first chunk
            if webm_header is None:
                webm_header = data[:2000] #first 2 kb contains headers 
            audio_chunk.extend(data) #add received data to array
            print("Chunk size:", len(audio_chunk))
            if len(audio_chunk) > 60_000: #receive enough data to transcribe
                try:
                    chunk_to_transcribe = webm_header + audio_chunk #add header to audio chunk to prevent type error
                    text = await transcribe_audio(chunk_to_transcribe) #call whisper to get convert bytes to text
                    full_transcript += " " + text #accumulate full transcript
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