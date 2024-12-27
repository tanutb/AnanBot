from pydantic import BaseModel
from typing import Optional
import requests
from config import MODEL_API

class ChatRequest(BaseModel):
    text: str
    image_path: str = None

def get_response(request: ChatRequest) -> str:
    __API = MODEL_API
    data = {"text": request.text}
    if request.image_path:
        data["image_path"] = request.image_path
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


if __name__ == "__main__":
    # Create a ChatRequest instance
    chat_request = ChatRequest(text="What's game oputo playing?")
    response_message = get_response(chat_request)
    print(response_message)