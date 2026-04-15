import time
from pathlib import Path

import numpy as np
import cv2
from typing import Tuple, Callable, List
from game_structure.phisical_function import grab, drop
from arduino_control.moveitmoveit import move_to
from game_structure.gsd import Gsd, camera_params
from main.take_image import HighResCamera


def calibrate_from_points(collected_arm_pts: List[Tuple[float, float]], 
                          collected_cam_pts: List[Tuple[float, float]],
                          last_frame: np.ndarray = None) -> Tuple[Callable[[Tuple[float, float]], Tuple[float, float]],
                                                                 Callable[[Tuple[float, float]], Tuple[float, float]],
                                                                 np.ndarray]:
    """
    Performs calibration calculation from a set of matching points.
    
    Returns:
        A tuple (camera_to_arm, arm_to_camera, annotated_image).
    """
    if len(collected_arm_pts) < 4:
        raise RuntimeError(f"Calibration failed: Only {len(collected_arm_pts)} points provided.")

    arm_pts_arr = np.array(collected_arm_pts, dtype=np.float32).reshape(-1, 1, 2)
    cam_pts_arr = np.array(collected_cam_pts, dtype=np.float32).reshape(-1, 1, 2)

    H_cam_to_arm, _ = cv2.findHomography(cam_pts_arr, arm_pts_arr)
    H_arm_to_cam, _ = cv2.findHomography(arm_pts_arr, cam_pts_arr)

    if H_cam_to_arm is None or H_arm_to_cam is None:
        raise RuntimeError("Calibration failed: Could not estimate homography.")

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
    gsd = Gsd(camera_params)
    from game_structure.gsd import TABLE_WIDTH, TABLE_HEIGHT
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
    
    # Initial known position of the card in the arm's coordinate system
    start_pos = (-25.0, 10.0)
    
    # Define a grid of reachable points in the arm's coordinate system for calibration
    arm_grid_points: List[Tuple[float, float]] = [
        (-25, 10), (-10, 10), (-10, 25), (-25, 25),
        (35, 10), (35, 20), (25, 20)
    ]
    
    collected_arm_pts = []
    collected_cam_pts = []
    
    current_card_arm_pos = start_pos
    
    print("Starting Arm-Camera Calibration sequence...")
    
    last_frame = None
    for target_arm_pos in arm_grid_points:
        print(f"Targeting Arm Position: {target_arm_pos}")
        move_to((10, 25))
        move_to(current_card_arm_pos)
        grab()
        move_to(target_arm_pos)
        drop()
        move_to((10, 25))
        move_to((-1, 10))
        frame = HighResCamera().take_image()
        if frame is None:
            current_card_arm_pos = target_arm_pos
            continue
        
        last_frame = frame
        result = gsd.process([frame])
        all_detected = result.open_cards + result.face_down_cards
        real = []
        for card in all_detected:
            if card.center.y < 1000:
                if card.center.y < 130 and (card.center.x < 550 and card.center.x > 250):
                    continue
                real.append(card)

        all_detected = real
        if not all_detected:
            current_card_arm_pos = target_arm_pos
            continue

        data_dir = Path(__file__).parent.parent / "data"
        data_dir.mkdir(exist_ok=True)
        cv2.imwrite(str(data_dir / f"arm_camera_{target_arm_pos}1.jpg"), frame)
        cv2.imwrite(str(data_dir / f"arm_camera_{target_arm_pos}2.jpg"), result.annotated_image)

        detected_card = all_detected[0]
        print(f"Detected Card Position: {detected_card.center}, Card: {detected_card.label}")
        print(f"Chosen out of {len(all_detected)}")
        cam_x, cam_y = detected_card.center.x, detected_card.center.y
        
        collected_arm_pts.append(target_arm_pos)
        collected_cam_pts.append((cam_x, cam_y))
        current_card_arm_pos = target_arm_pos

    return calibrate_from_points(collected_arm_pts, collected_cam_pts, last_frame)

if __name__ == "__main__":
    _, _, vis_img = calibrate_systems()
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)
    cv2.imwrite(data_dir / "calibration_vis.jpg", vis_img)
    print("Annotated calibration image saved to data/calibration_vis.jpg")
    '''
    arm_points = [(-25, 10), (-10, 10), (-10, 25), (-25, 25), (25, 10), (35, 10), (35, 20), (25, 20)]
    camera_points = [(872, 197), (679, 211), (685, 408), (870, 401), (243, 236), (108, 240), (105, 367), (247, 363)]
    frame = HighResCamera().take_image()
    cam2arm, arm2cam, vis_img = calibrate_from_points(arm_points, camera_points, frame)
    
    # Annotate matching points for verification
    for i, (cam_pt, arm_pt) in enumerate(zip(camera_points, arm_points)):
        # Camera point (Red)
        cx, cy = int(cam_pt[0]), int(cam_pt[1])
        cv2.circle(vis_img, (cx, cy), 8, (0, 0, 255), -1)
        cv2.putText(vis_img, f"C{i}", (cx + 10, cy - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # Projected Arm point (Yellow)
        proj_cam = arm2cam(arm_pt)
        px, py = int(proj_cam[0]), int(proj_cam[1])
        cv2.circle(vis_img, (px, py), 5, (0, 255, 255), -1)
        cv2.putText(vis_img, f"A{i}({arm_pt})", (px + 10, py + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
'''


