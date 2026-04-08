import numpy as np
import time
from typing import Union, Tuple
try:
    from picamera2 import Picamera2
except ImportError:
    Picamera2 = None

import arduino_control.moveitmoveit
from game_structure.models import Point2D
from arduino_control.moveitmoveit import grab, grabber_release, move_to, grabber_rest



def move_player(point_coordinate: Union[Point2D, Tuple[float, float]]) -> None:
    """
    Moves the robotic arm/player to a specific point coordinate.
    """
    move_to(point_coordinate)

def grab() -> None:
    """
    Triggers the grab mechanism.
    """
    arduino_control.moveitmoveit.grab()

def drop() -> None:
    """
    Triggers the drop/release mechanism.
    """
    grabber_release()
    grabber_rest()

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

def look_at_card() -> None:

    """
    Triggers the looking mechanism for a card.
    """
    pass