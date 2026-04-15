import socket
import math
import time
from typing import Tuple

Position = Tuple[float, float]
degrees = float
_sock = None  # The underscore means "private, don't touch this from outside"
_ARDUINO_IP = None
_TCP_PORT = 4210
_HOSTNAME = "player-nano.local"


def _connect():
    """Private function to handle the actual connection."""
    global _sock, _ARDUINO_IP
    if _sock:
        try:
            _sock.close()
        except:
            pass

    retries = 0
    while retries < 5:
        try:
            _ARDUINO_IP = socket.gethostbyname(_HOSTNAME)
            _sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            _sock.settimeout(5.0)
            _sock.connect((_ARDUINO_IP, _TCP_PORT))
            _sock.settimeout(None)
            print("✅ Connected to ESP32")
            return
        except Exception as e:
            retries += 1
            print(f"⚠️ Connection failed ({e}). Retrying ({retries}/5)...")
            time.sleep(3)
    
    print("❌ Failed to connect to Player ESP32 after 5 attempts. Continuing without hardware...")
    _sock = None


# Auto-connect the first time this module is imported anywhere
_connect()


def send_command(cmd_id: int, arg1: int = 0, arg2: int = 0):
    """The ONLY public function other files are allowed to use."""
    global _sock
    if not _sock:
        print(f"📴 [Offline Simulation] Player command ignored: {cmd_id} {arg1} {arg2}")
        return True
        
    message = f"{cmd_id} {arg1} {arg2}\n"

    try:
        _sock.sendall(message.encode())
        while True:
            response = _sock.recv(1024).decode().strip()
            if f"FINISHED_CMD:{cmd_id}" in response:
                print(f"finished {cmd_id}")
                return True
    except Exception as e:
        print(f"Connection lost! Reconnecting... {e}")
        _connect()
        return False
#-----------------------------calculations---------------------------------
s_l = (0.0, 0.0)
s_r = (7, 0.0)

a = 18
b = 22


def __alpha_beta(p: Position) -> Tuple[float, float]:
    """Compute left (alpha) and right (beta) joint angles (radians) for position p."""
    d_l = math.dist(p, s_l)
    term_l = (d_l**2 + a**2 - b**2) / (2 * a * d_l)
    term_l = max(-1.0, min(1.0, term_l))
    alpha = math.atan2(p[1] - s_l[1], p[0] - s_l[0]) + math.acos(term_l)

    d_r = math.dist(p, s_r)
    term_r = (d_r**2 + a**2 - b**2) / (2 * a * d_r)
    term_r = max(-1.0, min(1.0, term_r))
    beta = math.atan2(p[1] - s_r[1], p[0] - s_r[0]) - math.acos(term_r)
    return alpha, beta

def __stepper_angle(angle: float) -> int:
    """Convert raw angle (radians) to stepper motor steps."""
    return int(angle * -3 / 2)

def __get_grabbler_angle(position: int) -> float:
    theta_sep = math.acos((b**2+a**2-math.dist(position, s_r)**2)/(2*a*b))
    theta_rev = math.pi-(theta_sep-__alpha_beta(position)[1])
    return theta_rev * 180 / math.pi
#-----------------------------calculations---------------------------------

#---------------------------arms funcs-------------------------
DEFAULT_POS: Position = (-4, 10)
ROTATOR_POS: Position = (15, 8)
CLOSE_CENTER_POS: Position = (3.5, 7.5)
CLOSE_RIGHT_POS: Position = (-25, 7.5)
FAR_CENTER_POS: Position = (3.5, 12)

def __turn_left_motor(angle: float) -> None:
    """Turn the right motor to the specified angle (degrees)."""
    servo_angle = __stepper_angle(angle)
    print(f"Turning left motor to angle: {servo_angle}")
    send_command(3, int(servo_angle), 0)

def __turn_right_motor(angle: float) -> None:
    """Turn the left motor to the specified angle (degrees)."""
    servo_angle = __stepper_angle(angle)
    print(f"Turning right motor to angle: {servo_angle}")
    send_command(4, int(servo_angle), 0)

def __turn_motors(left_angle: float, right_angle: float) -> None:
    """Send servo angles to motors after converting to servo-specific values.

    Angles are expected in degrees.
    """
    right_servo_angle = __stepper_angle(right_angle - 162)
    left_servo_angle = __stepper_angle(left_angle - 237)
    print(f"Right Motor Angle: {right_servo_angle}, Left Motor Angle: {left_servo_angle}")
    send_command(2, int(left_servo_angle), int(right_servo_angle))

def move_to(pos: Position) -> None:
    """Move the arm to pos (x, y) in workspace units."""
    alpha, beta = __alpha_beta(pos)
    deg_r = beta / math.pi * 180
    deg_l = alpha / math.pi * 180
    print(f"Moving to position: {pos}")
    __turn_motors(deg_l, deg_r)
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
    __grabber_set(150)
    time.sleep(4)
    grabber_rest()

def grabber_rest() -> None:
    """Rest the grabber to the resting position."""
    print("Resting grabber!")
    __grabber_set(133)

def grab() -> None:
    """Perform a grab sequence: lower, wait, then partially lift."""
    print("Grabbing!")
    grabber_catch()
    time.sleep(1)
    grabber_rest()

def grab_from_rotator() -> None:
    """Perform a grab sequence from the rotator: lower, wait, then fully lift."""
    print("Grabbing from rotator!")
    __grabber_set(110)
    grabber_rest()
#--------------------------- Grabber funcs -------------------------

def rotator_rotate(angle: degrees) -> None:
    """Rotate the grabber to a specific angle."""
    print(f"Rotating grabber to angle: {angle}")
    send_command(6, int(angle * 3 / 2), 0)

def flipper_rotate(angle: degrees) -> None:
    """Rotate the flipper to a specific angle."""
    print(f"Rotating flipper to angle: {angle}")
    send_command(7, int(270 - angle), 0)

def __get_required_rotation(card_pos: Position, card_orientation: degrees) -> degrees:
    grabber_rotation =  __get_grabbler_angle(card_pos) - __get_grabbler_angle(ROTATOR_POS)
    required_rotation = card_orientation - grabber_rotation
    return (360 + required_rotation) % 180

def pos_to_rotator(required_rotation: degrees) -> None:
    rotator_rotate(required_rotation)
    left_approach() if required_rotation < 90 else right_approach()

def left_approach() -> None:
    move_to(CLOSE_CENTER_POS)
    move_to(ROTATOR_POS)

def right_approach() -> None:
    move_to(CLOSE_RIGHT_POS)
    move_to(ROTATOR_POS)

def right_exit() -> None:
    move_to(CLOSE_RIGHT_POS)
    move_to(FAR_CENTER_POS)

def left_exit() -> None:
    move_to(CLOSE_CENTER_POS)
    move_to(FAR_CENTER_POS)

def put_card_in_rotator(card_pos: Position, card_orientation: degrees) -> None:
    """Move a card to the rotator and rotate it to the correct orientation."""
    print(f"Putting card in rotator from position: {card_pos} with orientation: {card_orientation}")
    required_orientation = __get_required_rotation(card_pos, card_orientation)
    grabber_rest()
    move_to((-10, 10))
    grabber_catch()
    time.sleep(2)
    grabber_rest()
    move_to((20, 20))
    p1: Position = (ROTATOR_POS[0] + math.cos(math.radians(required_orientation)) * 10, ROTATOR_POS[1] + math.sin(math.radians(required_orientation)) * 10)
    rotator_rotate(required_orientation)
    move_to(p1)
    for i in range(0, 3):
        move_to((p1[0] * (1 - i/5) + i/5 * ROTATOR_POS[0], (p1[1] * (1 - i/5) + i/5 * ROTATOR_POS[1])))
    move_to(ROTATOR_POS)
    grabber_release()
    move_to(p1)
    time.sleep(1)

def take_card_from_rotator(card_pos: Position, card_orientation: degrees) -> None:
    """Take a card from the rotator and move it to the specified position."""
    print(f"Taking card from rotator to position: {card_pos} with orientation: {card_orientation}")
    required_orientation = __get_required_rotation(card_pos, card_orientation)
    pos_to_rotator(required_orientation)
    grab_from_rotator()
    left_exit() if required_orientation < 90 else right_exit()
    move_to(card_pos)
    grabber_release()

def grabber_lazer(lazer_state: bool) -> None:
    """Turn the grabber's lazer on or off."""
    print(f"Turning grabber lazer {'ON' if lazer_state else 'OFF'}")
    send_command(9, 1 if lazer_state else 0)
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
        #put_card_in_rotator((10, 10), 30)
        #grabber_rest()
        #__turn_motors(90, 90)
        #move_to((-10, 20))
        #grab()
        #grabber_catch()
        #grabber_release()
        #grabber_rest()
        grabber_lazer(True)
        #move_to((20, 20))
        #move_to(ROTATOR_POS)
        #put_card_in_rotator((10, 10), 0)
        #__grabber_set(30)
        
        print("your fon linging bring bring bring")
    finally:
        if _sock:
            _sock.close()