from typing import Optional
import requests
import os
from dotenv import load_dotenv
from utils import ChatRequest

load_dotenv()

def get_response(request: ChatRequest) -> str:
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

def get_user_profile_data(user_id: str) -> dict:
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
