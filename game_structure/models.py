"""
Data models for card detection system.

This module defines dataclasses that represent the core data structures
used throughout the card detection pipeline, replacing complex nested
tuples and lists with named, typed structures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

import numpy as np

if TYPE_CHECKING:
    from apriltag import AprilTag


@dataclass
class Point2D:
    """
    A 2D point in pixel coordinates.

    Attributes:
        x: Horizontal pixel coordinate.
        y: Vertical pixel coordinate.
    """

    x: float
    y: float

    def as_tuple(self) -> tuple[float, float]:
        """Return point as (x, y) tuple."""
        return (self.x, self.y)

    def as_int_tuple(self) -> tuple[int, int]:
        """Return point as (x, y) tuple with integer values."""
        return (int(self.x), int(self.y))


@dataclass
class Point3D:
    """
    A 3D point in world coordinates.

    Attributes:
        x: X coordinate in meters.
        y: Y coordinate in meters.
        z: Z coordinate (depth) in meters.
    """

    x: float
    y: float
    z: float

    def as_tuple(self) -> tuple[float, float, float]:
        """Return point as (x, y, z) tuple."""
        return (self.x, self.y, self.z)

    def as_list(self) -> list[float]:
        """Return point as [x, y, z] list."""
        return [self.x, self.y, self.z]


@dataclass
class BoundingBox:
    """
    A rectangular bounding box in pixel coordinates.

    Attributes:
        x1: Left edge x coordinate.
        y1: Top edge y coordinate.
        x2: Right edge x coordinate.
        y2: Bottom edge y coordinate.
    """

    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def width(self) -> int:
        """Width of the bounding box."""
        return abs(self.x2 - self.x1)

    @property
    def height(self) -> int:
        """Height of the bounding box."""
        return abs(self.y2 - self.y1)

    def as_tuple(self) -> tuple[int, int, int, int]:
        """Return as (x1, y1, x2, y2) tuple."""
        return (self.x1, self.y1, self.x2, self.y2)


@dataclass
class CameraIntrinsics:
    """
    Camera intrinsic parameters.

    These parameters describe the internal geometry of the camera,
    including focal lengths and principal point.

    Attributes:
        fx: Focal length in x direction (pixels).
        fy: Focal length in y direction (pixels).
        cx: Principal point x coordinate (pixels).
        cy: Principal point y coordinate (pixels).
    """

    fx: float
    fy: float
    cx: float
    cy: float

    def as_list(self) -> list[float]:
        """Return as [fx, fy, cx, cy] list for AprilTag detection."""
        return [self.fx, self.fy, self.cx, self.cy]


@dataclass
class TagOrientation:
    """
    Orientation information for an AprilTag.

    Describes the tag's position and upward direction for
    calculating rotation angles.

    Attributes:
        center: Center point of the tag in pixel coordinates.
        mid_top: Midpoint of the top edge in pixel coordinates.
    """

    center: Point2D
    mid_top: Point2D


@dataclass
class CardClassification:
    """
    Classification result for a detected card.

    Attributes:
        label: Card label in format like "10S", "KH", "AC".
               Format is <rank><suit> where:
               - rank: A, 2-10, J, Q, K
               - suit: S (Spades), H (Hearts), C (Clubs), D (Diamonds)
        confidence: Classification confidence score (0.0 to 1.0).
    """

    label: str
    confidence: float

    @property
    def rank(self) -> str:
        """Extract rank from label (e.g., '10' from '10S')."""
        return self.label[:-1]

    @property
    def suit(self) -> str:
        """Extract suit from label (e.g., 'S' from '10S')."""
        return self.label[-1]


@dataclass
class DetectedCard:
    """
    A playing card detected in an image.

    Represents a card found by the detection pipeline, including its
    location, boundary, and optionally its warped image and classification.

    Attributes:
        center: Center point of the card in pixel coordinates.
        corners: Ordered corner points of the card quadrilateral.
                 Shape (4, 2) in order: top-left, top-right, bottom-right, bottom-left.
        warped_image: Perspective-corrected card image (250x350 pixels).
                      None if detection was run without image extraction.
        classification: Card classification result, or None if not yet classified.
        is_face_down: True if the card is detected as face-down (backside visible).
    """

    center: Point2D
    corners: np.ndarray
    warped_image: Optional[np.ndarray] = None
    classification: Optional[CardClassification] = None
    is_face_down: bool = False

    @property
    def cx(self) -> float:
        """Shorthand for center x coordinate."""
        return self.center.x

    @property
    def cy(self) -> float:
        """Shorthand for center y coordinate."""
        return self.center.y

    @property
    def label(self) -> Optional[str]:
        """Card label if classified, else None."""
        return self.classification.label if self.classification else None

    @property
    def confidence(self) -> Optional[float]:
        """Classification confidence if classified, else None."""
        return self.classification.confidence if self.classification else None

    def corners_as_int32(self) -> np.ndarray:
        """Return corners as int32 array for OpenCV drawing functions."""
        return self.corners.astype(np.int32)


@dataclass
class CardDetectionResult:
    """
    Result from the card detection pipeline.

    Contains the annotated output image and lists of detected cards
    separated by whether they are face-up or face-down.

    Attributes:
        annotated_image: BGR image with detection visualizations drawn.
        open_cards: List of face-up cards with visible fronts.
        face_down_cards: List of face-down cards (backsides visible).
    """

    annotated_image: np.ndarray
    open_cards: list[DetectedCard] = field(default_factory=list)
    face_down_cards: list[DetectedCard] = field(default_factory=list)

    @property
    def all_cards(self) -> list[DetectedCard]:
        """Return all detected cards (both face-up and face-down)."""
        return self.open_cards + self.face_down_cards

    @property
    def card_count(self) -> int:
        """Total number of detected cards."""
        return len(self.open_cards) + len(self.face_down_cards)

    def format_cards(self) -> str:
        """
        Return a formatted string with each detected card and its corners.
        Each line follows the format: 'Label: [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]'
        """
        lines = []
        for card in self.all_cards:
            label = card.label if card.label else ("BACK" if card.is_face_down else "Unknown")
            lines.append(f"{label}: {card.corners.tolist()}")
        return "\n".join(lines)


@dataclass
class ConfidenceScore:
    """
    Confidence score from a detection method.

    Used for combining scores from multiple detection approaches.

    Attributes:
        value: Confidence value (typically 0.0 to 1.0).
        method: Name of the detection method that produced this score.
    """

    value: float
    method: str = ""

    def __post_init__(self) -> None:
        """Clamp confidence value to valid range."""
        self.value = max(0.0, min(1.0, self.value))


@dataclass
class AprilTagDetectionResult:
    """
    Result from AprilTag detection.

    Contains the annotated output image and list of detected AprilTags
    with their pose information.

    Attributes:
        annotated_image: BGR image with tag visualizations drawn.
        tags: List of detected AprilTag objects with pose information.
    """

    annotated_image: np.ndarray
    tags: list[AprilTag] = field(default_factory=list)

    @property
    def tag_count(self) -> int:
        """Number of detected tags."""
        return len(self.tags)
