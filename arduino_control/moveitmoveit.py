import socket
import math
import time
from typing import Tuple

Position = Tuple[float, float]
#-------------------------arduino communication setup-------------------------
# ARDUINO_IP = "10.20.88.179"
ARDUINO_IP = "10.255.102.178"
UDP_PORT = 4210

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", UDP_PORT))

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
X_OFFSET = 0#0.7
Y_OFFSET = 0#0.4

s_l = (0.0, 0.0)
s_r = (7, 0.0)

a = 19.4
b = 22

def __distance(A: Position, B: Position) -> float:
    """Return Euclidean distance between points A and B."""
    return math.hypot(A[0] - B[0], A[1] - B[1])

def __alpha_beta(p: Position) -> Tuple[float, float]:
    """Compute left (alpha) and right (beta) joint angles (radians) for position `p`."""
    d_l = __distance(p, s_l)
    term_l = (d_l ** 2 + a ** 2 - b ** 2) / (2 * a * d_l)
    term_l = max(-1.0, min(1.0, term_l))
    alpha = math.atan2(p[1] - s_l[1], p[0] - s_l[0]) + math.acos(term_l)

    d_r = __distance(p, s_r)
    term_r = (d_r ** 2 + a ** 2 - b ** 2) / (2 * a * d_r)
    term_r = max(-1.0, min(1.0, term_r))
    beta = math.atan2(p[1] - s_r[1], p[0] - s_r[0]) - math.acos(term_r)

    return alpha, beta

def __corrected(p: Position) -> Position:
    """Apply positional offsets based on region rules and return corrected position."""
    x_mltp = -1 if p[0] > 2.4 else 1 if p[0] < -2.4 else 0
    y_mltp = 0 if p[1] < 4.8 else -1
    return p[0] + x_mltp * X_OFFSET, p[1] + y_mltp * Y_OFFSET

def __get_angles(pos: Position) -> Tuple[float, float]:
    """Return raw joint angles (radians) for a given `pos` after applying corrections."""
    return __alpha_beta(__corrected(pos))

def __stepper_angle(angle: float) -> int:
    """Convert raw angle (radians) to stepper motor steps."""
    return int(angle * -3 / 2 + 135)
#-----------------------------calculations---------------------------------

#---------------------------arms funcs-------------------------
DEFAULT_POS: Position = (-4, 10)

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
    """Move the arm to `pos` (x, y) in workspace units."""
    alpha, beta = __get_angles(pos)
    deg_r = beta / math.pi * 180
    deg_l = alpha / math.pi * 180
    print(f"Moving to position: {pos}")
    __turn_motors(deg_l, deg_r)
#---------------------------arms funcs-------------------------

#--------------------------- Grabber funcs -------------------------
def __grabber_set(percent: int) -> None:
    """Set the grabber position relative to percent (0-100)."""
    send_command(1, 180 * percent // 100,0)

def grabber_grab() -> None:
    """Lower the grabber to the down position."""
    print("Lowering grabber!")
    __grabber_set(0)

def grabber_release() -> None:
    """Raise the grabber to the up position."""
    print("Raising grabber!")
    __grabber_set(100)

def grabber_rest() -> None:
    """Rest the grabber to the resting position."""
    print("Resting grabber!")
    __grabber_set(60)

def grab() -> None:
    """Perform a grab sequence: lower, wait, then partially lift."""
    print("Grabbing!")
    grabber_grab()
    time.sleep(1)
    grabber_rest()
    time.sleep(1)

#--------------------------- Grabber funcs -------------------------

#-------------------------------actions ----------------------------------

def move_card(card_pos: Position, target_pos: Position) -> None:
    """Pick up `<card>` and move it to `target_pos`.

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
# move_card((-20,10),(20,20))
# __turn_motors(90,90)
# send_command(4, 135,0)
# __turn_left_motor(90)
grab()
time.sleep(2)
grabber_release()
# __grabber_set(0)
time.sleep(1)
sock.close()