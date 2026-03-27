import socket
import time

# כאן תכתוב את ה-IP שמצאת ב-tcpdump
ARDUINO_IP = "10.28.182.178" 
UDP_PORT = 4210

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def pulse_motor(speed=200):
    print(f"Sending speed {speed} to Arduino at {ARDUINO_IP}...")
    # שליחת המהירות
    sock.sendto(str(speed).encode(), (ARDUINO_IP, UDP_PORT))
    
    # בגלל שהוספנו מנגנון ביטחון בארדואינו, 
    # הוא יכבה את המנוע לבד אחרי שניה אם לא נשלח כלום.
    print("Command sent. Motor should stop automatically in 1 second.")

pulse_motor(200)
sock.close()