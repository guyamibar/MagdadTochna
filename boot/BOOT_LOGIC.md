# Booting Logic & Workflow

The `boot` folder contains the scripts responsible for initializing the system, coordinating the communication between the physical hardware (camera, robotic arm, dealing mechanisms), the computer vision pipeline, and the AI game engine.

## `bootstrap.py` (The Main Entry Point)

`bootstrap.py` is the master orchestrator. When executed, it resets the physical and logical state and spawns three concurrent threads to manage the game:

1.  **Telegram Bot Thread (`thread_run_bot`)**:
    *   Starts the `run_bot.py` script from the `prompt_engineering_bot` module.
    *   This bot handles interactions with the user (receiving game rules, starting games, overriding moves).
2.  **Dealer Monitor Thread (`thread_run_dealer_start_loop_check`)**:
    *   Continuously monitors `prompt_engineering_bot/data/dealing.txt`.
    *   When the Telegram bot writes dealing instructions (e.g., "PLAYER 1: 3"), this thread intercepts it, parses the counts, and uses `translate_dealer_start_info_to_physical.py` to trigger the physical card shooter, distributing cards to `MYDECK`, `DECKPLAYER_1`, `DECKPLAYER_2`, and `PUBPILE_1`.
3.  **Main Game Turn Loop (`thread_run_game_turn_loop`)**:
    *   Waits for the physical "Turn Button" to be pushed.
    *   Upon button press, triggers `shoot_and_detect()` to capture an image and detect cards using the `Gsd` pipeline.
    *   Translates the physical detection into a structured string using `photo_to_state_translation.py`.
    *   Writes this state to `current_game_state_input.txt`, which prompts the AI to generate its next move.
    *   Waits for the AI to write its decision to `next_move.txt`.
    *   Translates the AI's textual move into physical arm commands via `translate_from_ai_move_to_physical.py` (moving, flipping, and grabbing/dropping).

## Hand Management (`hand_manager.py` & `hand_state.txt`)

Because face-down cards cannot be identified by the camera once they are in the player's hand, the system relies on a persistent memory file: `prompt_engineering_bot/data/hand_state.txt`.

### Structure of `hand_state.txt`
The state uses a JSON dictionary mapping the 6 physical `MYCARDS` slots to a list containing the card's identity and its visibility status:
```json
{
    "MYCARDS_1": ["Ace of Spades", "CLOSED"],
    "MYCARDS_2": [null, null]
}
```

### When is it Updated?
1.  **System Boot**: `bootstrap.py` resets the hand to 6 empty, unknown slots (`[None, None]`).
2.  **Physical Movement (Entering Hand)**: In `translate_from_ai_move_to_physical.py`, if the AI instructs a card to move to a `MYCARDS` slot and remain closed, the arm physically moves it, flips it up to inspect the rank/suit using the camera (`hm.look_at_card()`), flips it back down, and calls `hm.add_to_hand(dest, card_identity, "CLOSED")`. If it moves to `MYOPEN` physically, it is logged as `hm.add_to_hand(dest, card_identity, "OPEN")`.
3.  **Physical Movement (Leaving Hand)**: If the AI instructs a card to be played from `MYCARDS` to a public pile, `hm.remove_from_hand(src)` is called, clearing that slot in memory to `[None, None]`.
4.  **State Flipping**: If the AI instructs a move that requires flipping a card currently in `MYCARDS` (e.g., from `MYCLOSED` to `MYOPEN`), the arm physically flips the card, and `hm.flip_card_status(src)` is called to toggle the status between "OPEN" and "CLOSED".

### When is it Used?
`hand_state.txt` is consumed by `photo_to_state_translation.py` during the **Main Game Turn Loop** (Phase 1/2):
*   After capturing an image, the system looks at the physical layout.
*   For any `MYCARDS` slot detected as having a face-down card, it queries `hm.CLOSED` to retrieve the hidden identity and verify it is indeed marked as "CLOSED" in memory.
*   Cards marked as "OPEN" in memory (or detected as face-up physically) are appended to the `MYOPEN` list for the AI.
*   Cards marked as "CLOSED" and physically confirmed to be face-down by the camera are appended to the `MYCLOSED` list.
*   This ensures the AI receives a precise list of its available open and hidden cards, bridging the gap between physical computer vision limitations and the logical game state.
