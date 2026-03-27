"""
Card outline detection module.

This module provides functionality for detecting playing card outlines
in images using contour detection and perspective transformation.
"""

from __future__ import annotations

import sys
from typing import Optional

import cv2
import numpy as np
from models import DetectedCard, Point2D

# Detection thresholds
MIN_CARD_AREA: int = 500
QUADRILATERAL_VERTICES: int = 4

# Key codes for interactive mode
KEY_SPACE: int = 32
KEY_ESC: int = 27


class CardOutlineDetector:
    """
    A class for detecting and processing card outlines in an image.
    """

    @staticmethod
    def process_card_image(img: np.ndarray) -> None:
        """
        Process a card image with adaptive thresholding for visualization.

        Applies denoising, grayscale conversion, Gaussian blur, adaptive
        thresholding, and morphological operations, displaying intermediate results.

        Args:
            img: Input BGR image to process.
        """
        # 1. Load the image
        # 2. Convert to Grayscale
        # Adaptive thresholding requires a single channel image.
        dst = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 3. Gaussian Blur
        # We lightly blur the image (5x5 kernel) before thresholding.
        # This removes high-frequency noise so the threshold doesn't
        # pick up paper texture or camera grain as "edges".
        blur = cv2.GaussianBlur(gray, (5, 5), 0)

        # 4. Adaptive Thresholding
        thresh = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)

        # 5. Morphological Opening (Optional but Recommended)
        kernel = np.ones((3, 3), np.uint8)
        clean_thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)

        # Display results
        # We stack them horizontally for easy comparison
        combined_view = np.hstack((gray, thresh, clean_thresh))

        cv2.imshow("Original (Gray) | Adaptive Thresh | Morphological Clean", combined_view)
        cv2.waitKey(0)
        cv2.imshow("Denoised Image", dst)
        cv2.waitKey(0)

    @staticmethod
    def order_points(pts: np.ndarray) -> np.ndarray:
        """
        Orders the points of a quadrilateral in a consistent order:
        top-left, top-right, bottom-right, bottom-left.

        Args:
            pts (np.ndarray): Array of points representing the corners of a quadrilateral.

        Returns:
            np.ndarray: Ordered points in the specified order.
        """
        # Convert to numpy array
        pts = np.array(pts)

        # Find the centroid (center of the quadrilateral)
        center = np.mean(pts, axis=0)

        # Calculate the angle of each point relative to the center
        diff = pts - center
        angles = np.arctan2(diff[:, 1], diff[:, 0])

        # Sort points based on angles
        sort_indices = np.argsort(angles)
        sorted_pts = pts[sort_indices]

        return sorted_pts

    @staticmethod
    def warp_card(image: np.ndarray, corners: np.ndarray, out_w: int = 250, out_h: int = 350) -> np.ndarray:
        """
        Warps a card image to a standard size and orientation.

        Args:
            image (np.ndarray): The input image containing the card.
            corners (np.ndarray): The corners of the card in the image.
            out_w (int): Desired output width of the warped card.
            out_h (int): Desired output height of the warped card.

        Returns:
            np.ndarray: The warped card image.
        """
        # Ensure corners are in float32 format
        corners = np.array(corners, dtype="float32")

        # Order the corners in a consistent order
        rect = CardOutlineDetector.order_points(corners)

        # Ensure the top-left corner is correctly positioned
        if np.linalg.norm(rect[0] - rect[1]) > np.linalg.norm(rect[1] - rect[2]):
            rect = rect[[1, 2, 3, 0]]

        # Compute edge lengths in the source image
        width_top = np.linalg.norm(rect[1] - rect[0])
        width_bottom = np.linalg.norm(rect[2] - rect[3])
        height_left = np.linalg.norm(rect[3] - rect[0])
        height_right = np.linalg.norm(rect[2] - rect[1])

        # Calculate average width and height
        avg_width = (width_top + width_bottom) / 2.0
        avg_height = (height_left + height_right) / 2.0

        # Determine if the card is in portrait orientation or landscape
        portrait = avg_height >= avg_width

        # Define the destination points for the warp
        if portrait:
            dst_w, dst_h = out_w, out_h
            dst = np.array([[0, 0], [dst_w - 1, 0], [dst_w - 1, dst_h - 1], [0, dst_h - 1]], dtype="float32")
        else:
            # Rotate destination mapping by 90° for landscape orientation
            dst_w, dst_h = out_h, out_w
            dst = np.array([[0, dst_h - 1], [0, 0], [dst_w - 1, 0], [dst_w - 1, dst_h - 1]], dtype="float32")

        # Compute the perspective transform matrix
        transform = cv2.getPerspectiveTransform(rect, dst)

        # Apply the perspective warp
        warped = cv2.warpPerspective(image, transform, (dst_w, dst_h))

        # Rotate the warped image to portrait orientation if necessary
        if not portrait:
            warped = cv2.rotate(warped, cv2.ROTATE_90_CLOCKWISE)

        return warped

    @staticmethod
    def get_card_outlines(
        img: np.ndarray,
        include_img: bool = False,
    ) -> list[DetectedCard]:
        """
        Detect card outlines in an image.

        Uses edge detection and contour analysis to find quadrilateral
        shapes that likely represent playing cards.

        Args:
            img: Input BGR image to process.
            include_img: If True, include perspective-corrected card images
                        in the output DetectedCard objects.

        Returns:
            List of DetectedCard objects representing found cards.
        """
        original = img.copy()
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Apply Gaussian blur to reduce noise
        blur = cv2.GaussianBlur(gray, (5, 5), 1.2)

        # Perform Canny edge detection
        edges = cv2.Canny(blur, 50, 150)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        closed_edges = cv2.dilate(edges, kernel, iterations=1)

        # Find contours in the edge-detected image
        contours, _ = cv2.findContours(
            closed_edges,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )

        detected_cards: list[DetectedCard] = []

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < MIN_CARD_AREA:
                continue

            # Approximate the contour to a polygon
            perimeter = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.03 * perimeter, True)

            # Keep only 4-vertex polygons (quadrilaterals)
            if len(approx) == QUADRILATERAL_VERTICES:
                moments = cv2.moments(approx)
                ordered_corners = CardOutlineDetector.order_points(approx.reshape(4, 2))

                cx = int(moments["m10"] / moments["m00"])
                cy = int(moments["m01"] / moments["m00"])

                warped_image: Optional[np.ndarray] = None
                if include_img:
                    warped_image = CardOutlineDetector.warp_card(original, ordered_corners)

                card = DetectedCard(
                    center=Point2D(x=cx, y=cy),
                    corners=ordered_corners,
                    warped_image=warped_image,
                )
                detected_cards.append(card)

        return detected_cards

    @staticmethod
    def display_cards_in_image(img: np.ndarray) -> None:
        """
        Detect card outlines in an image, warp them, and display the results.

        This is a debugging/visualization function that shows detected cards
        with their centers, corner indices, and warped images.

        Args:
            img: Input BGR image to process.
        """
        detected_cards = CardOutlineDetector.get_card_outlines(img)
        output = img.copy()
        warped_images: list[np.ndarray] = []

        for card in detected_cards:
            cx, cy = card.center.as_int_tuple()

            # Draw the center point
            cv2.circle(output, (cx, cy), 5, (0, 0, 255), -1)

            # Label the center point
            cv2.putText(
                output,
                f"({cx},{cy})",
                (cx + 10, cy),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                (0, 0, 255),
                1,
            )

            # Show the order of the corner points
            for idx, point in enumerate(card.corners):
                cv2.putText(
                    output,
                    f"{idx}",
                    (int(point[0]), int(point[1])),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 0, 0),
                    2,
                )

            # Warp the card to a standard size
            warped = CardOutlineDetector.warp_card(img, card.corners)
            warped_images.append(warped)

            # Draw the contour on the output image
            cv2.polylines(output, [card.corners_as_int32()], True, (0, 255, 0), 2)

        # Display the detected quadrilaterals
        cv2.imshow("Quadrilaterals", output)
        cv2.waitKey(0)

        # Display each warped card
        for i, warped in enumerate(warped_images):
            cv2.imshow(f"Card {i}", warped)
            cv2.waitKey(0)

        cv2.destroyAllWindows()


if __name__ == "__main__":
    from card_classification import CardClassifier

    cam = cv2.VideoCapture(0)

    if not cam.isOpened():
        print("Error: Could not open camera.")
        sys.exit(1)

    cv2.namedWindow("Camera Feed")

    print("Press SPACE to take a photo. Press ESC to exit.")
    classifier = CardClassifier()

    while True:
        ret, frame = cam.read()

        if not ret:
            print("Error: Failed to capture image.")
            break

        cv2.imshow("Camera Feed", frame)

        key = cv2.waitKey(1)

        # SPACE pressed - capture and classify cards
        if key == KEY_SPACE:
            detected_cards = CardOutlineDetector.get_card_outlines(frame, include_img=True)
            for card in detected_cards:
                if card.warped_image is not None:
                    result = classifier.classify_image(card.warped_image)
                    cv2.imshow(f"{result.label} with confidence of {result.confidence:.2f}", card.warped_image)
                    cv2.waitKey(0)
                    print(f"Detected card: {result.label} at ({card.center.x}, {card.center.y})")

        # ESC pressed - exit
        elif key == KEY_ESC:
            print("Closing camera...")
            break

    cam.release()
    cv2.destroyAllWindows()
