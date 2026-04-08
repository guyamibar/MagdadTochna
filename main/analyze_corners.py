import cv2
import numpy as np
import os

def analyze_pixel_density(image_path):
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return None
    
    # Invert if the background is white (cards usually are)
    # We want to find the "ink" (rank/suit)
    _, thresh = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Calculate density in a grid to find the "busy" area
    h, w = thresh.shape
    grid_h, grid_w = 10, 10
    step_h, step_w = h // grid_h, w // grid_w
    
    density = np.zeros((grid_h, grid_w))
    for i in range(grid_h):
        for j in range(grid_w):
            roi = thresh[i*step_h:(i+1)*step_h, j*step_w:(j+1)*step_w]
            density[i, j] = np.sum(roi)
            
    return density

if __name__ == "__main__":
    img_dir = os.path.join('game_structure', 'data', 'hidden camera')
    for filename in os.listdir(img_dir):
        if filename.endswith('.jpg'):
            path = os.path.join(img_dir, filename)
            density = analyze_pixel_density(path)
            if density is not None:
                max_pos = np.unravel_index(np.argmax(density), density.shape)
                print(f"File: {filename} -> Highest density at grid cell {max_pos}")
