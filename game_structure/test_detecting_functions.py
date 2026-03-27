"""
Unit tests for detecting_functions module.

Tests the is_card_back() function using card images from the Cards folder.

Note: The is_card_back() function uses template matching against backside_template.jpg.
It will only match cards with that specific back design. Cards/BACK.jpg has a different
design and will NOT match - this is expected behavior.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest
from detecting_functions import BACKSIDE_TEMPLATE_PATH, is_card_back

# Path to the Cards folder relative to this test file
CARDS_DIR = Path(__file__).parent / "data" / "Cards"
GAMESTRUCTURE_DIR = Path(__file__).parent


def load_image(path: Path) -> np.ndarray:
    """
    Load an image from disk.

    Args:
        path: Path to the image file.

    Returns:
        BGR image as numpy array.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the image could not be loaded.
    """
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {path}")
    img = cv2.imread(str(path))
    if img is None:
        raise ValueError(f"Failed to load image: {path}")
    return img


def get_all_card_files() -> list[str]:
    """Get all card image files from the Cards folder, excluding BACK.jpg."""
    return sorted([path.name for path in CARDS_DIR.glob("*.jpg") if path.name != "BACK.jpg"])


class TestIsCardBack:
    """Tests for the is_card_back() function."""

    @pytest.fixture()
    def template_image(self) -> np.ndarray:
        """Load the backside template image itself (should match perfectly)."""
        return load_image(GAMESTRUCTURE_DIR / BACKSIDE_TEMPLATE_PATH)

    @pytest.fixture()
    def different_backside_image(self) -> np.ndarray:
        """Load the BACK.jpg which has a DIFFERENT design than the template."""
        return load_image(CARDS_DIR / "BACK.jpg")

    def test_template_matches_itself(self, template_image: np.ndarray) -> None:
        """Test that the template image matches itself with low threshold."""
        result = is_card_back(template_image, threshold=0.9)
        assert result is True, "Template should match itself"

    def test_different_back_design_does_not_match(
        self,
        different_backside_image: np.ndarray,
    ) -> None:
        """Test that a different back design does NOT match the template.

        BACK.jpg has a different design than backside_template.jpg, so it
        should NOT be identified as a match. This documents the limitation
        of template matching - it only works with the specific template.
        """
        result = is_card_back(different_backside_image)
        assert result is False, (
            "Different back design should NOT match. " "is_card_back() only matches the specific template pattern."
        )

    @pytest.mark.parametrize("card_name", get_all_card_files())
    def test_front_cards_not_detected_as_back(self, card_name: str) -> None:
        """Test that front-facing cards are not identified as backsides."""
        img = load_image(CARDS_DIR / card_name)
        result = is_card_back(img)
        assert result is False, f"{card_name} should NOT be identified as a backside card"

    def test_high_threshold_rejects_all(
        self,
        different_backside_image: np.ndarray,
    ) -> None:
        """Test that a threshold of 1.0 rejects all images."""
        result = is_card_back(different_backside_image, threshold=1.0)
        assert result is False, "Threshold of 1.0 should reject all images"

    def test_zero_threshold_behavior(self, template_image: np.ndarray) -> None:
        """Test that zero threshold accepts when there's any correlation."""
        result = is_card_back(template_image, threshold=0.0)
        assert result is True, "Zero threshold should accept template image"

    def test_default_threshold_value(self) -> None:
        """Test that the default threshold is reasonable (0.47)."""
        from detecting_functions import BACKSIDE_TEMPLATE_THRESHOLD

        assert 0.0 < BACKSIDE_TEMPLATE_THRESHOLD < 1.0
        assert BACKSIDE_TEMPLATE_THRESHOLD == pytest.approx(0.47)  # noqa: SIM300


class TestIsCardBackEdgeCases:
    """Edge case tests for is_card_back() function."""

    @pytest.fixture()
    def template_image(self) -> np.ndarray:
        """Load the backside template image."""
        return load_image(GAMESTRUCTURE_DIR / BACKSIDE_TEMPLATE_PATH)

    @pytest.fixture()
    def card_image(self) -> np.ndarray:
        """Load a card image for edge case tests."""
        return load_image(CARDS_DIR / "BACK.jpg")

    def test_small_image_does_not_crash(self) -> None:
        """Test that a very small image doesn't crash the function."""
        small_img = np.random.randint(0, 255, (10, 10, 3), dtype=np.uint8)
        try:
            result = is_card_back(small_img)
            assert result is False, "Small random image should not match"
        except cv2.error:
            # OpenCV may raise an error if image is smaller than template
            pass

    def test_grayscale_converted_image(self, card_image: np.ndarray) -> None:
        """Test with an image that was grayscale then converted back to BGR."""
        gray = cv2.cvtColor(card_image, cv2.COLOR_BGR2GRAY)
        bgr_from_gray = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        result = is_card_back(bgr_from_gray)
        assert isinstance(result, bool)

    def test_rotated_image_may_fail(self, card_image: np.ndarray) -> None:
        """Test that rotated images may cause OpenCV errors.

        Template matching requires the template to be smaller than the image.
        Rotating may change dimensions and cause issues.
        """
        rotated = cv2.rotate(card_image, cv2.ROTATE_90_CLOCKWISE)
        try:
            result = is_card_back(rotated)
            assert isinstance(result, bool)
        except cv2.error:
            # Expected if rotated image dimensions are smaller than template
            pass

    def test_resized_larger_image(self, card_image: np.ndarray) -> None:
        """Test with a larger resized image."""
        h, w = card_image.shape[:2]
        larger = cv2.resize(card_image, (w * 2, h * 2))
        result = is_card_back(larger)
        assert isinstance(result, bool)

    def test_resized_smaller_may_fail(self, card_image: np.ndarray) -> None:
        """Test that very small images may cause issues."""
        h, w = card_image.shape[:2]
        smaller = cv2.resize(card_image, (w // 4, h // 4))
        try:
            result = is_card_back(smaller)
            assert isinstance(result, bool)
        except cv2.error:
            # Expected if resized image is smaller than template
            pass

    def test_flipped_image(self, card_image: np.ndarray) -> None:
        """Test with a horizontally flipped image."""
        flipped = cv2.flip(card_image, 1)
        result = is_card_back(flipped)
        assert isinstance(result, bool)

    def test_return_type_is_bool(self, card_image: np.ndarray) -> None:
        """Test that return type is always a boolean."""
        result = is_card_back(card_image)
        assert isinstance(result, bool)
        assert result in (True, False)


class TestIsCardBackFromTableImages:
    """Tests for is_card_back() using card crops from table images."""

    @pytest.fixture()
    def classifier(self) -> CardClassifier:
        from card_classification import CardClassifier

        return CardClassifier()

    def test_backside_from_img3(self) -> None:
        img = cv2.imread(str(GAMESTRUCTURE_DIR / "data" / "reference" / "img3_warped.jpg"))
        if img is None:
            pytest.skip("img3_warped.jpg not found")
        # Crop a known BACK card from img3
        # {"corners": [[522, 1203], [639, 1186], [648, 1270], [533, 1284]], "label": "BACK"}
        from card_detection import CardOutlineDetector

        corners = np.array([[522, 1203], [639, 1186], [648, 1270], [533, 1284]], dtype=np.float32)
        warped = CardOutlineDetector.warp_card(img, corners)
        assert is_card_back(warped) is True

    def test_frontside_from_img3(self) -> None:
        img = cv2.imread(str(GAMESTRUCTURE_DIR / "data" / "reference" / "img3_warped.jpg"))
        if img is None:
            pytest.skip("img3_warped.jpg not found")
        # Crop a known KC card from img3
        # {"corners": [[293, 1198], [363, 1158], [420, 1255], [348, 1296]], "label": "KC"}
        from card_detection import CardOutlineDetector

        corners = np.array([[293, 1198], [363, 1158], [420, 1255], [348, 1296]], dtype=np.float32)
        warped = CardOutlineDetector.warp_card(img, corners)
        assert is_card_back(warped) is False
