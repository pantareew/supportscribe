from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()
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
#websocket connection
@app.websocket("/ws") #websocket endpoint
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept() #server accept connection
    print ("client connected")
    try:
        while True: #keep connect
            data = await websocket.receive() #await for frontend to send data
            if "bytes" in data: #audio bytes from frontend
                audio_bytes = data["bytes"]
                print("received audio chunk:", len(audio_bytes), "bytes")
            elif "text" in data: #text from frontend
                print("received text:", data["text"])
    except Exception as e:
        print("connection closed", e)