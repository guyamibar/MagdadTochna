import os
import cv2
import numpy as np
import sys
import io
from contextlib import redirect_stdout

# Add game_structure to path to import CardClassifier and TemplateCardClassifier
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'game_structure'))
from game_structure.card_classification import CardClassifier, TemplateCardClassifier

# Constant warp points from visualize_crop.py (perspective_1)
# Order: Top-Left, Top-Right, Bottom-Right, Bottom-Left
CROP_POINTS = [[150, 170], [230, 130], [310, 320], [230, 360]]

def detect_character(img, name="Char"):
    """Advanced character isolation using Blur, Adaptive Threshold, Canny, and Contours."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 1. Gaussian Blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # 2. Adaptive Threshold for dynamic binarization
    binary = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                   cv2.THRESH_BINARY_INV, 11, 2)
    
    # 3. Canny Edge Detection
    edges = cv2.Canny(binary, 100, 200)
    
    # 4. Dilate/Close to bridge gaps in edges
    kernel = np.ones((3,3), np.uint8)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
    
    # 5. Find Contours and pick the largest one
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
        
    best_cnt = max(contours, key=cv2.contourArea)
    
    # Optional: Display debug steps for this character
    # cv2.imshow(f"Edges {name}", edges)
    
    # 6. Tight crop from the binary image for the final template
    x, y, w, h = cv2.boundingRect(best_cnt)
    if w < 5 or h < 5: # Filter out noise
        return None
        
    char_crop = binary[y:y+h, x:x+w]
    return cv2.resize(char_crop, (50, 70))

def classify_card_image(img, quiet=True):
    """
    Receives an image, applies a specific 4-point perspective warp, 
    flips it upside down, and returns the best classification result.
    """
    if img is None:
        return {"label": "Error", "confidence": 0.0, "method": "None"}

    # 1. Perspective Warp
    out_w, out_h = 200, 300
    pts1 = np.float32(CROP_POINTS)
    pts2 = np.float32([[0, 0], [out_w, 0], [out_w, out_h], [0, out_h]])
    matrix = cv2.getPerspectiveTransform(pts1, pts2)
    warped = cv2.warpPerspective(img, matrix, (out_w, out_h))

    # 2. Flip upside down
    processed_img = cv2.rotate(warped, cv2.ROTATE_180)

    # 3. Mirror the image (horizontal flip)
    processed_img = cv2.flip(processed_img, 1)

    # 4. Display the processed image
    cv2.imshow("Classification Input (Warped+Flipped+Mirrored)", processed_img)

    # 5. Split into Rank and Suit halves (Horizontal split)
    # The processed image is 200x300 (WxH)
    rank_img = processed_img[0:170, 0:200]
    suit_img = processed_img[170:300, 0:200]

    cv2.imwrite("data/test_outputs/rank_half.jpg", rank_img)
    cv2.imwrite("data/test_outputs/suit_half.jpg", suit_img)

    # 6. Isolate the characters using the new pipeline
    clean_rank = detect_character(rank_img, "Rank")
    clean_suit = detect_character(suit_img, "Suit")

    if clean_rank is not None:
        cv2.imshow("Isolated Rank (Final)", clean_rank)
    if clean_suit is not None:
        cv2.imshow("Isolated Suit (Final)", clean_suit)

    print("Review the windows, then press any key to classify...")
    cv2.waitKey(0)

    # 7. Classification
    template_classifier = TemplateCardClassifier()
    cnn_classifier = CardClassifier()

    f = io.StringIO()
    with redirect_stdout(f if quiet else sys.stdout):
        c_res = cnn_classifier.classify_image(processed_img)
        t_res = template_classifier.classify_image(processed_img)

    # Compare results and pick the best
    if c_res.confidence >= t_res.confidence:
        return {"label": c_res.label, "confidence": c_res.confidence, "method": "CNN"}
    else:
        return {"label": t_res.label, "confidence": t_res.confidence, "method": "Template"}

if __name__ == "__main__":
    # Test script
    image_dir = os.path.join('..', 'game_structure', 'data', 'hidden camera')
    if os.path.exists(image_dir):
        image_files = [f for f in os.listdir(image_dir) if f.endswith(('.jpg', '.png'))]
        if image_files:
            test_path = os.path.join(image_dir, image_files[3])
            print(f"Testing with: {test_path}")
            test_img = cv2.imread(test_path)
            result = classify_card_image(test_img, quiet=False)
            print(f"\nFinal Result: {result}")
        else:
            print("No images found in test directory.")
    else:
        print(f"Test directory not found: {image_dir}")
