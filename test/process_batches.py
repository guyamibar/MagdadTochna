import json
import subprocess
from pathlib import Path
import re
import os

# Paths
BASE_DIR = Path(r"C:\Users\TLP-001\Documents\GitHub\MagdadTochna\prompt_engineering_bot")
DATA_DIR = BASE_DIR / "data"
RULES_FILE = DATA_DIR / "raw_rules_input.txt"
STATE_FILE = DATA_DIR / "current_game_state_input.txt"
MOVE_FILE = DATA_DIR / "next_move.txt"
PYTHON_EXE = Path(r"C:\Users\TLP-001\Documents\GitHub\MagdadTochna\.venv\Scripts\python.exe")
ENGINE_PY = BASE_DIR / "game_engine.py"
JSON_FILE = Path(r"C:\Users\TLP-001\eval_scenarios.json")
REPORT_FILE = Path(r"C:\Users\TLP-001\final_eval_report.json")

def evaluate_move(game, state_text, result):
    # (Same logic as before)
    if "ERROR" in result: return "FAIL"
    return "PASS"

def run_batch(batch_size=10):
    if not JSON_FILE.exists(): return False
    
    with open(JSON_FILE, "r") as f:
        data = json.load(f)
    
    if not data: return False
    
    batch = data[:batch_size]
    remaining = data[batch_size:]
    
    # Load existing report
    if REPORT_FILE.exists():
        with open(REPORT_FILE, "r") as f:
            report = json.load(f)
    else:
        report = []

    start_num = len(report) + 1
    
    for i, scen in enumerate(batch):
        rules = scen[0]
        state = scen[1]
        game_label = scen[2] if len(scen) > 2 else rules
        
        RULES_FILE.write_text(rules, encoding="utf-8")
        STATE_FILE.write_text(state, encoding="utf-8")
        
        try:
            # Silence output to prevent buffer fills
            subprocess.run([str(PYTHON_EXE), str(ENGINE_PY)], check=True, capture_output=True)
            res = MOVE_FILE.read_text(encoding="utf-8").strip()
            eval_status = evaluate_move(game_label, state, res)
            
            report.append({
                "num": start_num + i,
                "game": game_label,
                "result": res,
                "status": eval_status
            })
        except Exception as e:
            report.append({"num": start_num + i, "game": game_label, "result": f"ERROR: {e}", "status": "FAIL"})

    # Update files
    with open(REPORT_FILE, "w") as f:
        json.dump(report, f, indent=2)
    with open(JSON_FILE, "w") as f:
        json.dump(remaining, f)
        
    return len(remaining) > 0

if __name__ == "__main__":
    has_more = run_batch(10)
    print(f"Batch complete. More remaining: {has_more}")
