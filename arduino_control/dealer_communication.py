import socket
import time

#-------------------------arduino communication setup-------------------------
ARDUINO_HOSTNAME = "dealer-nano.local"
UDP_PORT = 4211

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", UDP_PORT))


high_power = 150
mid_power = 120
low_power = 90

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
    message = f"{cmd_id} {arg1} {arg2}"
    print(f"Sending command: {message}")
    sock.sendto(message.encode(), (ARDUINO_IP, UDP_PORT))

def move_smallDC(power: int, direction: bool) -> None:
    #1 - forward, 0 - for backward
    send_command(cmd_id=4, arg1=power, arg2=int(direction))
    print(f"Small DC motor running at power {power} in {'forward' if direction else 'backward'} direction...")
    time.sleep(4)
    send_command(cmd_id=4, arg1=0, arg2=int(direction))

def move_bigDC(power: int, direction: bool) -> None:
    #1 - forward, 0 - for backward
    send_command(cmd_id=5, arg1=power, arg2=int(direction))
    print(f"Big DC motor running at power {power} in {'forward' if direction else 'backward'} direction...")
    time.sleep(4)
    send_command(cmd_id=5, arg1=0, arg2=int(direction))
   
def move_stepper(degrees: int) -> None:
    print(f"Moving stepper to {degrees} degrees...")
    send_command(cmd_id=2, arg1=degrees, arg2=0)

def shoot_card(power: int) -> None:
    print(f"Shooting card with power: {power}")
    send_command(cmd_id=3, arg1=power, arg2=0)

def send_card_position(degree: int, power: int) -> None:
    print(f"Sending card position: {degree}, Power: {power}")
    send_command(cmd_id=8, arg1=degree, arg2=power)

if __name__ == "__main__":
    try:
        move_stepper(-90)
        time.sleep(4)
        shoot_card(mid_power)
        for i in range(4):
            move_stepper(0)
            time.sleep(2)
            move_stepper(90)
            time.sleep(2)
        # move_stepper(0)
    finally:
        sock.close()