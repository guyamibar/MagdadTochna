import cv2
from game_structure.gsd import Gsd, camera_params
import time
import numpy as np

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
        
        if Picamera2 is None:
            print("Warning: picamera2 module not found. Camera captures will be simulated.")
            self.picam2 = None
            return

        self.picam2 = Picamera2()
        self.config = self.picam2.create_still_configuration(
            main={"size": (4500, 3840), "format": "RGB888"}
        )
        self.picam2.configure(self.config)

    def start(self):
        """Starts the camera hardware."""
        if not self._started and self.picam2 is not None:
            self.picam2.start()
            print("Warming up camera...")
            time.sleep(2)
            self._started = True

    def stop(self):
        """Stops the camera hardware safely."""
        if self._started and self.picam2 is not None:
            print("Shutting down camera hardware safely...")
            self.picam2.stop()
            self.picam2.close()
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
            self.start()

        if self.picam2 is None:
            print("Camera not initialized, returning dummy image.")
            return np.zeros((3840, 4500, 3), dtype=np.uint8)

        try:
            print("Focusing...")
            self.picam2.autofocus_cycle()

            print("Capturing 64MP image... (this may take a moment)")
            img = self.picam2.capture_array()

            if not img.flags['C_CONTIGUOUS']:
                print("Fixing memory alignment (forcing C-contiguous)...")
                img = np.ascontiguousarray(img)

            print("Capture success!")
            return img

        except Exception as e:
            print(f"Camera capture error: {e}")
            return None

def take_image():
    """Standalone wrapper function for backward compatibility."""
    camera = HighResCamera()
    return camera.take_image()

if __name__ == "__main__":
    #camera = HighResCamera()
    #camera.start()
    image = cv2.imread("test1.jpg")
    if image is not None:
        cv2.imwrite("test1.jpg", image)
        gsd = Gsd(camera_params=camera_params)
        res = gsd.process([image])
        cv2.imwrite("test2.jpg", res.annotated_image)
        for card in res.open_cards:
            if card.center.y < 800:
                print(f"card {card.classification.label} at courdinates ({card.center.x}, {card.center.y})")
    #camera.stop()
