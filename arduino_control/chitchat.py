import socket
import time
import threading
from datetime import datetime

# הגדרות
UDP_PORT = 4210
ARDUINO_IP = "10.255.102.178" # <--- עדכן לכתובת של הארדואינו שלך!

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", UDP_PORT))

# --- פונקציה 1: המקשיב (Listener) ---
# רצה ברקע ומדפיסה כל מה שמגיע מהארדואינו
def listen_to_arduino():
    print("Listener started...")
    while True:
        try:
            data, addr = sock.recvfrom(1024)
            message = data.decode()
            
            # עיצוב ההדפסה לפי סוג ההודעה
            if "HEARTBEAT" in message:
                # מדפיס בשורה אחת מתעדכנת (כדי לא להציף את המסך)
                print(f"\r[STATUS] {message}", end="")
            else:
                # הודעות רגילות יורדות שורה
                print(f"\n[REPLY]  {message}")
            time.sleep(1)  # מנוחה קטנה למניעת עומס
                
        except Exception as e:
            print(f"Error: {e}")

# --- פונקציה 2: המשדר האוטומטי (Auto-Sender) ---
# שולחת את השעה כל 3 שניות
def send_time_updates():
    print("Auto-Sender started...")
    while True:
        current_time = datetime.now().strftime("%H:%M:%S")
        msg = f"Time is {current_time}"
        
        # שליחה לארדואינו
        sock.sendto(msg.encode(), (ARDUINO_IP, UDP_PORT))
        time.sleep(1)
        

# --- הפעלה ---

# הפעלת המקשיב ברקע
t1 = threading.Thread(target=listen_to_arduino, daemon=True)
t1.start()

# הפעלת שולח הזמן ברקע
t2 = threading.Thread(target=send_time_updates, daemon=True)
t2.start()

print("--- System Running ---")
print("You can also type messages manually below:")

try:
    # הלופ הראשי מאפשר לך לכתוב הודעות ידניות תוך כדי
    while True:
        manual_msg = input() # מחכה שתכתוב משהו ותלחץ אנטר
        if manual_msg:
            sock.sendto(manual_msg.encode(), (ARDUINO_IP, UDP_PORT))
            print(f"Sent manually: {manual_msg}")

except KeyboardInterrupt:
    print("\nClosing connection...")
    sock.close()