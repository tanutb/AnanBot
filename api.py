from PIL import Image
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import JSONResponse
import uvicorn
import requests
import utils
from src.multimodal import Multimodal

app = FastAPI()
MultiModal = Multimodal(debug=True)

# Chat endpoint
@app.post("/chat/")
async def chat_endpoint(request: utils.ChatRequest, background_tasks: BackgroundTasks):
    # Get the text and image path from the request
    text = request.text
    image_paths = request.image_paths
    user_id = request.user_id
    username = request.username
    is_mentioned = request.is_mentioned
    
    response, bg_data = MultiModal.generate_response(
        text, 
        image_paths, 
        user_id=user_id, 
        username=username, 
        is_mentioned=is_mentioned
    )
    
    # Offload memory saving to background task
    background_tasks.add_task(MultiModal.save_memory_background, bg_data)
    
    if 'img' in response:
        return JSONResponse(content={"response": response['response'], "img": response['img']})
    else:
        return JSONResponse(content={"response": response['response']})

@app.get("/user/{user_id}/details")
async def get_user_details(user_id: str):
    details = MultiModal.get_user_details(user_id)
    return JSONResponse(content=details)


if __name__ == "__main__":
    # Initialize FastAPI app
    uvicorn.run(app, host="0.0.0.0", port=8119)