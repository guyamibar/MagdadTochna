import numpy as np
import time
from typing import Union, Tuple
from picamera2 import Picamera2
from game_structure.models import Point2D

def take_image() -> np.ndarray:
    """
    Captures an image using the PiCamera2 and returns it as a numpy array.
    """
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
        return None

    finally:
        picam2.stop()

def move_player(point_coordinate: Union[Point2D, Tuple[float, float]]) -> None:
    """
    Moves the robotic arm/player to a specific point coordinate.
    """
    pass

def grab() -> None:
    """
    Triggers the grab mechanism.
    """
    pass

def drop() -> None:
    """
    Triggers the drop/release mechanism.
    """
    pass

def shoot(point_coordinate: Union[Point2D, Tuple[float, float]]) -> None:
    """
    Triggers the shooting mechanism targeting a specific point coordinate.
    """
    pass

def flip() -> None:
    """
    Triggers the flipping mechanism for a card.
    """
    pass
