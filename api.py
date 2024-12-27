from PIL import Image
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn
import requests
import utils
from src.multimodal import Multimodal

app = FastAPI()
MultiModal = Multimodal()

# Chat endpoint
@app.post("/chat/")
async def chat_endpoint(request: utils.ChatRequest):
    # Get the text and image path from the request
    text = request.text
    image_path = request.image_path
    response = MultiModal.generate_text(text, image_path)
    
    if 'img' in response:
        return JSONResponse(content={"response": response['response'], "img": response['img']})
    else:
        return JSONResponse(content={"response": response['response']})


if __name__ == "__main__":
    # Initialize FastAPI app
    uvicorn.run(app, host="0.0.0.0", port=8119)
