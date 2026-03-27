"""
Helper functions for card extraction.

This module provides utility functions for extracting and saving
card images from larger images for testing and debugging purposes.
"""

from __future__ import annotations

import os

import cv2
import numpy as np
from card_detection import CardOutlineDetector


def extract_cards(image: np.ndarray) -> None:
    """
    Extract and save all detected cards from an image.

    Detects card outlines in the image, warps each card to a standard
    size, and saves them to the "Card test" folder with random filenames.

    Args:
        image: BGR image containing cards to extract.

    Note:
        Creates files in the "Card test" directory. Ensure this
        directory exists before calling this function.
    """
    cards = CardOutlineDetector.get_card_outlines(image, include_img=True)
    for card in cards:
        if card.warped_image is not None:
            filename = f"card_{np.random.randint(10000)}.jpg"
            filepath = os.path.join("Card test", filename)
            cv2.imwrite(filepath, card.warped_image)


if __name__ == "__main__":
    img = cv2.imread(os.path.join("Test ims", "im1.jpg"))
    extract_cards(img)
