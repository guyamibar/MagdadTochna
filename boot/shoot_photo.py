import sys
import cv2
from pathlib import Path

# --- PATH SETUP ---
ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))
sys.path.append(str(ROOT_DIR / "game_structure"))

from main.take_image import take_image
from game_structure.gsd import Gsd, camera_params
from game_structure.models import CardDetectionResult

"""
FILE: shoot_photo.py

DESCRIPTION:
    Handles physical image acquisition from the live camera and runs 
    the Vision Pipeline (GSD).

INPUT:
    - None (Uses live camera).

OUTPUT:
    - res (CardDetectionResult): Structured object containing detected cards.
"""

def shoot_and_detect() -> CardDetectionResult:
    # 1. Acquisition (Strictly live)
    print("📸 Capturing live photo from camera...")
    img = take_image()

    if img is None:
        print("❌ Error: Image acquisition failed.")
        return None

    # 2. Vision Pipeline
    print("🔍 Running card detection pipeline...")
    gsd = Gsd(camera_params=camera_params)
    res = gsd.process([img])
    
    return res

if __name__ == "__main__":
    result = shoot_and_detect()
    if result:
        print(f"✅ Success: Detected {len(result.open_cards)} cards.")
