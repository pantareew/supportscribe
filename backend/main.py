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
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print ("client connected")
    try:
        while True:
            data = await websocket.receive_text()
            print("received:",data)
    except Exception as e:
        print("connection closed", e)