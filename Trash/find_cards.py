
import cv2
import numpy as np
from pathlib import Path
from game_structure.card_detection import CardOutlineDetector
from game_structure.card_classification import CardClassifier

def find_missing_cards():
    img_path = Path("game_structure/data/game_table.jpg")
    img = cv2.imread(str(img_path))
    if img is None:
        print("Could not load image")
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
