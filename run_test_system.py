import os
import sys
import time
import threading
import subprocess
import cv2
from pathlib import Path

"""
FILE: run_test_system.py

DESCRIPTION:
    A testing wrapper for the Magdad System.
    - Press [SPACE BAR] to trigger a turn.
    - VISUALIZATION: Shows window if a display is found, otherwise saves to 'latest_detection.jpg'.
"""

# --- CROSS-PLATFORM KEYBOARD DETECTION ---
if os.name == 'nt':
    import msvcrt
    def get_key():
        if msvcrt.kbhit(): return msvcrt.getch()
        return None
else:
    import termios, tty, select
    def get_key():
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            rlist, _, _ = select.select([sys.stdin], [], [], 0.1)
            if rlist: return sys.stdin.read(1).encode()
            return None
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

# --- PATH SETUP ---
ROOT_DIR = Path(__file__).parent
sys.path.append(str(ROOT_DIR))
sys.path.append(str(ROOT_DIR / "boot"))

# 1. MOCK HARDWARE FUNCTIONS
import game_structure.phisical_function as pf
def mock_move_player(coords): print(f"🛠️ [MOCK] Move arm to {coords}")
def mock_grab(): print("🛠️ [MOCK] Grab card")
def mock_drop(): print("🛠️ [MOCK] Drop card")
def mock_shoot(coords): print(f"🛠️ [MOCK] Shoot card to {coords}")
def mock_flip(): print("🛠️ [MOCK] Flip card")
def mock_turn_dealer(degree): print(f"🛠️ [MOCK] Turn dealer to {degree}")
def mock_look_at_card():
    print("🛠️ [MOCK] Looking at card with second camera...")
    return "Mock Card (7 of Hearts)"

pf.move_player = mock_move_player
pf.grab = mock_grab
pf.drop = mock_drop
pf.shoot = mock_shoot
pf.flip = mock_flip
pf.turn_dealer = mock_turn_dealer
pf.look_at_card = mock_look_at_card

# 2. OVERRIDE BOOTSTRAP LOGIC
import boot.bootstrap as main_boot
import boot.shoot_photo as sp

# Detect if we have a GUI display (Linux specific check)
HAS_DISPLAY = os.name == 'nt' or os.environ.get('DISPLAY') is not None

def visual_shoot_and_detect():
    res = sp.shoot_and_detect()
    if res is not None and hasattr(res, 'annotated_image'):
        if HAS_DISPLAY:
            try:
                print("🖼️  [VISUAL] Refreshing detection window...")
                h, w = res.annotated_image.shape[:2]
                display_img = cv2.resize(res.annotated_image, (w//2, h//2))
                cv2.imshow("Magdad Vision - Last Capture", display_img)
                cv2.waitKey(1) 
            except Exception as e:
                print(f"⚠️  [VISUAL] Display error: {e}. Falling back to disk save.")
                cv2.imwrite("latest_detection.jpg", res.annotated_image)
        else:
            print("💾 [VISUAL] No display found. Saving detection to 'latest_detection.jpg'...")
            cv2.imwrite("latest_detection.jpg", res.annotated_image)
    return res

main_boot.shoot_and_detect = visual_shoot_and_detect

button_pushed_flag = False
def mock_button_check():
    global button_pushed_flag
    if button_pushed_flag:
        button_pushed_flag = False 
        return True
    return False

main_boot.turn_button_pushed = mock_button_check

def mock_thread_run_bot():
    print("🤖 [Thread 1] Launching Telegram Bot...")
    bot_script = ROOT_DIR / "prompt_engineering_bot" / "run_bot.py"
    if os.name == 'nt':
        subprocess.Popen([sys.executable, "-u", str(bot_script)], creationflags=0x00000010)
    else:
        subprocess.Popen([sys.executable, "-u", str(bot_script)])

main_boot.thread_run_bot = mock_thread_run_bot

# 3. SPACE BAR LISTENER
def simulate_button_listener():
    global button_pushed_flag
    print("\n⌨️  READY: Tap [SPACE BAR] in THIS window to trigger a game turn.")
    while True:
        key = get_key()
        if key == b' ': 
            button_pushed_flag = True
            print("\n🔘 [TEST] Space Bar Pressed! Starting turn...")
        time.sleep(0.05)

if __name__ == "__main__":
    print("""
    🧪 ==========================================
       MAGDAD SYSTEM TEST (ROBUST DISPLAY)
    ==========================================
    """)
    from boot.hand_manager import save_hand
    save_hand({f"MYCLOSED_{i}": None for i in range(1, 7)})
    
    threading.Thread(target=simulate_button_listener, daemon=True).start()
    
    t1 = threading.Thread(target=main_boot.thread_run_bot, name="BotThread", daemon=True)
    t2 = threading.Thread(target=main_boot.thread_run_dealer_start_loop_check, name="DealerThread", daemon=True)
    t3 = threading.Thread(target=main_boot.thread_run_game_turn_loop, name="GameThread", daemon=True)
    
    t1.start()
    t2.start()
    t3.start()
    
    try:
        while True:
            if HAS_DISPLAY: cv2.waitKey(100) 
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n\n🧹 Test session ended.")
        if HAS_DISPLAY: cv2.destroyAllWindows()
