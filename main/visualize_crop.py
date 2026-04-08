import cv2
import os
import sys
import numpy as np

def perspective_warp(img, points, out_w=200, out_h=300):
    pts1 = np.float32(points)
    pts2 = np.float32([[0, 0], [out_w, 0], [out_w, out_h], [0, out_h]])
    matrix = cv2.getPerspectiveTransform(pts1, pts2)
    return cv2.warpPerspective(img, matrix, (out_w, out_h))

def visualize_options(image_path, crop_options, warp_options, output_dir='data/test_outputs'):
    img = cv2.imread(image_path)
    if img is None:
        print(f"Failed to read {image_path}")
        return

    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.basename(image_path).split('.')[0]
    
    panel_width = 300
    panel_height = 400
    
    viz_img = img.copy()
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]
    
    panels = []

    # Process Crops
    for i, (name, region) in enumerate(crop_options.items()):
        y1, y2, x1, x2 = region
        color = colors[i % len(colors)]
        cv2.rectangle(viz_img, (x1, y1), (x2, y2), color, 2)
        cv2.putText(viz_img, name, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        cropped = img[y1:y2, x1:x2]
        resized = cv2.resize(cropped, (panel_width, panel_height))
        cv2.putText(resized, f"CROP: {name}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        panels.append(resized)

    # Process Warps
    for i, (name, points) in enumerate(warp_options.items()):
        color = colors[(i + len(crop_options)) % len(colors)]
        pts = np.array(points, np.int32)
        cv2.polylines(viz_img, [pts], True, color, 2)
        cv2.putText(viz_img, name, (pts[0][0], pts[0][1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        warped = perspective_warp(img, points)
        resized = cv2.resize(warped, (panel_width, panel_height))
        cv2.putText(resized, f"WARP: {name}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        panels.append(resized)

    # Grid logic
    if panels:
        cols = 3
        rows = (len(panels) + cols - 1) // cols
        grid = np.zeros((rows * panel_height, cols * panel_width, 3), dtype=np.uint8)
        for i, p_img in enumerate(panels):
            r = i // cols
            c = i % cols
            grid[r*panel_height:(r+1)*panel_height, c*panel_width:(c+1)*panel_width] = p_img
        
        grid_path = os.path.join(output_dir, f"{base_name}_options_grid.jpg")
        cv2.imwrite(grid_path, grid)
        print(f"Saved comparison grid to {grid_path}")

    viz_path = os.path.join(output_dir, f"{base_name}_markup.jpg")
    cv2.imwrite(viz_path, viz_img)
    print(f"Saved markup visualization to {viz_path}")

if __name__ == "__main__":
    image_dir = os.path.join('..', 'game_structure', 'data', 'hidden camera')
    image_files = [f for f in os.listdir(image_dir) if f.endswith(('.jpg', '.png'))]
    
    if len(sys.argv) > 1:
        sample_image = sys.argv[1]
    elif image_files:
        sample_image = os.path.join(image_dir, image_files[2])
    else:
        print("No sample images found.")
        sys.exit(1)
        
    crops = {
        "top_left": (0, 200, 0, 200),
    }
    
    # Order: Top-Left, Top-Right, Bottom-Right, Bottom-Left
    warps = {
        "perspective_1": [[150, 170], [230, 130], [310, 320], [230, 360]],
        "perspective_wide": [[10, 10], [400, 20], [380, 390], [20, 360]]
    }
    
    visualize_options(sample_image, crops, warps)
