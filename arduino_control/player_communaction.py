import socket
import math
import time
from typing import Tuple

Position = Tuple[float, float]
#-------------------------arduino communication setup-------------------------
# ARDUINO_IP = "10.20.88.179"
ARDUINO_HOSTNAME = "player-nano.local"
UDP_PORT = 4210

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", UDP_PORT))

try:
    print(f"Looking for {ARDUINO_HOSTNAME}...")
    ARDUINO_IP = socket.gethostbyname(ARDUINO_HOSTNAME)
    print(f"Found Arduino at: {ARDUINO_IP}")
except socket.gaierror:
    print(f"⚠️ Warning: Could not find {ARDUINO_HOSTNAME}. Running in Offline Mode.")
    ARDUINO_IP = "0.0.0.0" # Dummy IP

def send_command(cmd_id: int, arg1: int = 0, arg2: int = 0) -> None:
    """Send a UDP command to the Arduino.

    Args:
        cmd_id: Command identifier.
        arg1: First integer argument.
        arg2: Second integer argument.
    """
    # יצירת המחרוזת בפורמט שהארדואינו מצפה לו (עם רווחים)
    message = f"{cmd_id} {arg1} {arg2}"
    print(f"Sending command: {message}")
    sock.sendto(message.encode(), (ARDUINO_IP, UDP_PORT))
#------------------------arduino communication setup-------------------------

#-----------------------------calculations---------------------------------



#---------------------------arms funcs-------------------------
def __turn_left_motor(angle: float) -> None:
    """Turn the right motor to the specified angle (degrees)."""
    servo_angle = __stepper_angle(angle)
    print(f"Turning left motor to angle: {servo_angle}")
    send_command(3, int(servo_angle), 0)
    time.sleep(1)

def __turn_right_motor(angle: float) -> None:
    """Turn the left motor to the specified angle (degrees)."""
    servo_angle = __stepper_angle(angle)
    print(f"Turning right motor to angle: {servo_angle}")
    send_command(4, int(servo_angle), 0)
    time.sleep(1)

def __turn_motors(left_angle: float, right_angle: float) -> None:
    """Send servo angles to motors after converting to servo-specific values.

    Angles are expected in degrees.
    """
    right_servo_angle = __stepper_angle(right_angle)
    left_servo_angle = __stepper_angle(left_angle)
    print(f"Right Motor Angle: {right_servo_angle}, Left Motor Angle: {left_servo_angle}")
    send_command(2, int(left_servo_angle), int(right_servo_angle))
    time.sleep(1)

def move_to(pos: Position) -> None:
    """Move the arm to pos (x, y) in workspace units."""
    alpha, beta = __get_angles(pos)
    deg_r = beta / math.pi * 180
    deg_l = alpha / math.pi * 180
    print(f"Moving to position: {pos}")
    __turn_motors(deg_l, deg_r)
    time.sleep(1.5)
#---------------------------arms funcs-------------------------

#--------------------------- Grabber funcs -------------------------
def __grabber_set(percent: int) -> None:
    """Set the grabber position relative to percent (0-100)."""
    send_command(1, 180 * percent // 100, 0)

def grabber_catch() -> None:
    """Lower the grabber to the down position."""
    print("Lowering grabber!")
    __grabber_set(0)

def grabber_release() -> None:
    """Raise the grabber to the up position."""
    print("Raising grabber!")
    __grabber_set(100)
    time.sleep(1)

def grabber_rest() -> None:
    """Rest the grabber to the resting position."""
    print("Resting grabber!")
    __grabber_set(60)

def grab() -> None:
    """Perform a grab sequence: lower, wait, then partially lift."""
    print("Grabbing!")
    grabber_catch()
    time.sleep(1)
    grabber_rest()
    time.sleep(1)

#--------------------------- Grabber funcs -------------------------

#-------------------------------actions ----------------------------------

def move_card(card_pos: Position, target_pos: Position) -> None:
    """Pick up <card> and move it to target_pos.

    Args:
        card_pos: Position of the card to be moved.
        target_pos: Destination position as (x, y).
    """
    move_to(card_pos)
    grab()
    move_to(target_pos)
    grabber_release()
    move_to(DEFAULT_POS)
#-------------------------------actions ----------------------------------
if __name__ == "__main__":
    # This code only runs if you play THIS file directly.
    # It will be ignored when you import this file elsewhere.
    try:
        #move_card((-20,10),(20,20))
        #__turn_motors(90, 90)
        #__turn_right_motor(90)
        #__turn_left_motor(90)
        # time.sleep(3)
        #grab()
        #time.sleep(3)
        #grabber_release()
        grabber_rest()
        # grabber_catch()
        #move_to((-20, 10))
    finally:
        sock.close()