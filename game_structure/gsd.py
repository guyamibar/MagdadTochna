"""
Game State Detector (GSD) module.

This module provides the main processing pipeline for detecting and classifying
playing cards on a table using computer vision. It uses AprilTags for spatial
reference and perspective correction.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import cv2
import numpy as np

if TYPE_CHECKING:
    from apriltag import AprilTag
    from card import Card

from card_classification import CardClassifier
from detecting_functions import read_apriltags, read_cards
from models import CardDetectionResult, Point2D, Point3D

# Camera intrinsic matrix (3x3) from calibration
K: list[list[float]] = [
    [1.39561099e03, 0.00000000e00, 8.85690305e02],
    [0.00000000e00, 1.38830766e03, 5.04754597e02],
    [0.00000000e00, 0.00000000e00, 1.00000000e00],
]

# Distortion coefficients [k1, k2, p1, p2, k3] from calibration
D: list[float] = [-0.07011441, 0.24724181, 0.00124205, -0.00364551, -0.27059026]

# Extract camera intrinsic parameters
fx: float = K[0][0]  # Focal length x
fy: float = K[1][1]  # Focal length y
cx: float = K[0][2]  # Principal point x
cy: float = K[1][2]  # Principal point y

# Camera parameters tuple for AprilTag detection [fx, fy, cx, cy]
camera_params: list[float] = [fx, fy, cx, cy]

# Output dimensions for warped table view (in pixels)
TABLE_WIDTH: int = 1000
TABLE_HEIGHT: int = 1800


class Gsd:
    """
    Game State Detector - Main processing pipeline for card detection.

    This class orchestrates the detection pipeline:
    1. Detects AprilTags to establish table boundaries
    2. Warps the camera view to a top-down perspective
    3. Detects and classifies playing cards in the warped image

    Attributes:
        fx: Focal length in x direction (pixels).
        fy: Focal length in y direction (pixels).
        cx: Principal point x coordinate (pixels).
        cy: Principal point y coordinate (pixels).
        cards: List of detected open Card objects.
        closed_cards: List of detected face-down Card objects.
        tags: List of detected AprilTag objects.
    """

    def __init__(self, camera_params: list[float]) -> None:
        """
        Initialize the Game State Detector.

        Args:
            camera_params: Camera intrinsic parameters [fx, fy, cx, cy].
        """
        self.fx, self.fy, self.cx, self.cy = camera_params
        self.camera_params = camera_params

        self.cards: list[Card] = []
        self.closed_cards: list[Card] = []
        self.tags: list[AprilTag] = []
        self.clsf = CardClassifier()

    def process(self, frames: list[np.ndarray]) -> CardDetectionResult:
        """
        Process camera frames to detect and classify cards.

        Takes one or more frames, detects AprilTags to establish the table
        coordinate system, warps to a top-down view, and detects/classifies
        all visible cards.

        Args:
            frames: List of BGR images from camera. At least one frame required.

        Returns:
            CardDetectionResult containing annotated image and detected cards.
        """
        first_frame = frames[0]

        for frame in frames:
            result = read_apriltags(frame, self.camera_params)
            cv2.waitKey(0)
            self.tags = result.tags

            warped_frame = self.warp_table_exact(first_frame)
            return read_cards(warped_frame, self.clsf)

        # Fallback if frames list is empty (should not happen)
        return CardDetectionResult(annotated_image=first_frame)

    @staticmethod
    def order_points(pts: np.ndarray) -> np.ndarray:
        """
        Order four points in consistent clockwise order starting from top-left.

        Uses sum and difference heuristics to determine corner positions:
        - Top-left: smallest sum (x + y)
        - Bottom-right: largest sum (x + y)
        - Top-right: smallest difference (y - x)
        - Bottom-left: largest difference (y - x)

        Args:
            pts: Array of shape (4, 2) containing four 2D points.

        Returns:
            Array of shape (4, 2) with points ordered as:
            [top-left, top-right, bottom-right, bottom-left].
        """
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]  # Top-Left
        rect[2] = pts[np.argmax(s)]  # Bottom-Right
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]  # Top-Right
        rect[3] = pts[np.argmax(diff)]  # Bottom-Left
        return rect

    @staticmethod
    def get_table_homography(frame: np.ndarray) -> np.ndarray:
        """
        Compute the perspective transform matrix from camera view to table view.

        Detects AprilTags in the frame and computes a homography matrix that
        maps the tag positions to the corners of the output table image.

        Args:
            frame: BGR image containing visible AprilTags.

        Returns:
            3x3 perspective transformation matrix.

        Note:
            Excludes AprilTag with ID 1 (reserved for other purposes).
        """
        result = read_apriltags(frame, camera_params)

        filtered_tags = [tag for tag in result.tags if tag.id != 1]

        if len(filtered_tags) == 1:
            tag = filtered_tags[0]
            # Use the tag's corners instead of its center
            src_pts = Gsd.order_points(np.array(tag.corners, dtype="float32"))

            # User requirement:
            # - Tag in bottom left
            # - Image width is 5x tag dimension (S)
            # - Image height is 9x tag dimension (S)
            # - Tag is a square in transformed image

            # Since TABLE_WIDTH = 1000 and TABLE_HEIGHT = 1800:
            # S = TABLE_WIDTH / 5 = 200
            # S = TABLE_HEIGHT / 9 = 200
            # Tag dimension S = 200 pixels.

            s = 200.0
            # Destination points for the tag in bottom-left corner:
            # TL, TR, BR, BL order from order_points
            dst_pts_tag = np.array(
                [
                    [0, TABLE_HEIGHT - 1 - s],  # TL
                    [s, TABLE_HEIGHT - 1 - s],  # TR
                    [s, TABLE_HEIGHT - 1],      # BR
                    [0, TABLE_HEIGHT - 1],      # BL
                ],
                dtype="float32",
            )
            return cv2.getPerspectiveTransform(src_pts, dst_pts_tag)
        else:
            # Fall back to using the centers of all detected tags
            centers = np.array([tag.pixels.as_tuple() for tag in filtered_tags], dtype="float32")
            src_pts = Gsd.order_points(centers)

            dst_pts = np.array(
            [
                [0, 0],  # Top-Left
                [TABLE_WIDTH - 1, 0],  # Top-Right
                [TABLE_WIDTH - 1, TABLE_HEIGHT - 1],  # Bottom-Right
                [0, TABLE_HEIGHT - 1],  # Bottom-Left
            ],
            dtype="float32",
        )

        return cv2.getPerspectiveTransform(src_pts, dst_pts)

    def warp_table_exact(self, image: np.ndarray) -> np.ndarray:
        """
        Warp the camera image to a top-down view of the table.

        Uses AprilTags detected in the image to compute a perspective transform
        that maps the table region to a rectangular output image.

        Args:
            image: Source BGR image from camera.

        Returns:
            Warped image of size (TABLE_WIDTH, TABLE_HEIGHT) showing
            the table from a top-down perspective.
        """
        homography = Gsd.get_table_homography(image)
        return cv2.warpPerspective(image, homography, (TABLE_WIDTH, TABLE_HEIGHT))

    def increase_contrast(self, img: np.ndarray) -> np.ndarray:
        """
        Enhance image contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization).

        Converts to LAB color space and applies CLAHE to the lightness channel,
        preserving color information while improving contrast.

        Args:
            img: Input BGR image.

        Returns:
            Contrast-enhanced BGR image.
        """
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)

        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced_l = clahe.apply(l_channel)

        merged = cv2.merge((enhanced_l, a_channel, b_channel))
        return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)

    def increase_contrast_simple(self, img: np.ndarray) -> np.ndarray:
        """
        Apply simple linear contrast adjustment.

        Args:
            img: Input BGR image.

        Returns:
            Contrast-adjusted BGR image with alpha=0.3, beta=120.
        """
        return cv2.convertScaleAbs(img, alpha=0.3, beta=120)

    def worth_adding(self, location: Point2D, threshold: float = 10) -> bool:
        """
        Check if a card location is far enough from existing closed cards.

        Used to avoid duplicate detections of the same card.

        Args:
            location: Pixel coordinates of the candidate card.
            threshold: Minimum distance in pixels to consider as separate card.

        Returns:
            True if the location is far enough from all existing closed cards.
        """
        return all(
            not Gsd.pixels_are_close(
                Point2D(card.pixels[0], card.pixels[1]),
                location,
                threshold,
            )
            for card in self.closed_cards
        )

    @staticmethod
    def pixels_are_close(loc1: Point2D, loc2: Point2D, threshold: float = 10) -> bool:
        """
        Check if two pixel locations are within a threshold distance.

        Args:
            loc1: First point.
            loc2: Second point.
            threshold: Maximum distance to be considered "close".

        Returns:
            True if the Euclidean distance between points is less than threshold.
        """
        dx = loc1.x - loc2.x
        dy = loc1.y - loc2.y
        distance = math.sqrt(dx * dx + dy * dy)
        return distance < threshold


if __name__ == "__main__":
    gsd = Gsd(camera_params)
    im = cv2.imread("data/test tables/img1.png")
    result = gsd.process([im])
    if result.open_cards:
        card = result.open_cards[0]
        print(f"First card: {card.label} at ({card.cx}, {card.cy})")
    cv2.imshow("Result", result.annotated_image)
    cv2.waitKey(0)

