from typing import Any, Dict
from PIL import Image
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import JSONResponse
import uvicorn
import requests
import utils
from src.multimodal import Multimodal

app = FastAPI()
MultiModal = Multimodal(debug=False)

# Debug endpoint
@app.post("/debug")
async def set_debug_mode(mode: bool) -> JSONResponse:
    """Endpoint to toggle debug mode for the multimodal agent.

    Args:
        mode: The desired debug status (True for ON, False for OFF).

    Returns:
        A JSONResponse containing the new debug status.
    """
    MultiModal.debug = mode
    return JSONResponse(content={"debug_mode": MultiModal.debug})

# Chat endpoint
@app.post("/chat/")
async def chat_endpoint(request: utils.ChatRequest, background_tasks: BackgroundTasks) -> JSONResponse:
    """Endpoint to generate a response from the multimodal agent.

    Args:
        request: The chat request object containing text, images, and user info.
        background_tasks: FastAPI background tasks handler.

    Returns:
        A JSONResponse containing the agent's text response and optional image.
    """
    # Get the text and image path from the request
    text = request.text
    image_paths = request.image_paths
    user_id = request.user_id
    context_id = request.context_id
    username = request.username
    is_mentioned = request.is_mentioned
    
    response, bg_data = MultiModal.generate_response(
        text, 
        image_paths, 
        user_id=user_id,
        context_id=context_id,
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
async def get_user_details(user_id: str) -> JSONResponse:
    """Endpoint to retrieve a user's karma and persona details.

    Args:
        user_id: The unique identifier of the user.

    Returns:
        A JSONResponse containing the user's details.
    """
    details = MultiModal.get_user_details(user_id)
    return JSONResponse(content=details)

@app.post("/user/{user_id}/karma")
async def set_user_karma(user_id: str, score: int) -> JSONResponse:
    """Endpoint to explicitly set a user's karma score.

    Args:
        user_id: The unique identifier of the user.
        score: The new karma score to set.

    Returns:
        A JSONResponse containing the user's ID and new score.
    """
    new_score = MultiModal.set_karma(user_id, score)
    return JSONResponse(content={"user_id": user_id, "score": new_score})


if __name__ == "__main__":
    # Initialize FastAPI app
    uvicorn.run(app, host="0.0.0.0", port=8119)