import socket
import time

# -------------------------arduino communication setup-------------------------
_HOSTNAME = "dealer-nano.local"
_sock = None  # The underscore means "private, don't touch this from outside"
_ARDUINO_IP = None
_TCP_PORT = 4211
low_power = 100
mid_power = 150
high_power = 210


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
    
    print("❌ Failed to connect to Dealer ESP32 after 5 attempts. Continuing without hardware...")
    _sock = None


# Auto-connect the first time this module is imported anywhere
_connect()


def send_command(cmd_id: int, arg1: int = 0, arg2: int = 0, arg3: int = 0):
    """The ONLY public function other files are allowed to use."""
    global _sock
    if not _sock:
        print(f"📴 [Offline Simulation] Dealer command ignored: {cmd_id} {arg1} {arg2} {arg3}")
        return True

    message = f"{cmd_id} {arg1} {arg2} {arg3}\n"

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

def move_smallDC(power: int, direction: bool) -> None:
    # 1 - forward, 0 - for backward
    send_command(cmd_id=4, arg1=power, arg2=int(direction))
    print(f"Small DC motor running at power {power} in {'forward' if direction else 'backward'} direction...")
    time.sleep(4)
    send_command(cmd_id=4, arg1=0, arg2=int(direction))


def move_bigDC(power: int, direction: bool) -> None:
    # 1 - forward, 0 - for backward
    send_command(cmd_id=5, arg1=power, arg2=int(direction))
    print(f"Big DC motor running at power {power} in {'forward' if direction else 'backward'} direction...")
    time.sleep(4)
    send_command(cmd_id=5, arg1=0, arg2=int(direction))


def move_stepper(degrees: int) -> None:
    print(f"Moving stepper to {degrees} degrees...")
    send_command(cmd_id=3, arg1=degrees)


def shoot_card(power: int) -> None:
    print(f"Shooting card with power: {power}")
    send_command(cmd_id=2, arg1=power)


def shoot_cards(number_of_cards: int, angle: int, power: int) -> None:
    print(f"Shooting {number_of_cards} cards in {angle} degrees.")
    send_command(cmd_id=1, arg1=number_of_cards, arg2=angle, arg3=power)

if __name__ == "__main__":
    shoot_cards(number_of_cards=3, angle=30, power=175)