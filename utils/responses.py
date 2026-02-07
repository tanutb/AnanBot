from typing import Optional, Dict, Any, Union
import requests
import os
from dotenv import load_dotenv
from utils import ChatRequest

load_dotenv()

def get_response(request: ChatRequest) -> Union[Dict[str, Any], str]:
    """Sends a chat request to the model API and retrieves the response.

    Args:
        request: The ChatRequest object containing input data.

    Returns:
        The JSON response from the API as a dictionary, or an error message string.
    """
    __API = os.getenv("MODEL_API")
    if not __API:
        return "Error: MODEL_API not set in .env"

    data = {
        "text": request.text,
        "user_id": request.user_id,
        "is_mentioned": request.is_mentioned,
        "karma": request.karma
    }
    
    if request.username:
        data["username"] = request.username

    if request.context_id:
        data["context_id"] = request.context_id
        
    if request.image_paths:
        data["image_paths"] = request.image_paths
        
    try:
        response = requests.post(__API, json=data)
        if response.status_code == 200 and response.content:
            try:
                response_json = response.json()
                return response_json
            except ValueError:
                print("Response content is not valid JSON")
                return "Error: Response content is not valid JSON"
        else:
            print(f"Request failed with status code {response.status_code}")
            return "Error: Request failed"
    except Exception as e:
        print(f"Error connecting to API: {e}")
        return f"Error: {e}"

def get_user_profile_data(user_id: str) -> Dict[str, Any]:
    """Fetches user profile data from the model API.

    Args:
        user_id: The unique identifier of the user.

    Returns:
        A dictionary containing the user's profile data or an error message.
    """
    __API = os.getenv("MODEL_API", "http://127.0.0.1:8119/chat/")
    base_url = __API.split("/chat")[0]  # Strip endpoint robustly
    target_url = f"{base_url}/user/{user_id}/details"
    
    try:
        resp = requests.get(target_url)
        if resp.status_code == 200:
            return resp.json()
        else:
            return {"error": f"Failed to fetch profile. API Error: {resp.status_code}"}
    except Exception as e:
        return {"error": f"Error connecting to backend: {e}"}

def set_user_karma(user_id: str, score: int) -> Dict[str, Any]:
    """Sets the karma score for a user via the model API.

    Args:
        user_id: The unique identifier of the user.
        score: The new karma score to set.

    Returns:
        A dictionary containing the API response or an error message.
    """
    __API = os.getenv("MODEL_API", "http://127.0.0.1:8119/chat/")
    base_url = __API.split("/chat")[0]
    target_url = f"{base_url}/user/{user_id}/karma"
    
    try:
        resp = requests.post(target_url, params={"score": score})
        if resp.status_code == 200:
            return resp.json()
        else:
            return {"error": f"Failed to set karma. API Error: {resp.status_code}"}
    except Exception as e:
        return {"error": f"Error connecting to backend: {e}"}

def set_bot_debug_mode(mode: bool) -> Dict[str, Any]:
    """Toggles the debug mode of the bot via the model API.

    Args:
        mode: True to enable debug mode, False to disable.

    Returns:
        A dictionary containing the API response or an error message.
    """
    __API = os.getenv("MODEL_API", "http://127.0.0.1:8119/chat/")
    base_url = __API.split("/chat")[0]
    target_url = f"{base_url}/debug"
    
    try:
        resp = requests.post(target_url, params={"mode": mode})
        if resp.status_code == 200:
            return resp.json()
        else:
            return {"error": f"Failed to toggle debug mode. API Error: {resp.status_code}"}
    except Exception as e:
        return {"error": f"Error connecting to backend: {e}"}
