import socket
import sys

# !!! CHECK SERIAL MONITOR FOR NEW IP !!!
ARDUINO_IP = "10.28.182.16"
UDP_PORT = 4210

def send_and_wait(cmd_type, arg1, arg2):
    # Create socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(3.0) # Wait 3 seconds max for reply
    
    msg = f"{cmd_type} {int(arg1)} {int(arg2)}"
    
    try:
        # 1. Send
        print(f"[Python] Sending: {msg}")
        sock.sendto(msg.encode(), (ARDUINO_IP, UDP_PORT))
        
        # 2. Wait for Reply (Blocking)
        data, addr = sock.recvfrom(1024)
        print(f"[Python] Reply: {data.decode()}")
        
    except socket.timeout:
        print("[Python] Error: No reply from Arduino. Check IP or WiFi.")
    finally:
        sock.close()

def gearR(angle):
    return -2 / 3 * angle + 120 

def gearL(angle):
    return -2 / 3 * angle + 180

# --- RUN COMMAND ---
# Example: Send Angle Command
send_and_wait(2, gearR(60), gearL(120))

# Example: Send Spin Command (Uncomment to use)
# send_and_wait(1, 180, 2000)