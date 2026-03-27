import os
import subprocess
import sys
import time
from pathlib import Path

# --- CONFIGURATION ---
# Replace with your actual Telegram Bot Token or set it in your environment
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "7969985495:AAGara8w4HwQXsFx-T97D5lHEfJCZSTA3Sg")
# ---------------------

def start_system():
    # Set the environment variable for the bot
    os.environ["TELEGRAM_BOT_TOKEN"] = TELEGRAM_TOKEN
    
    print("🚀 --- MAGDAD SYSTEM HOST (BOT MODE) ---")
    
    BASE_DIR = Path(__file__).parent
    
    try:
        # 1. Start the Telegram Bot in unbuffered mode
        print("🤖 Starting Telegram Bot...")
        bot_proc = subprocess.Popen([sys.executable, "-u", str(BASE_DIR / "telegram_bot.py")])
        
        print("\n✅ BOT ONLINE")
        print("👉 The bot is now running persistently.")
        print("📝 Use /session in Telegram to start a game session.")
        print("🛑 Press Ctrl+C in THIS window to shut down the Bot.\n")

        # Keep the main script alive while the bot is running
        while True:
            if bot_proc.poll() is not None:
                print("\n⚠️ Telegram Bot stopped unexpectedly. Restarting in 5 seconds...")
                time.sleep(5)
                bot_proc = subprocess.Popen([sys.executable, "-u", str(BASE_DIR / "telegram_bot.py")])
            time.sleep(2)

    except KeyboardInterrupt:
        print("\n\n🧹 Shutting down system...")
    finally:
        # Clean up the bot process
        if 'bot_proc' in locals():
            bot_proc.terminate()
        print("✅ Cleanup complete.")

if __name__ == "__main__":
    if not TELEGRAM_TOKEN:
        print("❌ ERROR: TELEGRAM_BOT_TOKEN environment variable is not set.")
    else:
        start_system()
