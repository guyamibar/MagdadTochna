"""
Card classification module.
Provides multiple methods for card identification:
1. CNN-based classifier (TensorFlow Lite) - Highest accuracy.
2. Advanced Template Matching - Corner-based ROI searching.
3. Simple Template Matching - Full-card comparison with slight rotations.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, List

import cv2
import numpy as np


import ai_edge_litert.interpreter as tflite


from models import CardClassification

# Path configuration
_MODULE_DIR: Path = Path(__file__).parent
CARDS_FOLDER: Path = _MODULE_DIR / "data" / "templates" / "cards"
TFLITE_MODEL_PATH: Path = _MODULE_DIR / "card_classifier_b3_quant.tflite"
BACKSIDE_TEMPLATE_PATH: Path = _MODULE_DIR / "data" / "templates" / "backside.jpg"
DEFAULT_IMG_SHAPE: int = 200

# Backside detection threshold
BACKSIDE_TEMPLATE_THRESHOLD: float = 0.25

# All possible card class names
CLASS_NAMES: list[str] = [
    "AC", "AD", "AH", "AS", "8C", "8D", "8H", "8S", "5C", "5D", "5H", "5S",
    "4C", "4D", "4H", "4S", "JC", "JD", "JH", "JS", "Joker", "KC", "KD", "KH", "KS",
    "9C", "9D", "9H", "9S", "QC", "QD", "QH", "QS", "7C", "7D", "7H", "7S",
    "6C", "6D", "6H", "6S", "10C", "10D", "10H", "10S", "3C", "3D", "3H", "3S",
    "2C", "2D", "2H", "2S"
]

# Rotation angles for simple template matching (degrees)
ROTATION_ANGLES: np.ndarray = np.linspace(-2, 2, 3)


class CardClassifier:
    """
    CNN-based card classifier with ensemble voting (0 and 180 degree views).
    Includes optional robust backside detection using a hybrid SIFT and Template approach.
    """
    def __init__(
        self,
        model_path: Path = TFLITE_MODEL_PATH,
        img_shape: int = DEFAULT_IMG_SHAPE,
    ) -> None:
        self.img_shape = img_shape
        self.interpreter = tflite.Interpreter(model_path=(model_path), num_threads=4)
        self.interpreter.allocate_tensors()
        self.class_names = CLASS_NAMES
        
        # Backside detection state
        self._backside_template_gray: Optional[np.ndarray] = None
        self._sift = cv2.SIFT_create(nfeatures=1000)
        self._kp_tpl: Optional[list] = None
        self._des_tpl: Optional[np.ndarray] = None

    def _load_backside_features(self) -> bool:
        """Lazy load backside template and extract SIFT features."""
        if self._des_tpl is not None:
            return True
            
        if not BACKSIDE_TEMPLATE_PATH.exists():
            print(f"Warning: Backside template not found at {BACKSIDE_TEMPLATE_PATH}")
            return False
            
        template = cv2.imread(str(BACKSIDE_TEMPLATE_PATH), cv2.IMREAD_GRAYSCALE)
        if template is None:
            print(f"Warning: Could not read backside template at {BACKSIDE_TEMPLATE_PATH}")
            return False
            
        self._backside_template_gray = template
        self._kp_tpl, self._des_tpl = self._sift.detectAndCompute(template, None)
        return self._des_tpl is not None

    def _get_template_score(self, gray_img: np.ndarray) -> float:
        """Calculate template matching score against backside template."""
        if self._backside_template_gray is None:
            return 0.0
            
        # Resize image to match template if needed
        h, w = self._backside_template_gray.shape
        if gray_img.shape != (h, w):
            img_resized = cv2.resize(gray_img, (w, h), interpolation=cv2.INTER_AREA)
        else:
            img_resized = gray_img
            
        # Match central part to avoid edge noise/partial cards issues
        margin_h, margin_w = h // 6, w // 6
        roi = img_resized[margin_h:-margin_h, margin_w:-margin_w]
        tpl_roi = self._backside_template_gray[margin_h:-margin_h, margin_w:-margin_w]
        
        res = cv2.matchTemplate(roi, tpl_roi, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)
        return float(max_val)

    def is_backside(self, img: np.ndarray) -> bool:
        """
        Robust hybrid check if image is a card backside.
        Combines SIFT feature matching and Template Matching.
        """
        if not self._load_backside_features():
            return False
            
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 1. Try Template Matching (Fast and often reliable for warped cards)
        tpl_score = self._get_template_score(gray)
        if tpl_score > 0.55:
            return True
            
        # 2. Try SIFT (Robust to rotation/scale/partial views)
        # Use equalized image for better feature extraction
        gray_eq = cv2.equalizeHist(gray)
        kp_img, des_img = self._sift.detectAndCompute(gray_eq, None)
        
        if des_img is not None and len(des_img) >= 10:
            bf = cv2.BFMatcher()
            matches = bf.knnMatch(self._des_tpl, des_img, k=2)
            
            good = []
            for m, n in matches:
                if m.distance < 0.7 * n.distance:
                    good.append(m)
            
            # Hybrid thresholding
            if len(good) > 35:
                return True
            if len(good) > 8 and tpl_score > 0.2:
                return True
                
        return False

    def _preprocess(self, img: np.ndarray) -> np.ndarray:
        """
        Enhanced preprocessing for CNN: CLAHE, resizing with INTER_AREA.
        """
        # 1. CLAHE enhancement in LAB space
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        limg = cv2.merge((cl, a, b))
        img_rgb = cv2.cvtColor(limg, cv2.COLOR_LAB2RGB)
        
        # 2. Resize to model input size
        resized = cv2.resize(img_rgb, (self.img_shape, self.img_shape), interpolation=cv2.INTER_AREA)
        
        return resized.astype(np.float32)

    def _run_inference(self, img_array: np.ndarray) -> np.ndarray:
        """Internal helper to get raw probabilities."""
        input_details = self.interpreter.get_input_details()
        output_details = self.interpreter.get_output_details()
        input_tensor = np.expand_dims(img_array, axis=0)
        self.interpreter.set_tensor(input_details[0]["index"], input_tensor)
        self.interpreter.invoke()
        return self.interpreter.get_tensor(output_details[0]["index"])[0]

    def classify_image(self, img: np.ndarray, check_backside: bool = False) -> CardClassification:
        """
        Classifies using an ensemble: Normal and 180-rotation views.
        Pick the most confident of the two.
        
        Args:
            img: BGR image of the card.
            check_backside: If True, first check if it is a backside.
        """
        if check_backside and self.is_backside(img):
            return CardClassification(label="BACK", confidence=1.0)

        # Orientation 1
        p1 = self._run_inference(self._preprocess(img))
        idx1 = np.argmax(p1)
        conf1 = p1[idx1]
        
        # Orientation 2
        p2 = self._run_inference(self._preprocess(cv2.rotate(img, cv2.ROTATE_180)))
        idx2 = np.argmax(p2)
        conf2 = p2[idx2]
        
        if conf1 >= conf2:
            label, confidence = self.class_names[idx1], conf1
        else:
            label, confidence = self.class_names[idx2], conf2
            
        print(f"CNN Best View: {label} ({confidence*100:.1f}%)")
        return CardClassification(label=label, confidence=float(confidence))

    def classify_images(self, img_list: list[np.ndarray], check_backside: bool = False) -> list[CardClassification]:
        return [self.classify_image(img, check_backside=check_backside) for img in img_list]


class TemplateCardClassifier:
    """
    Template-based card classifier using grayscale ROI searching.
    Focuses on the rank/suit corner with a search-based matching.
    """
    def __init__(self, img_size=(250, 350)):
        self.img_size = img_size  # (width, height)
        # Template corner ROI size
        self.tpl_size = (100, 140) 
        # Search area in the card (larger than template)
        self.search_size = (140, 180)
        
        self.templates: dict[str, np.ndarray] = {}
        self._load_templates()

    def _preprocess(self, img: np.ndarray) -> np.ndarray:
        """Grayscale, resize, normalize and blur."""
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img
            
        gray = cv2.resize(gray, self.img_size)
        # Normalize contrast
        gray = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)
        # Slight blur to reduce noise sensitivity
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        return gray

    def _load_templates(self) -> None:
        """Load and preprocess corner templates from the data folder."""
        if not CARDS_FOLDER.exists():
            return

        tw, th = self.tpl_size
        for file_name in os.listdir(CARDS_FOLDER):
            if file_name.endswith(".jpg"):
                label = Path(file_name).stem
                img_path = CARDS_FOLDER / file_name
                img = cv2.imread(str(img_path))
                if img is not None:
                    gray = self._preprocess(img)
                    # Apply Otsu's threshold for distinct shapes
                    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                    if np.mean(thresh) < 127: thresh = cv2.bitwise_not(thresh)
                    # Extract corner template
                    template = thresh[0:th, 0:tw]
                    self.templates[label] = template
        
        print(f"Loaded {len(self.templates)} corner templates.")

    def _match_in_roi(self, roi: np.ndarray, template: np.ndarray) -> float:
        """Find best match for template in ROI using TM_CCOEFF_NORMED."""
        if roi.shape[0] < template.shape[0] or roi.shape[1] < template.shape[1]:
            return 0.0
            
        res = cv2.matchTemplate(roi, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)
        return float(max_val)

    def classify_image(self, img: np.ndarray) -> CardClassification:
        """Classifies image by matching corner against all templates."""
        if not self.templates:
            return CardClassification(label="Unknown", confidence=0.0)

        # Preprocess input image and its 180-rotated version
        gray = self._preprocess(img)
        # Apply Otsu's threshold
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        if np.mean(thresh) < 127: thresh = cv2.bitwise_not(thresh)
        
        thresh_180 = cv2.rotate(thresh, cv2.ROTATE_180)

        sw, sh = self.search_size
        roi_0 = thresh[0:sh, 0:sw]
        roi_180 = thresh_180[0:sh, 0:sw]

        scores = []
        for label, template in self.templates.items():
            s0 = self._match_in_roi(roi_0, template)
            s180 = self._match_in_roi(roi_180, template)
            scores.append((label, max(s0, s180)))

        scores.sort(key=lambda x: x[1], reverse=True)
        best_label, best_score = scores[0]
        
        print(f"Template ROI Top Matches: {scores[:3]}")
        return CardClassification(label=best_label, confidence=float(best_score))

    def classify_images(self, img_list: list[np.ndarray]) -> list[CardClassification]:
        return [self.classify_image(img) for img in img_list]


# Global classifier instance for functional interface
_DEFAULT_CLASSIFIER: Optional[CardClassifier] = None


def _get_default_classifier() -> CardClassifier:
    """Lazy initialization of the default CNN classifier."""
    global _DEFAULT_CLASSIFIER
    if _DEFAULT_CLASSIFIER is None:
        _DEFAULT_CLASSIFIER = CardClassifier()
    return _DEFAULT_CLASSIFIER


def get_card_label(card_img: np.ndarray, check_backside: bool = False) -> CardClassification:
    """
    Identify a card using the CNN-based classifier.
    
    Args:
        card_img: BGR image of a warped/cropped card to classify.
        check_backside: If True, first check if it is a backside.

    Returns:
        CardClassification with the best matching label and confidence score.
    """
    return _get_default_classifier().classify_image(card_img, check_backside=check_backside)


def get_cards_lables(images: list[np.ndarray], check_backside: bool = False) -> list[CardClassification]:
    """
    Classify multiple card images using the CNN-based classifier.

    Args:
        images: List of BGR card images to classify.
        check_backside: If True, first check if it is a backside.

    Returns:
        List of CardClassification objects, one per input image.
    """
    return _get_default_classifier().classify_images(images, check_backside=check_backside)
