"""
Playing card representation module.

This module defines the Card class which represents a playing card with
its label, rank, suit, value, and position information.
"""

from __future__ import annotations

from models import Point2D, Point3D

# Mapping of rank names to numeric values
RANK_VALUES: dict[str, int] = {
    "A": 1,
    "J": 11,
    "Q": 12,
    "K": 13,
}


class Card:
    """
    Represents a playing card.

    A card has a label (e.g., "10S" for 10 of Spades), which encodes both
    the rank and suit. The card also tracks its pixel and world-space locations.

    Attributes:
        label: Full card label (e.g., "10S", "KH", "AC").
        rank_name: Rank portion of label (e.g., "10", "K", "A").
        suit: Suit letter (S=Spades, H=Hearts, C=Clubs, D=Diamonds).
        value: Numeric value (A=1, 2-10, J=11, Q=12, K=13).
        pixels: Pixel coordinates in the image.
        location: 3D world coordinates in meters.
        edges: True if card was detected with both edges visible.
        confidence: Classification confidence score (0.0 to 1.0).
    """

    def __init__(
        self,
        label: str,
        pixel_location: Point2D | None = None,
        edges: bool = True,
        confidence: float = 0.0,
    ) -> None:
        """
        Initialize a Card instance.

        Args:
            label: Card label in format "<rank><suit>" (e.g., "10S", "KH").
                   Use "N" for an unknown/null card.
            pixel_location: Initial pixel coordinates.
            edges: True if both edges of the card were detected.
            confidence: Classification confidence score.
        """
        self.pixels: Point2D = pixel_location or Point2D(x=0, y=0)
        self.location: Point3D = Point3D(x=0.0, y=0.0, z=0.0)
        self.edges = edges
        self.confidence = confidence

        if label == "N":
            self.label = "N"
            self.rank_name = ""
            self.suit = ""
            self.value = 0
        else:
            self.label = label.upper()
            self.rank_name = label[:-1].upper()
            self.suit = label[-1].upper()
            self.value = self._calculate_value()

    def _calculate_value(self) -> int:
        """
        Calculate the numeric value of the card based on rank.

        Returns:
            Integer value: A=1, 2-10 as-is, J=11, Q=12, K=13.
        """
        if self.rank_name in RANK_VALUES:
            return RANK_VALUES[self.rank_name]
        return int(self.rank_name)

    def __str__(self) -> str:
        """Return human-readable string representation."""
        return (
            f"{self.rank_name} of {self.suit} at ({self.location.x:.2f}, {self.location.y:.2f}, {self.location.z:.2f})"
        )

    def __repr__(self) -> str:
        """Return detailed representation for debugging."""
        return f"Card('{self.label}', pixels=({self.pixels.x}, {self.pixels.y}))"
