import requests
from config import STABLE_WEBUI_API , NEGATIVE_PROMPTS

def generate_image(prompt, steps=25, cfg_scale=7, width=512, height=512):
    url = STABLE_WEBUI_API
    headers = {
        "Content-Type": "application/json"
    }
    data = {
    "prompt": prompt,
    "negative_prompt": NEGATIVE_PROMPTS,
    "seed": -1,
    "subseed": -1,
    "subseed_strength": 0,
    "sampler_name": "Euler a",
    "scheduler": "string",
    "batch_size": 1,
    "n_iter": 1,
    "steps": steps,
    "cfg_scale": cfg_scale,
    "width": width,
    "height": height,
    "restore_faces": False,
    "denoising_strength": 0.7,
    "eta": 1,
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Request failed with status code {response.status_code}")
        return None