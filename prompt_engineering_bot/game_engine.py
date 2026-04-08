import os
import sys
from pathlib import Path
from google import genai

# Add algorithmic_solvers to path
ALGO_PATH = Path(__file__).parent / "algorithmic_solvers"
sys.path.append(str(ALGO_PATH))

try:
    from uno_solver import solve as solve_uno
    from blackjack_solver import solve as solve_blackjack
    from war_solver import solve as solve_war

    ALGO_SOLVERS = {
        "UNO": solve_uno,
        "BLACKJACK": solve_blackjack,
        "WAR": solve_war
    }
except ImportError as e:
    print(f"Warning: Solvers not available: {e}")
    ALGO_SOLVERS = {}

# Best practice: Set this in your terminal/system, not in the code itself!
os.environ["GEMINI_API_KEY"] = "AIzaSyCHyk8QN1UjtybX1WJOV-MNgVIxdLBAyXg"
client = genai.Client()

# Model Fallback List (Ordered by preference)
MODELS = [
    "gemini-flash-lite-latest",
    "gemini-2.0-flash-lite-preview-02-05", # Fastest/Latest Lite
    "gemini-1.5-flash",                  # Most stable
    "gemini-1.5-flash-8b",               # Smallest/Fastest
    "gemini-1.0-pro"                     # Legacy Stable
]

def generate_content_with_fallback(prompt, model_list=MODELS):
    """Try models in order if one is overloaded or rate-limited."""
    for model_id in model_list:
        try:
            response = client.models.generate_content(model=model_id, contents=prompt)
            return response.text.strip(), model_id
        except Exception as e:
            # Check for rate limit or high demand (ResourceExhausted)
            if "429" in str(e) or "ResourceExhausted" in str(e):
                print(f"⚠️ Model {model_id} is busy. Trying fallback...")
                continue
            else:
                # Re-raise other unexpected errors
                raise e
    raise Exception("❌ All Gemini models are currently unavailable or rate-limited.")

STRUCTURED_RULES_FILE = Path(__file__).parent / "data" / "structured_rules_cache.txt"
RAW_RULES_FILE = Path(__file__).parent / "data" / "raw_rules_input.txt"
GAME_STATE_FILE = Path(__file__).parent / "data" / "current_game_state_input.txt"
NEXT_MOVE_FILE = Path(__file__).parent / "data" / "next_move.txt"


def generate_structured_rules(raw_rules_input):
    """Stage 1: Transform human rules into machine-structured logic."""
    RAW_RULES_FILE.write_text(raw_rules_input, encoding="utf-8")
    clean_rules = raw_rules_input.strip().upper()
    if clean_rules in ALGO_SOLVERS:
        STRUCTURED_RULES_FILE.write_text(clean_rules, encoding="utf-8")
        return clean_rules

    prompt_1 = f"""
	You are an expert game designer and logic engine. I am going to provide you with the raw rules for a game. Your task is to rewrite and structure these rules into a highly organized, unambiguous format optimized for a computer to understand.

	First, establish the foundational mechanics of the game engine:
	1. We have a regular deck of cards, with 4 suits (Spades, Hearts, Diamonds, Clubs), and 13 ranks (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, J, K, Q).
	2. At each turn, a player can take cards and move them from their source to a destination they choose.
	3. Each player can have open cards (shown to everybody) and closed cards (shown only to them).
	4. Drawing a card from a deck/pile is essentially moving a card from the deck/pile to the destination that is the player's closed cards.
	5. Draw Source: If the rules say "draw from deck" or "draw from pile", use PUBLIC_DECK or P1-P6 depending on what the raw rules specify. Defaultly the public pile is P1.
	6. If valid, a player can pass their turn, before or after playing another action.
	7. IMPORTANT: No move is legal unless it is explicitly permitted by the rules provided below. If the rules don't say you can play a card, you can't play it.
	8. IMPORTANT: Cards in MYCLOSED are ALWAYS considered accessible for the player to play from, even if they are not 'open' to others.
	9. Internal moves (e.g., from MYCLOSED to MYOPEN) are NOT allowed unless the rules specifically mention "opening" or "revealing" a card as an action.
	10. If a PUBLIC PILE has "NONE" as its top card, it is considered empty.

	**Raw Rules:**
	{raw_rules_input}

	These are the rules, and if something is not stated here, then it does not apply!

	Break the rules down into these exact sections:
	0. Game Environment Setup
	1. Core Objective & Win Condition
	2. Explicit Permissions (Draw from pile? Pass turn?)
	3. Turn Phases
	4. Legal Actions
	5. Constraints & Edge Cases

	Output only the structured rules. Do not include introductory or concluding remarks.
	"""
    structured, used_model = generate_content_with_fallback(prompt_1)
    STRUCTURED_RULES_FILE.write_text(structured, encoding="utf-8")
    return structured


def analyze_turn(structured_rules, game_state_input):
    """Stages 2-4: Execute the move logic based on rules and state."""

    # --- Algorithmic Override Check (STRICT) ---
    # We check BOTH the cache AND the raw input to be absolutely sure
    raw_rules = RAW_RULES_FILE.read_text(encoding="utf-8").strip().upper()
    cache_rules = structured_rules.strip().upper()

    if raw_rules in ALGO_SOLVERS or cache_rules in ALGO_SOLVERS:
        algo_key = raw_rules if raw_rules in ALGO_SOLVERS else cache_rules
        result_list, reasoning = ALGO_SOLVERS[algo_key](game_state_input)
        return {"final_result": "\n".join(result_list), "strategy": reasoning, "algo": True}

    # --- STAGE 2: Legal Moves ---
    prompt_2 = f"""
You are a robotic, literal rules enforcement engine. Analyze the state and list every legal move based ONLY on the provided rules.
1. DO NOT assume standard rules.
2. DO NOT ignore source/destination constraints.
3. If a rule specifies a draw destination, follow it.

<STRUCTURED_RULES>
{structured_rules}
</STRUCTURED_RULES>

<GAME_STATE>
{game_state_input}
</GAME_STATE>
"""
    legal_moves, _ = generate_content_with_fallback(prompt_2)

    # --- STAGE 3: Strategy ---
    prompt_3 = f"""
You are an expert tactical advisor. Determine the single best move from the verified legal list.

**Rules:** {structured_rules}
**State:** {game_state_input}
**Legal Moves:** {legal_moves}
"""
    strategy, _ = generate_content_with_fallback(prompt_3)

    # --- STAGE 4: Validation & Formatting ---
    prompt_4 = f"""
You are a strict, logical final validation engine for a card game. Your sole purpose is to verify that a proposed move is 100% legal according to the rules and the current game state, and to translate that move into machine-readable syntax.
<RULES>
{structured_rules}
</RULES>
<GAME_STATE>
{game_state_input}
</GAME_STATE>
<PROPOSED_MOVE>
{strategy}
</PROPOSED_MOVE>
<INSTRUCTIONS>
Perform a rigorous sanity check. You must determine:
1. Does the proposed move violate any constraints in the <RULES>?
2. Does the player actually possess the required cards in the stated location within the <GAME_STATE>?
**CRITICAL FALLBACK LOGIC:**
If the <PROPOSED_MOVE> is determined to be ILLEGAL, but there is a deck that the player can draw from according to the <RULES> and <GAME_STATE>, you must treat the move as drawing from the public deck instead of returning an error. In this case, output the legal draw action (e.g., * src: PUBLIC_DECK, dest: MYCLOSED, card: None).
Additionally, follow this fallback procedure: if the given play is not legal then play some legal move. if there isnt a legal move and there is a deck then draw from the deck.

Translate the move into the exact syntax required. You must strictly use the following location nomenclature for the 'src' (source) and 'dest' (destination):
* PUBLIC_DECK 
* P1 to P6 (Public pile number i, e.g., P2)
* MYCLOSED  (My closed/hidden hand, only i see this)
* MYOPEN (My open/visible cards)
* MYDECK (a Deck that only player that can draw is the me. nobody sees the cards)
* PLAYERi_OPEN (Player i's open cards, e.g., PLAYER2_OPEN, i =2,3)
* PLAYERi_DECK (Player i's deck, e.g.,PLAYER2_DECK, i =2,3)

If the action is to draw a card (where the specific card is unknown or being pulled from a deck), the 'card' value must be exactly 'None'. 
Do not output any conversational filler. Output strictly according to one of the two formats below.
</INSTRUCTIONS>
<OUTPUT_FORMAT_LEGAL>
If the move is legal, output a bulleted list of the exact actions.
Every line must be exactly "* src: SOURCE, dest: DESTINATION, card: CARDNAME".
If drawing a card, use 'None' for the card.
Explictly write out the card only if the source if MYOPEN or MYCLOSED.
The final bullet point must always be exactly "* PASS".
No comments, no reasoning, no extra words.
Example Legal Output:
* src: MYOPEN, dest: P1, card: Ace of Spades
* PASS
Provide your final output below(dont write other things besides the given format):
Every line of the output MUST strictly follow the format: * src: SOURCE, dest: DESTINATION, card: CARDNAME
The final line MUST be: * PASS
DO NOT include any analysis, reasoning, or 'Illegal Move' text.
"""
    final_result, _ = generate_content_with_fallback(prompt_4)
    return {
        "legal_moves": legal_moves,
        "strategy": strategy,
        "final_result": final_result,
        "algo": res.get("algo", False) if 'res' in locals() else cache_rules in ALGO_SOLVERS
    }


if __name__ == "__main__":
    if not STRUCTURED_RULES_FILE.exists() or STRUCTURED_RULES_FILE.stat().st_size == 0:
        if RAW_RULES_FILE.exists():
            raw_rules = RAW_RULES_FILE.read_text(encoding="utf-8")
            generate_structured_rules(raw_rules)
        else:
            print("Error: No rules configured.")
            exit(1)

    rules = STRUCTURED_RULES_FILE.read_text(encoding="utf-8")
    state = GAME_STATE_FILE.read_text(encoding="utf-8")
    res = analyze_turn(rules, state)

    # print(f"\nREASONING ({etype}): {res['strategy']}")
    NEXT_MOVE_FILE.write_text(res['final_result'], encoding="utf-8")
