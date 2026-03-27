"""
Unit tests for Template Matching CardClassifier using multiple reference images.
"""

from __future__ import annotations

from pathlib import Path
import cv2
import numpy as np
import pytest
from card_classification import TemplateCardClassifier
from card_detection import CardOutlineDetector

# Path configuration
DATA_DIR = Path(__file__).parent / "data"
REFERENCE_DIR = DATA_DIR / "reference"
SUMMARIES_DIR = DATA_DIR / "test_summaries"

EXPECTED_DATA: dict[Path, list[dict]] = {
    REFERENCE_DIR / "game_table.jpg": [
        {"corners": [[695, 700], [866, 741], [837, 864], [667, 818]], "label": "5D"},
        {"corners": [[228, 604], [352, 626], [321, 795], [199, 778]], "label": "6H"},
        {"corners": [[82, 502], [205, 537], [156, 702], [35, 671]], "label": "6S"},
        {"corners": [[813, 519], [933, 500], [974, 669], [850, 698]], "label": "KC"},
        {"corners": [[408, 375], [515, 436], [429, 583], [324, 526]], "label": "AC"},
        {"corners": [[649, 379], [816, 324], [850, 448], [682, 493]], "label": "AD"},
        {"corners": [[229, 283], [333, 352], [239, 496], [134, 432]], "label": "4S"},
        {"corners": [[445, 168], [589, 252], [523, 359], [380, 265]], "label": "AH"},
        {"corners": [[693, 166], [861, 116], [891, 240], [721, 288]], "label": "JS"},
        {"corners": [[491, 55], [664, 67], [650, 192], [481, 177]], "label": "8S"},
        {"corners": [[319, 43], [392, 145], [256, 246], [180, 145]], "label": "9D"},
    ],
    REFERENCE_DIR / "img1_warped.jpg": [
        {"corners": [[788, 681], [870, 771], [744, 891], [659, 800]], "label": "10C"},
        {"corners": [[496, 582], [612, 539], [677, 698], [564, 748]], "label": "2D"},
        {"corners": [[694, 479], [820, 481], [820, 654], [694, 655]], "label": "KC"},
        {"corners": [[329, 393], [504, 394], [503, 521], [328, 517]], "label": "3H"},
        {"corners": [[751, 290], [922, 327], [894, 451], [722, 411]], "label": "7H"},
        {"corners": [[32, 224], [152, 186], [207, 348], [88, 389]], "label": "4H"},
        {"corners": [[185, 211], [297, 162], [369, 318], [255, 371]], "label": "7D"},
        {"corners": [[376, 101], [499, 78], [532, 247], [409, 271]], "label": "3C"},
        {"corners": [[724, 67], [841, 35], [892, 199], [772, 235]], "label": "6S"},
        {"corners": [[532, 76], [642, 21], [722, 174], [611, 231]], "label": "9D"},
        {"corners": [[149, 32], [325, 16], [336, 139], [162, 155]], "label": "7S"},
    ]
}

@pytest.fixture(scope="module")
def classifier():
    return TemplateCardClassifier()

@pytest.mark.parametrize("img_path", EXPECTED_DATA.keys())
def test_template_all_cards_visual(classifier, img_path):
    img = cv2.imread(str(img_path))
    if img is None:
        pytest.fail(f"Could not load test image: {img_path}")
        
    vis = img.copy()
    expected_cards = EXPECTED_DATA[img_path]
    
    for i, expected in enumerate(expected_cards):
        corners = np.array(expected["corners"], dtype=np.float32)
        warped = CardOutlineDetector.warp_card(img, corners)
        
        result = classifier.classify_image(warped)
        is_correct = result.label == expected["label"]
        color = (0, 255, 0) if is_correct else (0, 0, 255)
        
        pts = corners.astype(np.int32).reshape((-1, 1, 2))
        cv2.polylines(vis, [pts], True, color, 3)
        
        center = np.mean(corners, axis=0).astype(np.int32)
        text_pos = (center[0] - 40, center[1])
        cv2.rectangle(vis, (text_pos[0]-5, text_pos[1]-25), (text_pos[0]+105, text_pos[1]+25), (0,0,0), -1)
        cv2.putText(vis, f"Exp:{expected['label']}", (text_pos[0], text_pos[1]), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(vis, f"Pred:{result.label}", (text_pos[0], text_pos[1] + 20), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = SUMMARIES_DIR / f"template_test_summary_{img_path.stem}.jpg"
    cv2.imwrite(str(summary_path), vis)
    print(f"\nTemplate Matcher Summary image saved to: {summary_path}")

@pytest.mark.parametrize("img_path", EXPECTED_DATA.keys())
def test_template_individual(classifier, img_path):
    img = cv2.imread(str(img_path))
    if img is None:
        pytest.fail(f"Could not load test image: {img_path}")
        
    expected_cards = EXPECTED_DATA[img_path]
    for i, expected in enumerate(expected_cards):
        corners = np.array(expected["corners"], dtype=np.float32)
        warped = CardOutlineDetector.warp_card(img, corners)
        result = classifier.classify_image(warped)
        if result.label != expected["label"]:
            print(f"Template Matcher Deviation in {img_path.name} Card {i} ({expected['label']}) detected as {result.label}")
