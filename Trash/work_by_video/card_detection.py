import cv2
import numpy as np

class CardOutlineDetector:
    """
    A class for detecting and processing card outlines in an image.
    """

    @staticmethod
    def process_card_image(img):
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
        thresh = cv2.adaptiveThreshold(
            blur,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11,
            2
        )

        # 5. Morphological Opening (Optional but Recommended)
        kernel = np.ones((3, 3), np.uint8)
        clean_thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)

        # Display results
        # We stack them horizontally for easy comparison
        combined_view = np.hstack((gray, thresh, clean_thresh))

        cv2.imshow('Original (Gray) | Adaptive Thresh | Morphological Clean', combined_view)
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
    def warp_card(image, corners: np.ndarray, out_w : int = 250, out_h : int = 350) -> np.ndarray:
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
            dst = np.array([
                [0, 0],
                [dst_w - 1, 0],
                [dst_w - 1, dst_h - 1],
                [0, dst_h - 1]
            ], dtype="float32")
        else:
            # Rotate destination mapping by 90° for landscape orientation
            dst_w, dst_h = out_h, out_w
            dst = np.array([
                [0, dst_h - 1],
                [0, 0],
                [dst_w - 1, 0],
                [dst_w - 1, dst_h - 1]
            ], dtype="float32")

        # Compute the perspective transform matrix
        M = cv2.getPerspectiveTransform(rect, dst)

        # Apply the perspective warp
        warped = cv2.warpPerspective(image, M, (dst_w, dst_h))

        # Rotate the warped image to portrait orientation if necessary
        if not portrait:
            warped = cv2.rotate(warped, cv2.ROTATE_90_CLOCKWISE)

        return warped

    @staticmethod
    def get_card_outlines(img: np.ndarray, include_img : bool = False) -> np.ndarray:
        """
        Detects card outlines in an image and returns a list of courdinates of cards.

        Args:
            img (np.ndarray): The input grayscale image.
            include_img (bool): Whether to include the warped card images in the output.
        """
        cards = []
        org = img.copy()
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Apply Gaussian blur to reduce noise
        blur = cv2.GaussianBlur(img, (5, 5), 1.2)

        # Perform Canny edge detection
        edges = cv2.Canny(blur, 50, 150)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        # Dilation makes edges thicker and connects nearby lines
        closed_edges = cv2.dilate(edges, kernel, iterations=1)
        cv2.imshow("Edges", edges)

        # Find contours in the edge-detected image
        contours, _ = cv2.findContours(
            closed_edges,
            cv2.RETR_EXTERNAL,  # Retrieve only external contours
            cv2.CHAIN_APPROX_SIMPLE  # Compress horizontal, vertical, and diagonal segments
        )

        output = []

        quadrilaterals = []

        for cnt in contours:
            # Ignore very small contours based on area
            area = cv2.contourArea(cnt)
            if area < 500:
                continue

            # Approximate the contour to a polygon
            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.03 * peri, True)

            # Keep only 4-vertex polygons
            if len(approx) == 4:
                quadrilaterals.append(approx)
                M = cv2.moments(approx)
                ordered_pts = CardOutlineDetector.order_points(approx.reshape(4, 2))

                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                if include_img:
                    warped = CardOutlineDetector.warp_card(org, ordered_pts)
                    output.append([[cx, cy], ordered_pts, warped])
                else:
                    output.append([[cx, cy], ordered_pts])

        return output





    @staticmethod
    def display_cards_in_image(img: np.ndarray) -> None:
        """
        Detects card outlines in an image, warps them, and displays the results.

        Args:
            img (np.ndarray): The input grayscale image.
        """
        cards = []

        temp = CardOutlineDetector.get_card_outlines(img)
        output = img.copy()

        for card in temp:
            cx, cy = card[0][0], card[0][1]
            ordered_pts = card[1]
            # Draw the center point
            cv2.circle(output, (cx, cy), 5, (0, 0, 255), -1)

            # Optional: Label the center point
            cv2.putText(
            output,
            f"({cx},{cy})",
            (cx + 10, cy),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (0, 0, 255),
            1
            )

            # Show the order of the points
            for i, point in enumerate(ordered_pts):
                cv2.putText(
                output,
                f"{i}",
                (int(point[0]), int(point[1])),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 0, 0),
                2
                )

            # Warp the card to a standard size
            warped = CardOutlineDetector.warp_card(img, ordered_pts)
            cards.append(warped)

            # Draw the contour on the output image
            cv2.polylines(output, [ordered_pts], True,(0, 255, 0), 2)

        # Display the detected quadrilaterals
        cv2.imshow("Quadrilaterals", output)
        cv2.waitKey(0)

        # Display each warped card
        for i, card in enumerate(cards):
            cv2.imshow(f"Card {i}", card)
            cv2.waitKey(0)
            #CardOutlineDetector.process_card_image(card)

        cv2.destroyAllWindows()


if __name__ == "__main__":
    cam = cv2.VideoCapture(1)

    # Check if camera opened successfully
    if not cam.isOpened():
        print("Error: Could not open camera.")
        exit()

    cv2.namedWindow("Camera Feed")

    print("Press SPACE to take a photo. Press ESC to exit.")

    while True:
        # 2. Read the current frame
        ret, frame = cam.read()

        if not ret:
            print("Error: Failed to capture image.")
            break

        # 3. Display the frame in a window
        cv2.imshow("Camera Feed", frame)

        # 4. Wait for key press
        key = cv2.waitKey(1)

        # If SPACE (ASCII 32) is pressed, save the image
        if key == 32:
            img_name = "opencv_frame.png"
            CardOutlineDetector.display_cards_in_image(frame)

        # If ESC (ASCII 27) is pressed, close the loop
        elif key == 27:
            print("Closing camera...")
            break

    # 5. Release resources
    cam.release()
    cv2.destroyAllWindows()
