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

#generate summary
async def generate_summary(transcript: str) -> str: #return summary text
    #response return in structured format 
    response = await asyncio.to_thread(     #run function in separate thread so server wont freeze while waiting for ai
        ai.responses.create,
        model="gpt-4.1-mini",
        #prompt
        input=f"""
        You are an AI assistant for IT service desk agents.
        From the transcript below, extract:
        - Customer Issue
        - Troubleshooting Steps Taken
        - Resolution Status (Resolved / Unresolved)
        - Next Steps (if unresolved)

        Transcript:
        {transcript}

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
            data = await websocket.receive() #await for frontend to send data
            #receiving audio
            if "bytes" in data:
                chunk = data["bytes"] #get audio bytes
                #extract header from first chunk
                if webm_header is None:
                    webm_header = chunk[:2000] #first 2 kb contains headers 
                audio_chunk.extend(chunk) #add received data to array
                print("Chunk size:", len(audio_chunk))
                if len(audio_chunk) > 60_000: #receive enough data to transcribe
                    try:
                        chunk_to_transcribe = webm_header + audio_chunk #add header to audio chunk to prevent type error
                        text = await transcribe_audio(chunk_to_transcribe) #call whisper to get convert bytes to text
                        full_transcript += " " + text #accumulate full transcript
                        #send transcribed text back to frontend
                        await websocket.send_json({
                            "type": "transcript",
                            "data": text
                        }) 
                    except Exception as e:
                        await websocket.send_json({
                            "type": "error",
                            "data": str(e)
                        })
                    audio_chunk.clear() #clear chunk array
            #receiving stop signal
            elif "text" in data and data["text"] == "STOP":
                #if there's leftover chunk
                if audio_chunk and webm_header:
                    try: 
                        print("Printing final transcript")
                        final_chunk = webm_header + audio_chunk
                        text = await transcribe_audio(final_chunk)
                        full_transcript += " " + text #add transcript from leftover
                        #send transcript to frontend
                        await websocket.send_json({
                                "type": "transcript",
                                "data": text
                            }) 
                        
                    except Exception as e:
                        print("Final transcript error:", e)
                #generate summary after got full transcript
                if full_transcript.strip():
                    print("Generating summary...")
                    #send transcript to AI to generate summary
                    summary = await generate_summary(full_transcript)
                    try:
                        #send summary to frontend
                        await websocket.send_json({
                            "type": "summary",
                            "data": summary
                        })
                    except Exception as e:
                        print("Summary error:", e)
                break
    except Exception as e:
        print("Connection error:", e)
