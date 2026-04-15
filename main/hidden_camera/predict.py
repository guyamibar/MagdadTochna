import cv2
import numpy as np
from ai_edge_litert.interpreter import Interpreter
from pathlib import Path
import sys

class CardClassifier:
    def __init__(self, rank_model_path, suit_model_path):
        # Load Rank Model
        self.rank_interpreter = Interpreter(model_path=rank_model_path)
        self.rank_interpreter.allocate_tensors()
        self.rank_input_details = self.rank_interpreter.get_input_details()
        self.rank_output_details = self.rank_interpreter.get_output_details()
        
        # Load Suit Model
        self.suit_interpreter = Interpreter(model_path=suit_model_path)
        self.suit_interpreter.allocate_tensors()
        self.suit_input_details = self.suit_interpreter.get_input_details()
        self.suit_output_details = self.suit_interpreter.get_output_details()
        
        # Load Labels
        self.rank_labels = self._load_labels(f"{rank_model_path}.labels.txt")
        self.suit_labels = self._load_labels(f"{suit_model_path}.labels.txt")
        
        # Perspective transform parameters (matching extract_corners.py)
        self.pts_src = np.array([[150, 170], [230, 130], [310, 320], [230, 360]], dtype=np.float32)
        self.width = int((np.linalg.norm(self.pts_src[0] - self.pts_src[1]) + np.linalg.norm(self.pts_src[2] - self.pts_src[3])) / 2)
        self.height = int((np.linalg.norm(self.pts_src[1] - self.pts_src[2]) + np.linalg.norm(self.pts_src[0] - self.pts_src[3])) / 2)
        self.pts_dst = np.array([[0, 0], [self.width, 0], [self.width, self.height], [0, self.height]], dtype=np.float32)
        self.matrix = cv2.getPerspectiveTransform(self.pts_src, self.pts_dst)

    def _load_labels(self, path):
        with open(path, 'r') as f:
            return [line.strip() for line in f.readlines()]

    def preprocess(self, image_path):
        img = cv2.imread(str(image_path))
        if img is None:
            raise ValueError(f"Could not read image: {image_path}")
            
        # Convert BGR to RGB (OpenCV uses BGR by default, TensorFlow models expect RGB)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
        # 1. Perspective Transform
        warped = cv2.warpPerspective(img_rgb, self.matrix, (self.width, self.height))
        
        # 2. Rotate 180 and Mirror
        rotated = cv2.rotate(warped, cv2.ROTATE_180)
        mirrored = cv2.flip(rotated, 1)
        
        # 3. Split (Rank top 110 rows, Suit remaining)
        rank_part = mirrored[0:110, :]
        suit_part = mirrored[110:, :]
        
        # 4. Resize
        rank_input = cv2.resize(rank_part, (128, 128), interpolation=cv2.INTER_AREA)
        suit_input = cv2.resize(suit_part, (128, 128), interpolation=cv2.INTER_AREA)
        
        # 5. Standardization
        rank_input = rank_input.astype(np.float32)
        suit_input = suit_input.astype(np.float32)
        
        # Rank: MobileNetV2 expects [-1, 1] scaling
        rank_input = (rank_input / 127.5) - 1.0
        
        # Suit: Standard zero-mean unit-variance
        suit_input = (suit_input - np.mean(suit_input)) / (np.std(suit_input) + 1e-7)
        
        # Add batch dimension
        rank_input = np.expand_dims(rank_input, axis=0)
        suit_input = np.expand_dims(suit_input, axis=0)
        
        return rank_input, suit_input

    def predict(self, image_path):
        rank_input, suit_input = self.preprocess(image_path)
        
        # Run Rank Inference
        self.rank_interpreter.set_tensor(self.rank_input_details[0]['index'], rank_input)
        self.rank_interpreter.invoke()
        rank_output = self.rank_interpreter.get_tensor(self.rank_output_details[0]['index'])
        rank_idx = np.argmax(rank_output)
        rank_conf = rank_output[0][rank_idx]
        
        # Run Suit Inference
        self.suit_interpreter.set_tensor(self.suit_input_details[0]['index'], suit_input)
        self.suit_interpreter.invoke()
        suit_output = self.suit_interpreter.get_tensor(self.suit_output_details[0]['index'])
        suit_idx = np.argmax(suit_output)
        suit_conf = suit_output[0][suit_idx]
        
        return {
            'rank': self.rank_labels[rank_idx],
            'rank_conf': rank_conf,
            'suit': self.suit_labels[suit_idx],
            'suit_conf': suit_conf
        }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python predict.py <image_path>")
        sys.exit(1)
        
    classifier = CardClassifier("rank_classifier.tflite", "suit_classifier.tflite")
    
    image_path = sys.argv[1]
    try:
        result = classifier.predict(image_path)
        print(f"\nInference Results for {image_path}:")
        print(f"  Rank: {result['rank']} ({result['rank_conf']:.2%})")
        print(f"  Suit: {result['suit']} ({result['suit_conf']:.2%})")
        print(f"  Detected: {result['rank']} of {result['suit']}")
    except Exception as e:
        print(f"Error: {e}")
