"""
AprilTag fiducial marker representation module.

This module defines the AprilTag class which represents a detected AprilTag
marker with its ID, corner positions, center location, and 3D pose information.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
from game_structure.models import Point2D, Point3D

# Default AprilTag size in meters
DEFAULT_TAG_SIZE: float = 0.08


class AprilTag:
    """
    Represents a detected AprilTag fiducial marker.

    AprilTags are used for spatial reference and camera pose estimation.
    Each tag has a unique ID and provides both pixel coordinates and
    3D position relative to the camera.

    Attributes:
        id: The integer ID of the tag (from the tag family).
        corners: The 4 corner pixel coordinates as list of (x, y) tuples.
        pixels: The pixel center coordinates.
        size: Physical size of the tag in meters.
        location: 3D position in meters from camera.
    """

    def __init__(
        self,
        tag_id: int,
        corners: list[tuple[float, float]],
        center: tuple[float, float],
        pose_t: Optional[np.ndarray] = None,
        size: float = DEFAULT_TAG_SIZE,
    ) -> None:
        """
        Initialize an AprilTag instance.

        Args:
            tag_id: The integer ID of the tag.
            corners: The 4 corner pixel coordinates as list of (x, y).
            center: The (u, v) pixel center coordinates.
            pose_t: Optional translation vector [x, y, z] from camera (meters).
                    If None, location defaults to origin.
            size: Physical size of the tag in meters.
        """
        self.id = tag_id
        self.corners = corners
        self.pixels = Point2D(x=center[0], y=center[1])
        self.size = size

        if pose_t is not None:
            flat = pose_t.flatten()
            self.location = Point3D(x=float(flat[0]), y=float(flat[1]), z=float(flat[2]))
        else:
            self.location = Point3D(x=0.0, y=0.0, z=0.0)

    def __str__(self) -> str:
        """Return human-readable string representation."""
        return f"Tag ID: {self.id} at ({self.location.x:.2f}, {self.location.y:.2f}, {self.location.z:.2f})m"

    def __repr__(self) -> str:
        """Return detailed representation for debugging."""
        return f"AprilTag(ID={self.id}, loc=({self.location.x:.2f}, {self.location.y:.2f}, {self.location.z:.2f}))"
