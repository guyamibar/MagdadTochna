
import cv2
import numpy as np
import os
import sys
from pathlib import Path

# Add the project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from card_detection import CardOutlineDetector
from card_classification import CardClassifier

def find_missing_cards():
    img_path = Path(__file__).parent / "data" / "game_table.jpg"
    img = cv2.imread(str(img_path))
    if img is None:
        print(f"Could not load image: {img_path}")
        return

    detector = CardOutlineDetector()
    classifier = CardClassifier()

    cards = detector.get_card_outlines(img, include_img=True)
    
    print("Detected Cards:")
    for i, card in enumerate(cards):
        res = classifier.classify_image(card.warped_image)
        corners_list = card.corners.tolist()
        print(f"Card {i}: Label: {res.label}, Confidence: {res.confidence:.2f}, Corners: {corners_list}")

if __name__ == "__main__":
    find_missing_cards()
