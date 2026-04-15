import os
import sys

# Allow running this script directly from the repository root.
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import cv2
from boot.hand_manager import save_hand
from game_structure.gsd import Gsd, camera_params
import time
import numpy as np
import traceback
from arduino_control.moveitmoveit import move_to, grab, grabber_release, grabber_lazer
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

    def take_image(self, autofocus=True):
        """Captures a single image. Set autofocus=False to skip focus cycle for faster sequential captures."""
        if not self._started:
            if not self.start():
                print("⚠️ [Camera] Returning dummy image.")
                return np.zeros((3840, 4500, 3), dtype=np.uint8)

        try:
            if autofocus:
                print("🔍 [Camera] Focusing...")
                self.picam2.autofocus_cycle()

            print("📸 [Camera] Capturing image...")
            img = self.picam2.capture_array()

            if img is None:
                print("❌ [Camera] capture_array returned None.")
            else:
                print("✅ [Camera] Capture success!")
            return img

        except Exception as e:
            print(f"❌ [Camera] Capture error: {e}")
            traceback.print_exc()
            return None

    def take_laser_image(self, exposure_time=1500, analog_gain=1.0):
        """
        Captures an image with very low exposure, isolating bright light sources like lasers.
        exposure_time: in microseconds (e.g. 2000 = 2ms). Adjust based on room lighting.
        """
        if not self._started:
            if not self.start():
                print("⚠️ [Camera] Returning dummy image.")
                return np.zeros((3840, 4500, 3), dtype=np.uint8)

        try:

            print("🔍 [Camera] Focusing...")
            self.picam2.autofocus_cycle()
            print(f"🔴 [Camera] Setting manual exposure (Time: {exposure_time}µs, Gain: {analog_gain})...")
            # Disable Auto Exposure and enforce manual limits
            self.picam2.set_controls({
                "AeEnable": False,
                "ExposureTime": exposure_time,
                "AnalogueGain": analog_gain
            })

            # Allow a tiny pause for the sensor to apply the new exposure settings
            time.sleep(1)


            print("📸 [Camera] Capturing dark image for laser detection...")
            # Explicitly request the 'main' stream to guarantee the 4500x3840 resolution
            img = self.picam2.capture_array('main')

            # Immediately restore Auto Exposure so take_image() works normally next time
            print("🔄 [Camera] Restoring Auto Exposure...")
            self.picam2.set_controls({"AeEnable": True})

            # Allow the camera sensor pipeline to switch back to auto before returning
            time.sleep(0.2)

            if img is not None:
                # Print the resolution to the console to verify it matches take_image()
                print(f"📐 [Camera] Laser image resolution confirmed: {img.shape[1]}x{img.shape[0]}")
            return img

        except Exception as e:
            print(f"❌ [Camera] Laser capture error: {e}")
            traceback.print_exc()
            # Failsafe: Attempt to restore Auto Exposure if a crash occurred
            try:
                self.picam2.set_controls({"AeEnable": True})
            except Exception:
                pass
            return None

    def get_laser_location(self, num_captures=3):
        """
        Find laser location by capturing multiple images in each state and averaging them.
        This reduces noise and improves detection accuracy.
        
        Args:
            num_captures: Number of images to capture in each state (laser on/off). Default 3.
        """
        print(f"📸 [Laser] Capturing {num_captures} images with laser ON...")
        grabber_lazer(True)
        laser_on_images = []
        for i in range(num_captures):
            img = self.take_image(autofocus=(i == 0))  # Autofocus only on first capture
            if img is not None:
                laser_on_images.append(img)
                print(f"   ✅ Laser ON image {i+1}/{num_captures}")
            else:
                print(f"   ❌ Failed to capture laser ON image {i+1}/{num_captures}")

        if not laser_on_images:
            print("❌ [Laser] No images captured with laser ON")
            return None

        print(f"📸 [Laser] Capturing {num_captures} images with laser OFF...")
        grabber_lazer(False)
        laser_off_images = []
        for i in range(num_captures):
            img = self.take_image(autofocus=False)
            if img is not None:
                laser_off_images.append(img)
                print(f"   ✅ Laser OFF image {i+1}/{num_captures}")
            else:
                print(f"   ❌ Failed to capture laser OFF image {i+1}/{num_captures}")

        if not laser_off_images:
            print("❌ [Laser] No images captured with laser OFF")
            return None

        # Average images in each state to reduce noise
        print("🔄 [Laser] Averaging images to reduce noise...")
        img_laser_on_avg = np.mean(laser_on_images, axis=0).astype(np.uint8)
        img_laser_off_avg = np.mean(laser_off_images, axis=0).astype(np.uint8)
        print(f"   ✅ Averaged {len(laser_on_images)} ON images and {len(laser_off_images)} OFF images")

        # Compute difference on averaged images
        img_diff = cv2.absdiff(img_laser_on_avg, img_laser_off_avg)
        
        # Convert difference image to HSV for red color detection
        img_diff_hsv = cv2.cvtColor(img_diff, cv2.COLOR_BGR2HSV)
        cv2.imwrite("img_diff_hsv.jpg", img_diff_hsv)

        
        # Define red color ranges in HSV (red wraps around hue circle)
        lower_red_1 = np.array([0, 100, 100])
        upper_red_1 = np.array([10, 255, 255])
        lower_red_2 = np.array([170, 100, 100])
        upper_red_2 = np.array([180, 255, 255])
        
        # Create masks for both red ranges
        mask1 = cv2.inRange(img_diff_hsv, lower_red_1, upper_red_1)
        mask2 = cv2.inRange(img_diff_hsv, lower_red_2, upper_red_2)
        red_mask = cv2.bitwise_or(mask1, mask2)
        
        # Find contours of red areas
        contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            print("⚠️ [Laser] No red laser detected in difference image.")
            # Fallback: find brightest point
            img_gray = cv2.cvtColor(img_diff, cv2.COLOR_BGR2GRAY)
            _, max_val, _, max_loc = cv2.minMaxLoc(img_gray)
            if max_val < 10:
                return None
            center_x, center_y = max_loc
            print(f"✅ [Laser] Using fallback brightness detection at ({center_x}, {center_y})")
        else:
            # Find largest red contour (the laser spot)
            largest_contour = max(contours, key=cv2.contourArea)
            
            # Calculate center using moments
            M = cv2.moments(largest_contour)
            if M["m00"] == 0:
                print("⚠️ [Laser] Could not compute laser center.")
                return None
            
            center_x = int(M["m10"] / M["m00"])
            center_y = int(M["m01"] / M["m00"])
            print(f"✅ [Laser] Detected RED laser at ({center_x}, {center_y}) [averaged from {len(laser_on_images)} captures]")
        
        # Create annotated image showing laser location on the averaged laser-on image
        img_annotated = img_laser_on_avg.copy()
        marker_color = (0, 0, 255)  # Red in BGR
        
        # Draw circle and crosshair
        cv2.circle(img_annotated, (center_x, center_y), radius=40, color=marker_color, thickness=3)
        cv2.drawMarker(img_annotated, (center_x, center_y), color=marker_color,
                       markerType=cv2.MARKER_CROSS, markerSize=60, thickness=2)
        
        # Add text with coordinates
        text = f"RED Laser: ({center_x}, {center_y})"
        cv2.putText(img_annotated, text, (center_x + 50, center_y - 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, marker_color, 3)

        return (center_x, center_y), img_annotated


def take_image():
    """Standalone wrapper function for backward compatibility."""
    camera = HighResCamera()
    return camera.take_image()


if __name__ == "__main__":
    camera = HighResCamera()
    camera.start()
    result = camera.get_laser_location()
    if result:
        (laser_x, laser_y), annotated_img = result
        cv2.imwrite("laser_location.jpg", annotated_img)
        print(f"✅ Laser location saved: ({laser_x}, {laser_y})")
    else:
        print("❌ Failed to detect laser.")
    camera.stop()

