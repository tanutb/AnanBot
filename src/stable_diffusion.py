import requests
from config import STABLE_WEBUI_API

def generate_image(prompt, steps=50, cfg_scale=7.5, width=512, height=512):
    url = STABLE_WEBUI_API
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "prompt": prompt,
        "steps": steps,
        "cfg_scale": cfg_scale,
        "width": width,
        "height": height
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Request failed with status code {response.status_code}")
        return None