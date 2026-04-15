import cv2

from boot.hand_manager import save_hand
from game_structure.gsd import Gsd, camera_params
import time
import numpy as np
import traceback
from arduino_control.moveitmoveit import move_to, grab, grabber_release
try:
    from picamera2 import Picamera2

except ImportError:
    Picamera2 = None

class HighResCamera:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(HighResCamera, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._started = False
        self.picam2 = None
        self.config = None

    def _setup_camera(self):
        """Internal method to initialize the picamera2 object."""
        if Picamera2 is None:
            return False

        try:
            if self.picam2 is None:
                print("📸 [Camera] Initializing Picamera2 instance...")
                self.picam2 = Picamera2()
            
            if self.config is None:
                print("📸 [Camera] Creating still configuration (4500x3840)...")
                self.config = self.picam2.create_still_configuration(
                    main={"size": (4500, 3840), "format": "RGB888"}
                )
                self.picam2.configure(self.config)
            return True
        except Exception as e:
            print(f"❌ [Camera] Setup error: {e}")
            traceback.print_exc()
            self.picam2 = None
            self.config = None
            return False

    def start(self):
        """Starts the camera hardware."""
        if self._started:
            return True

        if not self._setup_camera():
            print("⚠️ [Camera] picamera2 module not found or setup failed. Simulation mode.")
            return False

        try:
            print("📸 [Camera] Starting hardware...")
            self.picam2.start()
            print("⌛ [Camera] Warming up (2s)...")
            time.sleep(2)
            self._started = True
            return True
        except Exception as e:
            print(f"❌ [Camera] Failed to start: {e}")
            traceback.print_exc()
            return False

    def stop(self):
        """Stops the camera hardware safely."""
        if self._started and self.picam2 is not None:
            print("📸 [Camera] Stopping hardware...")
            try:
                self.picam2.stop()
            except Exception as e:
                print(f"⚠️ [Camera] Error during stop: {e}")
            self._started = False

    def __enter__(self):
        """Runs automatically when you use a 'with' statement. Starts the camera."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Runs automatically when the 'with' block ends or crashes. Safely cleans up."""
        self.stop()

    def take_image(self):
        """Captures a single autofocus image."""
        if not self._started:
            if not self.start():
                print("⚠️ [Camera] Returning dummy image.")
                return np.zeros((3840, 4500, 3), dtype=np.uint8)

        try:
            print("🔍 [Camera] Focusing...")
            self.picam2.autofocus_cycle()

            print("📸 [Camera] Capturing image...")
            img = self.picam2.capture_array()

            if img is not None and not img.flags['C_CONTIGUOUS']:
                print("🔧 [Camera] Fixing memory alignment...")
                img = np.ascontiguousarray(img)

            if img is None:
                print("❌ [Camera] capture_array returned None.")
            else:
                print("✅ [Camera] Capture success!")
                save_path = r"/home/lahav/MagdadTochna/main/tablerun.jpg"
                if save_path:
                    try:
                        # Picamera2 usually returns RGB, but cv2 saves as BGR.
                        # Convert it so the colors are correct in the saved file.
                        img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                        cv2.imwrite(save_path, img_bgr)
                        print(f"💾 [Camera] Image successfully saved to: {save_path}")
                    except Exception as e:
                        print(f"❌ [Camera] Failed to save image: {e}")
            return img

        except Exception as e:
            print(f"❌ [Camera] Capture error: {e}")
            traceback.print_exc()
            return None

def take_image():
    """Standalone wrapper function for backward compatibility."""
    camera = HighResCamera()
    return camera.take_image()

if __name__ == "__main__":
    from pathlib import Path
    ROOT_DIR = Path(__file__).parent.parent
    H_PATH = ROOT_DIR / "data" / "H_cam_to_arm.npy"
    
    H_cam_to_arm = None
    if H_PATH.exists():
        H_cam_to_arm = np.load(H_PATH)
        print(f"✅ Loaded calibration matrix from {H_PATH}")
    else:
        print(f"⚠️ Warning: Calibration matrix not found at {H_PATH}")

    def camera_to_arm(cam_x, cam_y):
        if H_cam_to_arm is None: return (0, 0)
        pt = np.array([(cam_x, cam_y)], dtype=np.float32).reshape(-1, 1, 2)
        transformed = cv2.perspectiveTransform(pt, H_cam_to_arm)
        return (float(transformed[0][0][0]), float(transformed[0][0][1]))

    camera = HighResCamera()
    camera.start()
    image = camera.take_image()
    if image is not None:
        cv2.imwrite("test1.jpg", image)
        gsd = Gsd(camera_params=camera_params)
        res = gsd.process([image])
        cv2.imwrite("test2.jpg", res.annotated_image)
        
        all_cards = res.open_cards + res.face_down_cards
        for card in all_cards:
            cam_x, cam_y = card.center.x, card.center.y
            if 300 <= cam_y <= 800:
                label = card.classification.label if card.classification else "Face Down"
                arm_x, arm_y = camera_to_arm(cam_x, cam_y)
                move_to((arm_x, arm_y))
                grab()
                move_to((-10, 10))
                grabber_release()
                print(f"🃏 {label}:")
                print(f"   Camera: ({cam_x:.1f}, {cam_y:.1f})")
                print(f"   Arm:    ({arm_x:.2f}, {arm_y:.2f})")
    camera.stop()
