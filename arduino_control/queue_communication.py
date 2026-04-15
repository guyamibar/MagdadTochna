import socket
import struct
from typing import Tuple, List

class ArduinoCommander:
    def __init__(self, hostname: str, port: int):
        self.hostname = hostname
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(2.0)
        
        # This is your internal queue!
        self.command_queue: List[Tuple[int, float, float]] = []
        
        try:
            print(f"Looking for {self.hostname}...")
            self.ip = socket.gethostbyname(self.hostname)
            print(f"Found Arduino at: {self.ip}")
        except socket.gaierror:
            print(f"⚠️ Warning: Could not find {self.hostname}. Running in Offline Mode.")
            self.ip = "0.0.0.0"

    def queue_command(self, cmd_id: int, arg1: float, arg2: float) -> None:
        """Adds a command to the waiting queue."""
        self.command_queue.append((cmd_id, arg1, arg2))
        print(f"Queued cmd: {cmd_id} - Queue size: {len(self.command_queue)}")

    def send_all(self) -> None:
        """Packs and sends all queued commands to the Arduino, then clears the queue."""
        if not self.command_queue:
            print("Queue is empty, nothing to send.")
            return

        payload = bytearray()
        
        for cmd_id, arg1, arg2 in self.command_queue:
            # Pack the data: '<' (little-endian), 'B' (1 byte), 'f' (4 bytes), 'f' (4 bytes)
            packed_command = struct.pack('<Bff', cmd_id, arg1, arg2)
            payload.extend(packed_command)
            
        print(f"\n🚀 Firing batch of {len(self.command_queue)} commands ({len(payload)} bytes)...")
        self.sock.sendto(payload, (self.ip, self.port))
        
        # VERY IMPORTANT: Clear the queue after sending so we don't resend old commands
        self.command_queue.clear()

        # Optional: Wait for the Arduino's reply
        try:
            data, addr = self.sock.recvfrom(1024)
            print(f"Arduino Reply: {data.decode()}\n")
        except socket.timeout:
            print("No reply from Arduino.\n")

    def close(self):
        """Clean up the socket connection."""
        self.sock.close()


# --- Main Execution ---
if __name__ == "__main__":
    # Create one global instance of your commander
    commander = ArduinoCommander("player-nano.local", 4210)
    
    try:
        print("--- Simulating a game loop ---")
        
        # Add commands from anywhere in your code whenever you want
        commander.queue_command(1, 10.5, -3.14)
        commander.queue_command(2, 0.0, 42.42)
        
        # ... maybe some time passes or other logic happens ...
        
        commander.queue_command(3, 100.1, 50.5)
        commander.queue_command(4, 9.99, 1.11)
        
        # Now, flush the queue and send them all at once!
        commander.send_all()
        
        print("your fon linging bring bring bring")
        
    finally:
        commander.close()