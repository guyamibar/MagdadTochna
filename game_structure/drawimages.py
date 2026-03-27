"""
Image annotation drawing module.

This module provides the DrawImages class for drawing annotations on images,
including labels, circles, and bounding boxes for detected cards and AprilTags.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Union

import cv2
import numpy as np

if TYPE_CHECKING:
    from models import BoundingBox

# Drawing parameters
CIRCLE_RADIUS_CARD: int = 6
CIRCLE_RADIUS_TAG: int = 5
FONT: int = cv2.FONT_HERSHEY_SIMPLEX
FONT_SCALE_CARD: float = 0.7
FONT_SCALE_TAG: float = 0.8
LINE_THICKNESS: int = 2
LABEL_OFFSET_X: int = 10
LABEL_OFFSET_Y: int = 20
MIN_BOX_SIZE: int = 40


class DrawImages:
    """
    Helper class for drawing annotations on detection result images.

    Provides methods to draw card markers (circle + label) and AprilTag
    markers (bounding box + center + label) on images.

    Attributes:
        x: Center x coordinate in pixels.
        y: Center y coordinate in pixels.
        label: Text label to draw.
        color: BGR color tuple for drawing.
        box: Optional bounding box for tag visualization.
    """

    def __init__(
        self,
        x: float,
        y: float,
        label: str,
        color: tuple[int, int, int],
        box: Optional[Union[BoundingBox, tuple[int, int, int, int]]] = None,
    ) -> None:
        """
        Initialize a DrawImages instance.

        Args:
            x: Center x coordinate in pixels.
            y: Center y coordinate in pixels.
            label: Text label to display.
            color: BGR color tuple (e.g., (255, 0, 0) for blue).
            box: Optional bounding box (BoundingBox or tuple) for tags.
        """
        self.x = int(x)
        self.y = int(y)
        self.label = str(label)
        self.color = color
        # Store as tuple for internal use
        if box is not None and hasattr(box, "as_tuple"):
            self.box: Optional[tuple[int, int, int, int]] = box.as_tuple()
        else:
            self.box = box

    def smart_label_position(self) -> tuple[int, int]:
        """
        Calculate optimal label position that stays within the bounding box.

        Returns:
            Pixel coordinates (x, y) for the label position.
            Falls back to offset from center if box is too small or not provided.
        """
        if self.box is None:
            return (self.x + LABEL_OFFSET_X, self.y)

        x1, y1, x2, y2 = self.box
        width = abs(x2 - x1)
        height = abs(y2 - y1)

        # If box is too small, fall back to center offset
        if width < MIN_BOX_SIZE or height < MIN_BOX_SIZE:
            return (self.x + LABEL_OFFSET_X, self.y)

        # Position label inside top-left of bounding box
        return (int(x1 + 5), int(y1 + LABEL_OFFSET_Y))

    def draw_card(self, image: np.ndarray) -> None:
        """
        Draw a card marker (circle + label) on the image.

        Args:
            image: BGR image to draw on (modified in place).
        """
        cv2.circle(image, (self.x, self.y), CIRCLE_RADIUS_CARD, self.color, -1)

        text_pos = self.smart_label_position()
        cv2.putText(
            image,
            self.label,
            text_pos,
            FONT,
            FONT_SCALE_CARD,
            self.color,
            LINE_THICKNESS,
        )

    def draw_tag(self, image: np.ndarray) -> None:
        """
        Draw an AprilTag marker (bounding box + center + label) on the image.

        Args:
            image: BGR image to draw on (modified in place).
        """
        if self.box:
            x1, y1, x2, y2 = map(int, self.box)
            cv2.rectangle(image, (x1, y1), (x2, y2), self.color, LINE_THICKNESS)

        cv2.circle(image, (self.x, self.y), CIRCLE_RADIUS_TAG, self.color, -1)

        text_pos = self.smart_label_position()
        cv2.putText(
            image,
            self.label,
            text_pos,
            FONT,
            FONT_SCALE_TAG,
            self.color,
            LINE_THICKNESS,
        )
