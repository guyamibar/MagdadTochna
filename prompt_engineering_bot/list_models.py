import os
import sys
from pathlib import Path
from google import genai

# --- PATH SETUP ---
BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR))

try:
    from rotate_key_model import API_KEYS
except ImportError:
    print("❌ Error: Could not find rotate_key_model.py")
    sys.exit(1)

def list_available_models():
    print("🚀 --- Gemini API Model Diagnostics ---")
    
    for i, key in enumerate(API_KEYS):
        if "YOUR_KEY" in key or not key.startswith("AIza"):
            print(f"\n🔑 Key Index {i}: [Skipping Placeholder]")
            continue
            
        print(f"\n🔑 Testing Key Index {i}: {key[:10]}...")
        try:
            client = genai.Client(api_key=key)
            models = client.models.list()
            
            print(f"✅ Success! Models available for this key:")
            found = False
            for m in models:
                # In the new SDK, m.supported_methods is a list of strings
                if "generateContent" in m.supported_methods:
                    name = m.name.replace("models/", "")
                    print(f"  - {name}")
                    found = True
            
            if not found:
                print("  ⚠️ No 'generateContent' models found for this key.")
                
        except Exception as e:
            print(f"❌ Error with this key: {e}")

if __name__ == "__main__":
    list_available_models()
