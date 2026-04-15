import sys
import cv2
from pathlib import Path

# --- PATH SETUP ---
ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))

from main.take_image import take_image

"""
FILE: shoot_photo.py

DESCRIPTION:
    Handles physical image acquisition from the live camera and saves it 
    to boot/data/photo.jpg.
"""

def shoot_photo() -> bool:
    # 1. Acquisition
    print("📸 Capturing live photo from camera...")
    img = take_image()

    if img is None:
        print("❌ Error: Image acquisition failed.")
        return False

    # 2. Saving
    save_path = Path(__file__).parent / "photo_to_state_pipeline" / "photo.jpg"
    save_path.parent.mkdir(parents=True, exist_ok=True)
    
    cv2.imwrite(str(save_path), img)
    print(f"💾 Saved photo to {save_path}")
    
    return True

if __name__ == "__main__":
    success = shoot_photo()
    if success:
        print(f"✅ Success.")
