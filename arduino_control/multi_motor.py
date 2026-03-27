import socket
import time

ARDUINO_IP = "10.28.182.178" # עדכן ל-IP שלך
UDP_PORT = 4210

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def send_motor_cmd(cmd_type, arg1, arg2):
    # הפורמט: ID CMD SPEED DURATION
    msg = f"{cmd_type} {arg1} {arg2}"
    print(f"Sending: {msg}")
    sock.sendto(msg.encode(), (ARDUINO_IP, UDP_PORT))


def gearR(angle):
    return -2 / 3 * angle + 2 / 3 * 180
    
def gearL(angle):
    return -2 / 3 * angle + 180

send_motor_cmd(1, 200, 5000)
send_motor_cmd(2, gearR(60), gearL(120))

print("Commands sent. Arduino handles the timing independently.")
