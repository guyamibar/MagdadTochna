"""
Detection functions for cards and AprilTags.

This module provides utility functions for detecting playing cards and AprilTag
fiducial markers in images. It handles card outline detection, backside detection,
and AprilTag pose estimation.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import TYPE_CHECKING, Callable

import cv2
import numpy as np
from pupil_apriltags import Detector

if TYPE_CHECKING:
    from card_classification import CardClassifier

from apriltag import AprilTag
from card_classification import get_cards_lables
from card_detection import CardOutlineDetector
from drawimages import DrawImages
from models import (
    AprilTagDetectionResult,
    BoundingBox,
    CardDetectionResult,
    ConfidenceScore,
    DetectedCard,
)

# Path to the template image for card backside detection (relative to this module)
_MODULE_DIR: Path = Path(__file__).parent
BACKSIDE_TEMPLATE_PATH: Path = _MODULE_DIR / "data" / "templates" / "backside.jpg"

# AprilTag configuration
APRILTAG_FAMILY: str = "tag36h11"
APRILTAG_SIZE_METERS: float = 0.08
APRILTAG_THREADS: int = 4

# Card backside detection thresholds
BACKSIDE_TEMPLATE_THRESHOLD: float = 0.47
BACKSIDE_MIN_MATCH_COUNT: int = 15
BACKSIDE_MIN_INLIER_RATIO: float = 0.5
BACKSIDE_LOWE_RATIO: float = 0.75

# Minimum distance from image corner to consider a card valid (pixels)
MIN_CORNER_DISTANCE: int = 180


def found_card(scores: list[ConfidenceScore]) -> bool:
    """
    Determine if a card detection is confident enough based on combined scores.

    Uses the sum of squared confidence values from two detection methods.
    A combined score > 1 indicates a reliable detection.

    Args:
        scores: List of ConfidenceScore objects from different detection methods.

    Returns:
        True if combined confidence score exceeds threshold.
    """
    total = sum(score.value**2 for score in scores)
    return total > 1


def read_cards(
    frame: np.ndarray,
    clsf: CardClassifier,
) -> CardDetectionResult:
    """
    Detect and classify playing cards in an image.

    Finds card outlines, filters out cards too close to image corners,
    classifies each card, and draws annotations on the output image.

    Args:
        frame: BGR input image from camera.
        clsf: CardClassifier instance (currently unused, classification done
              via template matching).

    Returns:
        CardDetectionResult containing annotated image and detected cards.
    """
    detected_cards = CardOutlineDetector.get_card_outlines(frame, include_img=True)
    output = frame.copy()

    image_size = (frame.shape[1], frame.shape[0])

    # Filter cards that are too close to corners
    valid_cards = [
        card for card in detected_cards if dist_to_corner(card.center.as_tuple(), image_size) >= MIN_CORNER_DISTANCE
    ]

    # Classify cards using template matching and CNN
    warped_images = [card.warped_image for card in valid_cards if card.warped_image is not None]
    classifications = get_cards_lables(warped_images, check_backside=True)

    # Assign classifications to cards
    open_cards: list[DetectedCard] = []
    for i, card in enumerate(valid_cards):
        card.classification = classifications[i]
        open_cards.append(card)

    face_down_cards: list[DetectedCard] = []

    # Draw annotations for all detected cards
    for card in open_cards + face_down_cards:
        cx, cy = card.center.as_int_tuple()

        cv2.polylines(output, [card.corners_as_int32()], True, (0, 255, 0), 2)
        cv2.circle(output, (cx, cy), 5, (0, 0, 255), -1)
        cv2.putText(
            output,
            f"({cx},{cy})",
            (cx + 10, cy),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (0, 0, 255),
            1,
        )

        # Draw classification label for classified cards
        if card.classification:
            cv2.putText(
                output,
                f"{card.classification.label} {card.classification.confidence:.2f}",
                (cx + 10, cy - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                (0, 0, 255),
                1,
            )

    return CardDetectionResult(
        annotated_image=output,
        open_cards=open_cards,
        face_down_cards=face_down_cards,
    )


def is_card_back(
    img: np.ndarray,
    threshold: float = BACKSIDE_TEMPLATE_THRESHOLD,
) -> bool:
    """
    Quick check if a card image shows the backside using template matching.

    Uses normalized cross-correlation to compare the card image against
    a reference backside template.

    Args:
        img: BGR image of the card to check.
        threshold: Minimum correlation value to consider a match (0-1).

    Returns:
        True if the card appears to be face-down (backside visible).
    """
    template_img = cv2.imread(str(BACKSIDE_TEMPLATE_PATH), cv2.IMREAD_GRAYSCALE)
    gray_card = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    result = cv2.matchTemplate(gray_card, template_img, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(result)

    return max_val >= threshold


def is_card_backside(img_card: np.ndarray) -> bool:
    """
    Robust check if a card image shows the backside using feature matching.

    Performs SIFT feature detection and matching with geometric verification
    to reliably detect card backsides even with rotation and perspective changes.

    The detection pipeline:
    1. Extract SIFT features from both card and template
    2. Match features using brute-force matcher with Lowe's ratio test
    3. Verify geometric consistency using affine transformation
    4. Check that the projected shape is convex (no twists)

    Args:
        img_card: BGR image of the card to check.

    Returns:
        True if the card is face-down (backside pattern detected).
    """
    gray_card = cv2.cvtColor(img_card, cv2.COLOR_BGR2GRAY)
    gray_template = cv2.imread(str(BACKSIDE_TEMPLATE_PATH), cv2.IMREAD_GRAYSCALE)

    if gray_card is None or gray_template is None:
        return False

    # Detect SIFT features
    sift = cv2.SIFT_create(nfeatures=2000)
    kp_template, des_template = sift.detectAndCompute(gray_template, None)
    kp_card, des_card = sift.detectAndCompute(gray_card, None)

    if des_template is None or des_card is None:
        return False

    # Match features using brute-force matcher
    # Note: SIFT uses L2 norm, not Hamming (Hamming is for binary descriptors like ORB)
    bf = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)
    matches = bf.knnMatch(des_template, des_card, k=2)

    # Filter matches using Lowe's ratio test
    good_matches = [m for m, n in matches if m.distance < BACKSIDE_LOWE_RATIO * n.distance]

    if len(good_matches) < BACKSIDE_MIN_MATCH_COUNT:
        return False

    # Geometric verification using affine transformation
    src_pts = np.float32(
        [kp_template[m.queryIdx].pt for m in good_matches],
    ).reshape(-1, 1, 2)
    dst_pts = np.float32(
        [kp_card[m.trainIdx].pt for m in good_matches],
    ).reshape(-1, 1, 2)

    transform_matrix, mask = cv2.estimateAffinePartial2D(src_pts, dst_pts)

    if transform_matrix is None or mask is None:
        return False

    # Count inliers and check consistency
    inliers_count = int(mask.sum())

    if inliers_count < BACKSIDE_MIN_MATCH_COUNT:
        return False

    if (inliers_count / len(good_matches)) < BACKSIDE_MIN_INLIER_RATIO:
        return False

    # Verify projected shape is convex (sanity check)
    h, w = gray_template.shape
    corners = np.float32(
        [
            [0, 0],
            [0, h - 1],
            [w - 1, h - 1],
            [w - 1, 0],
        ]
    ).reshape(-1, 1, 2)

    try:
        # Convert 2x3 affine matrix to 3x3 for perspectiveTransform
        affine_3x3 = np.vstack([transform_matrix, [0, 0, 1]])
        projected = cv2.perspectiveTransform(corners, affine_3x3)
        return bool(cv2.isContourConvex(np.int32(projected)))
    except cv2.error:
        return False


def dist_to_corner(
    point: tuple[float, float],
    image_size: tuple[int, int],
) -> float:
    """
    Calculate the Euclidean distance from a point to the nearest image corner.

    This is used to filter out card detections that are too close to the
    image edges, which are often partial or unreliable detections.

    Args:
        point: The (x, y) pixel coordinates.
        image_size: The (width, height) of the image in pixels.

    Returns:
        Distance in pixels to the closest corner.
    """
    x, y = point
    w, h = image_size

    dist_x = min(abs(x), abs(x - w))
    dist_y = min(abs(y), abs(y - h))

    return math.hypot(dist_x, dist_y)


def read_apriltags(
    frame: np.ndarray,
    camera_params: list[float],
) -> AprilTagDetectionResult:
    """
    Detect AprilTags in an image and estimate their 3D poses.

    Finds all tag36h11 AprilTags in the frame, estimates their pose relative
    to the camera, and draws annotations showing tag IDs and distances.

    Args:
        frame: BGR input image from camera.
        camera_params: Camera intrinsic parameters [fx, fy, cx, cy].

    Returns:
        AprilTagDetectionResult containing annotated image and detected tags.
    """
    detector = Detector(
        families=APRILTAG_FAMILY,
        nthreads=APRILTAG_THREADS,
        quad_decimate=1.0,
        refine_edges=True,
        decode_sharpening=0.25,
    )

    output_img = frame.copy()
    gray = cv2.cvtColor(output_img, cv2.COLOR_BGR2GRAY)

    results = detector.detect(
        gray,
        estimate_tag_pose=True,
        camera_params=camera_params,
        tag_size=APRILTAG_SIZE_METERS,
    )

    detected_tags: list[AprilTag] = []
    drawing_operations: list[Callable[[np.ndarray], None]] = []

    for detection in results:
        tag = AprilTag(
            tag_id=detection.tag_id,
            corners=detection.corners,
            center=detection.center,
            pose_t=detection.pose_t,
            size=APRILTAG_SIZE_METERS,
        )
        detected_tags.append(tag)

        # Calculate bounding box from corners
        xs = [int(p[0]) for p in detection.corners]
        ys = [int(p[1]) for p in detection.corners]
        bbox = BoundingBox(x1=min(xs), y1=min(ys), x2=max(xs), y2=max(ys))

        # Prepare tag label with ID and depth
        label_text = f"ID:{tag.id} Z:{tag.location.z:.2f}m"

        draw_obj = DrawImages(
            x=tag.pixels.x,
            y=tag.pixels.y,
            label=label_text,
            color=(255, 0, 0),
            box=bbox,
        )
        drawing_operations.append(draw_obj.draw_tag)

        # Add corner marker drawings
        for px, py in detection.corners:
            corner_marker = DrawImages(px, py, "", (0, 255, 0))
            drawing_operations.append(corner_marker.draw_card)

    # Execute all drawing operations
    for draw_func in drawing_operations:
        draw_func(output_img)

    return AprilTagDetectionResult(annotated_image=output_img, tags=detected_tags)
