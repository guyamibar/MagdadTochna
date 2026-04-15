"""
Card outline detection module.

This module provides functionality for detecting playing card outlines
in images using contour detection and perspective transformation.
"""

from __future__ import annotations

import sys
from typing import Optional, List, Tuple
import cv2
import numpy as np
from game_structure.models import DetectedCard, Point2D

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
    def get_line_intersection(line1: Tuple[int, int, int, int], line2: Tuple[int, int, int, int]) -> Optional[
        Tuple[int, int]]:
        """Calculates the exact (x, y) intersection of two lines using determinants."""
        x1, y1, x2, y2 = line1
        x3, y3, x4, y4 = line2

        den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if den == 0:
            return None

        num_t = (x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)
        px = x1 + num_t * (x2 - x1) / den
        py = y1 + num_t * (y2 - y1) / den

        return (int(px), int(py))

    @staticmethod
    def calculate_angle(line: Tuple[int, int, int, int]) -> float:
        """Calculates the angle of a line in degrees."""
        x1, y1, x2, y2 = line
        return np.degrees(np.arctan2(y2 - y1, x2 - x1)) % 180

    @staticmethod
    def calculate_line_length(line: Tuple[int, int, int, int]) -> float:
        """Calculates the physical length of a line segment."""
        return np.hypot(line[2] - line[0], line[3] - line[1])

    @staticmethod
    def are_lines_collinear(line1: Tuple[int, int, int, int], line2: Tuple[int, int, int, int], angle_tol=15,
                            dist_tol=30) -> bool:
        """
        Checks if line2 is just a fragmented continuation of line1.
        Requires them to have roughly the same angle AND be physically overlapping.
        """
        # 1. Angle Check
        theta1 = CardOutlineDetector.calculate_angle(line1)
        theta2 = CardOutlineDetector.calculate_angle(line2)
        angle_diff = min(abs(theta1 - theta2), 180 - abs(theta1 - theta2))

        if angle_diff > angle_tol:
            return False  # Angles are different, must be adjacent sides

        # 2. Distance Check (Perpendicular distance from line2's center to line1)
        x1, y1, x2, y2 = line1
        x3, y3, x4, y4 = line2

        # Midpoint of line2
        mid_x, mid_y = (x3 + x4) / 2.0, (y3 + y4) / 2.0

        length1 = CardOutlineDetector.calculate_line_length(line1)
        if length1 == 0:
            return False

        # Mathematical distance from a point to a line
        dist = abs((x2 - x1) * (y1 - mid_y) - (x1 - mid_x) * (y2 - y1)) / length1

        return dist < dist_tol

    @staticmethod
    def merge_lines(line1: Tuple[int, int, int, int], line2: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
        """
        Merges two collinear line segments into one long line by finding
        the two endpoints that are furthest apart.
        """
        pts = [
            (line1[0], line1[1]),
            (line1[2], line1[3]),
            (line2[0], line2[1]),
            (line2[2], line2[3])
        ]

        max_dist = 0.0
        best_pair = (pts[0], pts[1])

        # Check the distance between all possible pairs of endpoints
        for i in range(4):
            for j in range(i + 1, 4):
                d = np.hypot(pts[i][0] - pts[j][0], pts[i][1] - pts[j][1])
                if d > max_dist:
                    max_dist = d
                    best_pair = (pts[i], pts[j])

        return (int(best_pair[0][0]), int(best_pair[0][1]), int(best_pair[1][0]), int(best_pair[1][1]))

    # --- Main Filtering Function ---

    @staticmethod
    def find_corners_via_intersections(
            contour: np.ndarray,
            edge_image: np.ndarray,
            debug_raw: Optional[np.ndarray] = None,
            debug_filtered: Optional[np.ndarray] = None
    ) -> Optional[np.ndarray]:
        """Finds 4 corners by prioritizing the longest, distinct straight lines."""

        # 1. Isolate edges
        mask = np.zeros_like(edge_image)
        cv2.drawContours(mask, [contour], -1, 255, 1)
        isolated_edges = cv2.bitwise_and(edge_image, mask)

        # 2. Find all straight lines
        lines = cv2.HoughLinesP(
            isolated_edges, rho=1, theta=np.pi / 180, threshold=30, minLineLength=40, maxLineGap=10
        )

        if lines is None or len(lines) < 4:
            return None

        # DEBUG: Draw raw lines
        if debug_raw is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                cv2.line(debug_raw, (x1, y1), (x2, y2), (0, 0, 255), 2)

        merged_edges = [line[0] for line in lines]

        # 3. Sort all lines by length (Longest first) - Keep this as is
        merged_edges.sort(key=CardOutlineDetector.calculate_line_length, reverse=True)

        # 4. Iterative Candidate Search for two parallel pairs
        def get_angle_diff(a1, a2):
            diff = abs(a1 - a2)
            return min(diff, 180 - diff)

        representative_lines = []

        # We loop through all merged edges, trying each as the primary 'seed' (line1)
        for i in range(len(merged_edges)):
            line1 = merged_edges[i]
            angle1 = CardOutlineDetector.calculate_angle(line1)

            # --- Step A: Find a parallel partner for line1 ---
            line2 = None
            for j in range(len(merged_edges)):
                if i == j: continue  # Don't compare a line to itself

                potential_l2 = merged_edges[j]
                angle2 = CardOutlineDetector.calculate_angle(potential_l2)

                # Parallel check
                if get_angle_diff(angle1, angle2) < 15:
                    # Distance check (ensure they aren't the same physical edge)
                    if not CardOutlineDetector.are_lines_collinear(line1, potential_l2, dist_tol=30):
                        line2 = potential_l2
                        # Store index j so we can skip it later
                        current_j = j
                        break

            if line2 is None:
                continue  # This seed line has no parallel partner; try the next seed

            # --- Step B: Find a perpendicular pair (Axis B) ---
            line3 = None
            line4 = None

            # Search for the first perpendicular line
            for k in range(len(merged_edges)):
                if k == i or k == current_j: continue

                potential_l3 = merged_edges[k]
                angle3 = CardOutlineDetector.calculate_angle(potential_l3)

                # Perpendicular check (~90 degrees)
                if 70 < get_angle_diff(angle1, angle3) < 110:
                    line3 = potential_l3

                    # Now find a parallel partner for line3
                    for m in range(len(merged_edges)):
                        # Index comparison fixes the NumPy ValueError
                        if m == i or m == current_j or m == k: continue

                        potential_l4 = merged_edges[m]
                        angle4 = CardOutlineDetector.calculate_angle(potential_l4)

                        # Parallel to Axis B check
                        if get_angle_diff(angle3, angle4) < 15:
                            if not CardOutlineDetector.are_lines_collinear(line3, potential_l4, dist_tol=30):
                                line4 = potential_l4
                                break

                    if line4 is not None:
                        break  # Found a complete Axis B!

            # --- Step C: Final Validation ---
            if all(l is not None for l in [line1, line2, line3, line4]):
                representative_lines = [line1, line2, line3, line4]
                break  # Success! We found a valid rectangular set. Stop searching.

        # If we exit the loop and representative_lines is empty, no valid card was found
        if len(representative_lines) < 4:
            return None

        # --- NEW RADIAL SORTING LOGIC ---
        # Find the midpoints of the 4 lines
        midpoints = []
        for line in representative_lines:
            x1, y1, x2, y2 = line
            midpoints.append(((x1 + x2) / 2.0, (y1 + y2) / 2.0))

        # Find the rough center of the card (average of midpoints)
        center_x = sum(p[0] for p in midpoints) / 4.0
        center_y = sum(p[1] for p in midpoints) / 4.0

        # Helper to get the radial angle of a line's midpoint relative to the center
        def get_radial_angle(line: tuple[int, int, int, int]) -> float:
            x1, y1, x2, y2 = line
            mid_x = (x1 + x2) / 2.0
            mid_y = (y1 + y2) / 2.0
            return float(np.arctan2(mid_y - center_y, mid_x - center_x))

        # Sort lines radially around the perimeter.
        # This guarantees they are in adjacent sequence!
        representative_lines.sort(key=get_radial_angle)
        # --------------------------------

        # DEBUG: Draw filtered lines
        if debug_filtered is not None:
            colors = [(0, 255, 0), (255, 0, 0), (0, 255, 255), (255, 0, 255)]
            for i, line in enumerate(representative_lines):
                x1, y1, x2, y2 = line
                cv2.line(debug_filtered, (x1, y1), (x2, y2), colors[i % 4], 3)

        # 5. Intersect adjacent lines to find corners
        corners = []
        if len(representative_lines) == 4:
            for i in range(4):
                line1 = representative_lines[i]
                line2 = representative_lines[(i + 1) % 4]
                pt = CardOutlineDetector.get_line_intersection(line1, line2)
                if pt is not None:
                    corners.append(pt)

        # DEBUG: Draw corners
        if len(corners) == 4 and debug_filtered is not None:
            for pt in corners:
                cv2.circle(debug_filtered, pt, 6, (0, 165, 255), -1)

        if len(corners) == 4:
            return np.array(corners, dtype=np.int32).reshape(4, 2)

        return None
    # --- Main Pipeline ---
    @staticmethod
    def get_card_outlines(
            img: np.ndarray,
            include_img: bool = False,
            debug_mode: bool = True  # Set to False in production
    ) -> list[DetectedCard]:
        """
        Detect card outlines with primary intersection strategy and built-in debug visualization.
        """
        original = img.copy()
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Apply Gaussian blur
        blur = cv2.GaussianBlur(gray, (5, 5), 1.2)

        # Perform Canny edge detection
        edges = cv2.Canny(blur, 100, 200)
        cv2.imshow("Edges", edges)
        # Morphological Closing
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        closed_edges = cv2.dilate(edges, kernel, iterations=1)
        cv2.imshow("Closed Edges", closed_edges)
        cv2.waitKey(0)
        # Find contours
        contours, _ = cv2.findContours(
            closed_edges,
            cv2.RETR_LIST,
            cv2.CHAIN_APPROX_SIMPLE,
        )

        # Setup debug canvases
        debug_contours = original.copy()
        debug_raw = original.copy()
        debug_filtered = original.copy()
        debug_final = original.copy()  # ADDED: Canvas for final detections

        # Draw all raw contours in green
        if debug_mode:
            cv2.drawContours(debug_contours, contours, -1, (0, 255, 0), 2)

        detected_cards: list[DetectedCard] = []

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < MIN_CARD_AREA:
                continue

            # Pass the debug canvases down to the intersection logic
            found_corners = CardOutlineDetector.find_corners_via_intersections(
                contour,
                closed_edges,
                debug_raw=debug_raw if debug_mode else None,
                debug_filtered=debug_filtered if debug_mode else None
            )

            if found_corners is not None:
                ordered_corners = CardOutlineDetector.order_points(found_corners)

                cx = int(np.mean(ordered_corners[:, 0]))
                cy = int(np.mean(ordered_corners[:, 1]))

                warped_image: Optional[np.ndarray] = None
                if include_img:
                    warped_image = CardOutlineDetector.warp_card(original, ordered_corners)

                # ADDED: Draw the final confirmed results on the debug canvas
                if debug_mode:
                    # Draw the bounding polygon (thick green line)
                    cv2.polylines(debug_final, [ordered_corners], isClosed=True, color=(0, 255, 0), thickness=3)
                    # Mark the center point (red dot)
                    cv2.circle(debug_final, (cx, cy), 5, (0, 0, 255), -1)
                    # Label the card number
                    cv2.putText(
                        debug_final,
                        f"Card {len(detected_cards) + 1}",
                        (cx - 30, cy - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (255, 255, 255),
                        2
                    )

                card = DetectedCard(
                    center=Point2D(x=cx, y=cy),
                    corners=ordered_corners,
                    warped_image=warped_image,
                )
                detected_cards.append(card)

        # Display the debug windows
        if debug_mode:
            cv2.imshow("1. Found Contours", debug_contours)
            cv2.imshow("2. Raw Hough Lines (Red)", debug_raw)
            cv2.imshow("3. Filtered Lines & Intersections", debug_filtered)
            cv2.imshow("4. Final Detected Cards", debug_final)  # ADDED: Show the final shapes

            # ADDED: Show warped cards if they were requested
            if include_img:
                for i, card in enumerate(detected_cards):
                    if card.warped_image is not None:
                        cv2.imshow(f"Warped Card {i + 1}", card.warped_image)

            print("Press any key on the image windows to continue...")
            cv2.waitKey(0)
            cv2.destroyAllWindows()

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
            frame = cv2.imread("../main/test2.jpg")
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
