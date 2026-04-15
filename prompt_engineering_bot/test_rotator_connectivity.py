import sys
import os
from pathlib import Path

# --- PATH SETUP ---
# Add the prompt_engineering_bot folder to the path so we can import rotate_key_model
BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR))

try:
    from rotate_key_model import rotator
except ImportError:
    print("❌ Error: Could not find rotate_key_model.py in the current directory.")
    sys.exit(1)

def test_rotation():
    print("🚀 --- Key Rotator Connectivity Test ---")
    
    test_prompt = "Say 'The system is online and connected.' if you can hear me."
    
    print("\n📡 Attempting to reach Gemini AI...")
    print(" (Note: If you see rotation logs, it means the first keys/models failed but it's still trying.)\n")
    
    try:
        # This will use the rotation logic automatically if it hits errors
        response = rotator.call_with_retry(test_prompt)
        
        print("\n✅ SUCCESS!")
        print("-" * 30)
        print(f"AI Output: {response.text.strip()}")
        print("-" * 30)
        print("\nYour KeyRotator is working and at least one key/model combination is valid.")
        
    except Exception as e:
        print("\n❌ CRITICAL FAILURE!")
        print("-" * 30)
        print(f"Error Details: {e}")
        print("-" * 30)
        print("\n💡 Troubleshooting Tips:")
        print("1. Check your internet connection.")
        print("2. Verify that your API keys in rotate_key_model.py are correct.")
        print("3. Go to Google AI Studio and verify the models in your list are actually available to you.")

if __name__ == "__main__":
    test_rotation()
