from typing import List
from pydantic import BaseModel

class Card(BaseModel):
    rank: str
    suit: str

class Player(BaseModel):
    hand: int  # Your notes say int, likely for hand count
    open: List[Card]
    deck: bool

class GameState(BaseModel):
    heaps_heads: List[Card]
    deck: bool
    players: List[Player]
    my_hand: List[Card]
    my_open: List[Card]
    my_deck: bool

# # --- Example Usage ---

# # 1. Create an object
# current_game = GameState(
#     heaps_heads = [Card(rank="10", suit="Spades")],
#     deck = True,
#     players = [Player(hand=5, open=[], deck=False)],
#     my_hand = [Card(rank="A", suit="Hearts")],
#     my_open = [],
#     my_deck = True
# )

# def print_ai_format(game_state: GameState):
#     print("PUBLIC PILES TOP CARDS:")
#     for i, card in enumerate(game_state.heaps_heads, 1):
#         print(f"{i}. Top pile Card: {card.rank} of {card.suit}")
#     print()
#     print("MY OPEN CARDS:", "NONE" if not game_state.my_open else f"[{', '.join(f'{c.rank} of {c.suit}' for c in game_state.my_open)}]")
#     print("MY CLOSED CARDS:", f"[{', '.join(f'{c.rank} of {c.suit}' for c in game_state.my_hand)}] (all face down, shown to only to me)" if game_state.my_hand else "NONE")
#     for i, player in enumerate(game_state.players, 1):
#         print(f"PLAYER {i} OPEN CARDS:", False if not player.open else f"[{', '.join(f'{c.rank} of {c.suit}' for c in player.open)}]")
#         print(f"PLAYER {i} DECK:", player.deck)
#     print()
#     print("MYDECK:", game_state.my_deck)
#     print("MYOPEN:", "NONE" if not game_state.my_open else f"[{', '.join(f'{c.rank} of {c.suit}' for c in game_state.my_open)}]")
#     print("PUBLICDECK:", game_state.deck)

# print_ai_format(current_game)



# # 2. Convert to JSON string
# json_data = current_game.model_dump_json(indent=2)
# print(f"JSON Output: {json_data}")

# # 3. Convert back from JSON string to Object
# new_game_obj = GameState.model_validate_json(json_data)
# print(f"Object Val: {new_game_obj.my_hand[0].rank}")