"""
Deck of playing cards module.

This module provides the Deck class which represents a standard 52-card
deck of playing cards with shuffle and removal operations.
"""

from __future__ import annotations

import random

from card import Card

# Standard deck configuration
RANKS: list[str] = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
SUITS: list[str] = ["S", "H", "C", "D"]


class Deck:
    """
    Represents a standard 52-card deck of playing cards.

    The deck is initialized with all 52 cards (13 ranks × 4 suits).
    Cards can be shuffled and removed as they are detected on the table.

    Attributes:
        cards: List of Card objects currently in the deck.
    """

    def __init__(self) -> None:
        """Initialize a new deck with all 52 cards."""
        self.cards: list[Card] = [Card(rank + suit) for suit in SUITS for rank in RANKS]

    def __repr__(self) -> str:
        """Return short representation showing card count."""
        return f"Deck({len(self.cards)} cards remaining)"

    def __str__(self) -> str:
        """Return detailed string listing all cards in the deck."""
        lines = [f"there are {len(self.cards)} cards in the deck:"]
        for card in self.cards:
            lines.append(str(card))
        return "\n".join(lines)

    def shuffle(self) -> None:
        """Randomly shuffle the cards in the deck."""
        random.shuffle(self.cards)

    def remove_card(self, label: str) -> bool:
        """
        Remove a specific card from the deck.

        Useful when a card is detected on the table by the camera.

        Args:
            label: Card label to remove (e.g., "10S", "KH").
                   Case-insensitive.

        Returns:
            True if the card was found and removed, False otherwise.
        """
        label_upper = label.upper()
        for card in self.cards:
            if card.label == label_upper:
                self.cards.remove(card)
                return True
        return False

    def count_remaining(self) -> int:
        """
        Return the number of cards remaining in the deck.

        Returns:
            Number of cards currently in the deck.
        """
        return len(self.cards)
