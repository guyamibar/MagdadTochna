import os
import time
from google import genai

# List your 4 API keys here
API_KEYS = [
    "AIzaSyCHyk8QN1UjtybX1WJOV-MNgVIxdLBAyXg", # Key 1 (Current)
    "YOUR_KEY_2_HERE",
    "YOUR_KEY_3_HERE",
    "YOUR_KEY_4_HERE"
]

# List of models to try if the primary is overloaded
MODELS = [
    "gemini-flash-lite-latest",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b"
]

class KeyRotator:
    def __init__(self):
        self.key_index = 0
        self.model_index = 0
        self.client = None
        self._update_client()

    def _update_client(self):
        """Initializes the client with the current key."""
        current_key = API_KEYS[self.key_index]
        os.environ["GEMINI_API_KEY"] = current_key
        self.client = genai.Client(api_key=current_key)

    def rotate(self):
        """Moves to the next key. If all keys are cycled, moves to the next model."""
        self.key_index += 1
        if self.key_index >= len(API_KEYS):
            self.key_index = 0
            self.model_index = (self.model_index + 1) % len(MODELS)
        
        self._update_client()
        print(f"🔄 Error detected. Rotating to Key Index {self.key_index} | Model: {MODELS[self.model_index]}")

    def call_with_retry(self, prompt, target_model=None):
        """
        Executes the AI call. 
        If a 503 or 429 error occurs, it rotates the key and retries.
        """
        max_attempts = len(API_KEYS) * len(MODELS)
        attempts = 0
        
        while attempts < max_attempts:
            try:
                # Use provided model or current rotation model
                model_id = target_model if target_model else MODELS[self.model_index]
                
                response = self.client.models.generate_content(
                    model=model_id,
                    contents=prompt
                )
                return response
            except Exception as e:
                err_msg = str(e)
                # Check for 503 (High Demand), 429 (Rate Limit), or specific demand keywords
                if "503" in err_msg or "429" in err_msg or "demand" in err_msg.lower():
                    self.rotate()
                    attempts += 1
                    time.sleep(0.5) # Minimal pause before retry
                else:
                    # If it's a different error (like a prompt error), raise it
                    raise e
        
        raise Exception("❌ Fail: All API keys and models exhausted.")

# Create a singleton instance for the project to use
rotator = KeyRotator()
