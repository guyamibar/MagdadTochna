# Magdad System: The "Black Box" Logic

This document explains how the system transforms raw input into machine actions.

## 1. The Input-to-Output Flow
The system acts as a translator between human rules and mechanical execution:
*   **INPUTS:** 
    *   `raw_rules_input.txt`: Human-written game rules.
    *   `current_game_state_input.txt`: The physical state of the table.
*   **OUTPUTS:**
    *   `dealing.txt`: A sequence of hardware commands for the dealer.
    *   `next_move.txt`: The optimal tactical move for the bot.

## 2. Decision Architecture (The "If" Logic)
The system uses a tiered branching logic to ensure speed and accuracy:

### Phase A: Router (ALGO vs. AI)
*   **IF** the rules match a predefined keyword (e.g., `UNO`, `WAR`):
    *   Bypass the LLM and trigger the **Algorithmic Solver** (Instant & 100% Deterministic).
*   **ELSE** (Custom Game):
    *   Trigger the **Multi-Stage AI Pipeline**.

### Phase B: The AI Pipeline (4-Stage Reasoning)
1.  **Stage 1 (Structuring):** Translates messy human text into a strict "Logical Rulebook."
2.  **Stage 2 (Legal Moves):** Lists every physically possible move based strictly on the Rulebook.
3.  **Stage 3 (Strategy):** Acts as a grandmaster to pick the single "Best" move from the legal list.
4.  **Stage 4 (Validation):** A final "Robotic" check to ensure the move follows the standardized `src: ..., dest: ..., card: ...` format.

## 3. Hardware Integration
The results are saved to `.txt` files which are monitored by the mechanical control scripts. Every file update triggers a physical response from the robotic arms.
