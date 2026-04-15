import os
import time
import json
import requests

# List your API keys here
API_KEYS = [
    "AIzaSyBR7WXSwG7z0J8FeuTL1CUxpfP0yF9uitU",
    "AIzaSyBR7WXSwG7z0J8FeuTL1CUxpfP0yF9uitU",
    "AIzaSyBhMx_uz5VaKfntKWKdLMeExhKOgtf9pxY",
    "AIzaSyC4EfHcnp29Kh91E_cfwARhqmUqTkB-HiQ"
]

# List of models to try
MODELS = [
    # The absolute best for free tier (1,000 requests/day)
    "gemini-2.5-flash",

    # Highest intelligence available for free (100 requests/day)
    "gemini-2.5-pro",

    # Fastest, highest volume for light tasks (1,500 requests/day)
    "gemini-2.5-flash-lite",

    # Stable legacy version (still active for free users)
    "gemini-2.0-flash"
]

class KeyRotator:
    def __init__(self):
        self.key_index = 0
        self.model_index = 0

    def is_placeholder(self, key):
        """Returns True if the key is a placeholder."""
        return "YOUR_KEY" in key or not key.startswith("AIza")

    def rotate(self):
        """Moves to the next model. If all models are cycled, moves to the next key."""
        self.model_index += 1
        if self.model_index >= len(MODELS):
            self.model_index = 0
            self.key_index = (self.key_index + 1) % len(API_KEYS)
            
            # Skip placeholders
            start_idx = self.key_index
            while self.is_placeholder(API_KEYS[self.key_index]):
                self.key_index = (self.key_index + 1) % len(API_KEYS)
                if self.key_index == start_idx:
                    break
        
        print(f"🔄 Rotating to Key Index {self.key_index} | Model: {MODELS[self.model_index]}")

    def call_with_retry(self, prompt, target_model=None):
        """
        Executes the AI call via REST API. 
        Retries on 429, 503, 400, or 404.
        """
        max_attempts = len(API_KEYS) * len(MODELS)
        attempts = 0
        
        while attempts < max_attempts:
            key = API_KEYS[self.key_index]
            model = target_model if target_model else MODELS[self.model_index]

            if self.is_placeholder(key):
                self.rotate()
                attempts += 1
                continue

            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
            headers = {'Content-Type': 'application/json'}
            data = {
                "contents": [{"parts": [{"text": prompt}]}]
            }

            try:
                response = requests.post(url, headers=headers, json=data, timeout=30)
                res_json = response.json()

                if response.status_code == 200:
                    # Success! Mimic the SDK response structure for compatibility
                    class SimpleResponse:
                        def __init__(self, text):
                            self.text = text
                    
                    text_out = res_json['candidates'][0]['content']['parts'][0]['text']
                    return SimpleResponse(text_out)

                else:
                    # Handle Errors
                    msg = res_json.get('error', {}).get('message', 'Unknown Error')
                    print(f"⚠️ API Error ({response.status_code}): {msg[:100]}...")
                    
                    if response.status_code in [429, 503, 400, 404]:
                        self.rotate()
                        attempts += 1
                        time.sleep(1) # Cooldown
                        continue
                    else:
                        raise Exception(f"API Failure: {msg}")

            except Exception as e:
                print(f"⚠️ Request Error: {e}")
                self.rotate()
                attempts += 1
                time.sleep(1)
        
        raise Exception("❌ Fail: All API keys and models exhausted.")

# Create a singleton instance
rotator = KeyRotator()
