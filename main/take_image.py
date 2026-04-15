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
                if not img.flags['C_CONTIGUOUS']:
                    img = np.ascontiguousarray(img)
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

    def get_laser_location(self):
        img = HighResCamera().take_laser_image()
        cv2.imwrite("try.jpg", img)
        gsd = Gsd(camera_params=camera_params)
        img = gsd.warp_table_exact(img)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        # 2. Define the bounds for the color red.
        # In OpenCV, Hue goes from 0 to 179.
        # Red is tricky because it sits at the very edge of the Hue circle,
        # meaning it wraps around from 170-179 back to 0-10.

        # Lower red range (Hue 0 to 10)
        lower_red_1 = np.array([0, 120, 70])
        upper_red_1 = np.array([10, 255, 255])

        # Upper red range (Hue 170 to 180)
        lower_red_2 = np.array([170, 50, 30])
        upper_red_2 = np.array([180, 255, 255])

        # 3. Create masks for both red ranges
        mask1 = cv2.inRange(hsv, lower_red_1, upper_red_1)
        mask2 = cv2.inRange(hsv, lower_red_2, upper_red_2)

        # 4. Combine the two masks (Pixel is red if it's in mask1 OR mask2)
        final_red_mask = cv2.bitwise_or(mask1, mask2)

        # 5. Apply the mask to the original image
        # This keeps original pixel colors where the mask is white (255)
        # and turns them black (0) where the mask is black.
        red_only_image = cv2.bitwise_and(img, img, mask=final_red_mask)

        contours, _ = cv2.findContours(final_red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.imwrite("laser_mask1.jpg", final_red_mask)
        print("saved")
        # If the image is completely black (no laser detected)
        if not contours:
            print("⚠️ [Laser] No light sources detected in the image.")
            return None

        # 2. Find the largest contour (assuming the laser is the biggest bright spot)
        largest_contour = max(contours, key=cv2.contourArea)




        # 3. Calculate the center of the shape using "Image Moments"
        # Moments are just a mathematical way to find the center of mass of a cluster of pixels
        M = cv2.moments(largest_contour)

        # Prevent division by zero (happens if the contour is somehow a single pixel line)
        if M["m00"] == 0:
            return None

        # Calculate the exact x and y coordinates
        center_x = int(M["m10"] / M["m00"])
        center_y = int(M["m01"] / M["m00"])

        # annotate point on image
        # 1. Choose a highly visible color (BGR format). Green: (0, 255, 0)
        marker_color = (0, 255, 0)

        # 2. Draw a circle around the laser
        # Arguments: image, center, radius, color, thickness
        cv2.circle(img, (center_x, center_y), radius=20, color=marker_color, thickness=2)

        # 3. Draw a precise crosshair exactly at the center point
        # Arguments: image, position, color, markerType, markerSize, thickness
        cv2.drawMarker(img, (center_x, center_y), color=marker_color,
                       markerType=cv2.MARKER_CROSS, markerSize=30, thickness=2)

        # 4. (Optional) Add text showing the exact coordinates
        text = f"Laser: ({center_x}, {center_y})"
        # Arguments: image, text, bottom-left corner, font, scale, color, thickness
        cv2.putText(img, text, (center_x + 25, center_y - 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, marker_color, 2)

        return (center_x, center_y), img


def take_image():
    """Standalone wrapper function for backward compatibility."""
    camera = HighResCamera()
    img = camera.take_image()




if __name__ == "__main__":
    cord, frame = HighResCamera().get_laser_location()
    cv2.imwrite("test.jpg", frame)
    print(f"the lazer location is {cord}")
    print("saved")
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

