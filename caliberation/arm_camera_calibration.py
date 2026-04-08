import time
from pathlib import Path

import numpy as np
import cv2
from typing import Tuple, Callable, List
from game_structure.phisical_function import move_player, grab, drop
from game_structure.gsd import Gsd, camera_params
from game_structure.models import Point2D
from main.take_image import HighResCamera


def calibrate_systems() -> Tuple[Callable[[Tuple[float, float]], Tuple[float, float]],
                                Callable[[Tuple[float, float]], Tuple[float, float]],
                                np.ndarray]:
    """
    Performs calibration between the Camera system (warped) and the Arm Base system.
    
    Returns:
        A tuple (camera_to_arm, arm_to_camera, annotated_image).
    """
    # Initialize Game State Detector for image warping and card detection
    gsd = Gsd(camera_params)
    from game_structure.gsd import TABLE_WIDTH, TABLE_HEIGHT
    
    # Initial known position of the card in the arm's coordinate system
    start_pos = (-20.0, 10.0)
    
    # Define a grid of reachable points in the arm's coordinate system for calibration
    arm_grid_points: List[Tuple[float, float]] = [
        (-20.0, 10.0), (-30.0, 10.0), (-20.0, 20.0),
        (10.0, 30.0), (30.0, 30.0), (20.0, 20.0),
        (30.0, 10.0)
    ]
    
    collected_arm_pts = []
    collected_cam_pts = []
    
    current_card_arm_pos = start_pos
    
    print("Starting Arm-Camera Calibration sequence...")
    
    last_frame = None
    for target_arm_pos in arm_grid_points:
        print(f"Targeting Arm Position: {target_arm_pos}")
        
        move_player(current_card_arm_pos)
        grab()
        move_player(target_arm_pos)
        drop()
        move_player((-4, 10))
        frame = HighResCamera().take_image()
        if frame is None:
            current_card_arm_pos = target_arm_pos
            continue
        
        last_frame = frame
        result = gsd.process([frame])
        all_detected = result.open_cards + result.face_down_cards
        real = [card for card in all_detected if card.center.y < 1000]
        all_detected = real
        if not all_detected:
            current_card_arm_pos = target_arm_pos
            continue
            
        detected_card = all_detected[0]
        cam_x, cam_y = detected_card.center.x, detected_card.center.y
        
        collected_arm_pts.append(target_arm_pos)
        collected_cam_pts.append((cam_x, cam_y))
        current_card_arm_pos = target_arm_pos

    if len(collected_arm_pts) < 4:
        raise RuntimeError(f"Calibration failed: Only {len(collected_arm_pts)} points collected.")

    arm_pts_arr = np.array(collected_arm_pts, dtype=np.float32).reshape(-1, 1, 2)
    cam_pts_arr = np.array(collected_cam_pts, dtype=np.float32).reshape(-1, 1, 2)

    H_cam_to_arm, _ = cv2.findHomography(cam_pts_arr, arm_pts_arr)
    H_arm_to_cam, _ = cv2.findHomography(arm_pts_arr, cam_pts_arr)

    # Save calibration matrices for later use
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)
    np.save(data_dir / "H_cam_to_arm.npy", H_cam_to_arm)
    np.save(data_dir / "H_arm_to_cam.npy", H_arm_to_cam)
    print(f"Calibration matrices saved to {data_dir}")

    def camera_to_arm(cam_coord: Tuple[float, float]) -> Tuple[float, float]:
        pt = np.array([cam_coord], dtype=np.float32).reshape(-1, 1, 2)
        transformed = cv2.perspectiveTransform(pt, H_cam_to_arm)
        return (float(transformed[0][0][0]), float(transformed[0][0][1]))

    def arm_to_camera(arm_coord: Tuple[float, float]) -> Tuple[float, float]:
        pt = np.array([arm_coord], dtype=np.float32).reshape(-1, 1, 2)
        transformed = cv2.perspectiveTransform(pt, H_arm_to_cam)
        return (float(transformed[0][0][0]), float(transformed[0][0][1]))

    # --- Generate Annotated Image ---
    if last_frame is None:
        last_frame = np.zeros((TABLE_HEIGHT, TABLE_WIDTH, 3), dtype=np.uint8)
    
    warped_img = gsd.warp_table_exact(last_frame)
    
    # 1. Draw Camera Coordinate Grid (Blue)
    for x in range(0, TABLE_WIDTH, 200):
        cv2.line(warped_img, (x, 0), (x, TABLE_HEIGHT), (255, 0, 0), 1)
    for y in range(0, TABLE_HEIGHT, 200):
        cv2.line(warped_img, (0, y), (TABLE_WIDTH, y), (255, 0, 0), 1)
    
    # 2. Draw Arm Base Coordinate Grid (Green)
    # Assuming arm workspace is roughly 0 to 100 units
    for arm_x in range(0, 101, 20):
        # Draw vertical lines in arm space
        pts = []
        for arm_y in range(0, 101, 5):
            pts.append(arm_to_camera((float(arm_x), float(arm_y))))
        cv2.polylines(warped_img, [np.array(pts, np.int32)], False, (0, 255, 0), 2)
        
    for arm_y in range(0, 101, 20):
        # Draw horizontal lines in arm space
        pts = []
        for arm_x in range(0, 101, 5):
            pts.append(arm_to_camera((float(arm_x), float(arm_y))))
        cv2.polylines(warped_img, [np.array(pts, np.int32)], False, (0, 255, 0), 2)

    cv2.putText(warped_img, "Blue: Camera Grid | Green: Arm Grid", (50, 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    print("Calibration complete.")
    return camera_to_arm, arm_to_camera, warped_img

if __name__ == "__main__":
    cam2arm, arm2cam, vis_img = calibrate_systems()
    cv2.imwrite("data/calibration_grid.jpg", vis_img)
    print("Annotated calibration image saved to data/calibration_grid.jpg")

