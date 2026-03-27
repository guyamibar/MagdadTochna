import socket

UDP_PORT = 4210
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", UDP_PORT))

print("Listening for Arduino data to find IP...")

try:
    # 1. קבלת חבילה ראשונה כדי לגלות את הכתובת
    data, addr = sock.recvfrom(1024)
    arduino_ip = addr[0]
    print(f"Success! Arduino found at: {arduino_ip}")
    print(f"Resistance data: {data.decode()}")

    # 2. שליחת פקודת תנועה (מהירות 200)
    print("Sending pulse command...")
    sock.sendto("200".encode(), (arduino_ip, UDP_PORT))
    
    print("Command sent. The Arduino will handle the 1-second timing itself.")

finally:
    sock.close()