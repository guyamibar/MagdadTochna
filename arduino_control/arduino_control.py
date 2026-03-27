import socket
import time
ARDUINO_IP = "10.28.182.16"
UDP_PORT = 4210

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", UDP_PORT))

def send_command(cmd_id, arg1=0, arg2=0):
    # יצירת המחרוזת בפורמט שהארדואינו מצפה לו (עם רווחים)
    message = f"{cmd_id} {arg1} {arg2}"
    print(f"Sending command: {message}")
    sock.sendto(message.encode(), (ARDUINO_IP, UDP_PORT))

print("System Ready. Sending commands...")

# דוגמה 1: סע קדימה (פקודה 1) במהירות 200 למשך 1000 מילי-שניות
# send_command(1, 180, 450)
# time.sleep(2) 

# דוגמה 2: הלוך-חזור (פקודה 2) במהירות 180 למשך 500 מילי-שניות לכל כיוון
# send_command(2, 100, 80)
# time.sleep(2)
send_command(3, 44, 0)


sock.close()