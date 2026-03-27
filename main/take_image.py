import numpy as np
from picamera2 import Picamera2
import time


def take_image():
    picam2 = Picamera2()

    try:
        config = picam2.create_still_configuration(main={"size": (4040, 3840), "format": "RGB888"})
        picam2.configure(config)

        # Start the camera sensor
        picam2.start()

        # Give the sensor time to warm up
        print("Warming up camera...")
        time.sleep(2)

        # Trigger autofocus
        print("Focusing...")
        picam2.autofocus_cycle()

        # Capture and save the file
        print("Capturing 64MP image... (this may take a moment)")
        img = picam2.capture_array()
        if not img.flags['C_CONTIGUOUS']:
            print("Fixing memory alignment (forcing C-contiguous)...")
            img = np.ascontiguousarray(img)

        print(f"Success!")

        return img


    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        picam2.stop()


if __name__ == "__main__":
    take_image()