import json
import subprocess
from pathlib import Path

# Paths
BASE_DIR = Path(r"C:\Users\TLP-001\Documents\GitHub\MagdadTochna\prompt_engineering_bot")
DATA_DIR = BASE_DIR / "data"
RULES_FILE = DATA_DIR / "raw_rules_input.txt"
STATE_FILE = DATA_DIR / "current_game_state_input.txt"
MOVE_FILE = DATA_DIR / "next_move.txt"
PYTHON_EXE = Path(r"C:\Users\TLP-001\Documents\GitHub\MagdadTochna\.venv\Scripts\python.exe")
ENGINE_PY = BASE_DIR / "game_engine.py"
JSON_FILE = Path(r"C:\Users\TLP-001\eval_scenarios.json")

def run_engine():
    try:
        subprocess.run([str(PYTHON_EXE), str(ENGINE_PY)], check=True, capture_output=True)
        return MOVE_FILE.read_text(encoding="utf-8").strip()
    except Exception as e:
        return f"ERROR: {e}"

def run_batch(count):
    if not JSON_FILE.exists():
        print("No scenarios left.")
        return []

    with open(JSON_FILE, "r") as f:
        data = json.load(f)

    results = []
    for _ in range(min(count, len(data))):
        scen = data.pop(0)
        rules = scen[0]
        state = scen[1]
        
        RULES_FILE.write_text(rules, encoding="utf-8")
        STATE_FILE.write_text(state, encoding="utf-8")
        
        res = run_engine()
        results.append({
            "game": rules,
            "state": state,
            "result": res
        })

    with open(JSON_FILE, "w") as f:
        json.dump(data, f)
        
    return results

if __name__ == "__main__":
    batch_res = run_batch(10)
    with open("C:\\Users\\TLP-001\\batch_results.json", "w") as f:
        json.dump(batch_res, f, indent=2)
    print(f"Processed {len(batch_res)} scenarios.")
