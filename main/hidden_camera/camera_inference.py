import cv2
import numpy as np
import time
from ai_edge_litert.interpreter import Interpreter
from pathlib import Path

class CardClassifier:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(CardClassifier, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, rank_model_path="rank_classifier.tflite", suit_model_path="suit_classifier.tflite"):
        if self._initialized:
            return
        self._initialized = True
        
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
        try:
            with open(path, 'r') as f:
                return [line.strip() for line in f.readlines()]
        except FileNotFoundError:
            print(f"Warning: Label file {path} not found. Using numeric indices.")
            return None

    def preprocess(self, img_bgr):
        # Convert BGR to RGB for warping
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            
        # 1. Perspective Transform
        warped = cv2.warpPerspective(img_rgb, self.matrix, (self.width, self.height))
        
        # 2. Rotate 180 and Mirror
        rotated = cv2.rotate(warped, cv2.ROTATE_180)
        mirrored = cv2.flip(rotated, 1)
        
        # 3. Split (Rank top 110 rows, Suit remaining)
        rank_part = mirrored[0:110, :]
        suit_part = mirrored[110:, :]
        
        # 4. Resize and Grayscale for Rank
        # Convert Rank to Grayscale (consistent with new model architecture)
        rank_gray = cv2.cvtColor(rank_part, cv2.COLOR_RGB2GRAY)
        
        rank_input = cv2.resize(rank_gray, (128, 128), interpolation=cv2.INTER_AREA)
        suit_input = cv2.resize(suit_part, (128, 128), interpolation=cv2.INTER_AREA)
        
        # 5. Standardize (Zero-mean, Unit-variance) and expand dims for batch
        # This makes the model robust to lighting variations
        rank_input = rank_input.astype(np.float32)
        suit_input = suit_input.astype(np.float32)
        
        rank_input = (rank_input - np.mean(rank_input)) / (np.std(rank_input) + 1e-7)
        suit_input = (suit_input - np.mean(suit_input)) / (np.std(suit_input) + 1e-7)
        
        # Add channel dimension for rank (batch, h, w, 1)
        rank_input = np.expand_dims(np.expand_dims(rank_input, axis=-1), axis=0)
        suit_input = np.expand_dims(suit_input, axis=0)
        
        return rank_input, suit_input

    def infere(self, img_bgr):
        rank_input, suit_input = self.preprocess(img_bgr)
        
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
        
        rank_label = self.rank_labels[rank_idx] if self.rank_labels else str(rank_idx)
        suit_label = self.suit_labels[suit_idx] if self.suit_labels else str(suit_idx)
        
        return {
            'rank': rank_label,
            'rank_conf': rank_conf,
            'suit': suit_label,
            'suit_conf': suit_conf
        }

def main():
    # Initialize classifier
    classifier = CardClassifier("rank_classifier.tflite", "suit_classifier.tflite")
    
    # Extraction area points for visualization
    pts_display = classifier.pts_src.astype(np.int32).reshape((-1, 1, 2))
    
    # Open camera
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open camera.")
        return

    last_inference_time = 0
    inference_interval = 3.0 # seconds
    result_text = "Waiting..."

    # Ensure output directory exists
    output_dir = Path("camera_samples")
    output_dir.mkdir(exist_ok=True)

    print(f"Starting camera feed. Press 'q' to exit. Saving images to {output_dir}/")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        current_time = time.time()

        # Run inference every 3 seconds
        if current_time - last_inference_time >= inference_interval:
            try:
                # Get prediction
                result = classifier.infere(frame)

                # Create timestamped filename
                timestamp = int(current_time)
                label_str = f"{result['rank']}_{result['suit']}"

                # Save original frame
                frame_filename = output_dir / f"capture_{timestamp}_{label_str}.jpg"
                cv2.imwrite(str(frame_filename), frame)

                # Re-crop for saving (using BGR for imwrite)
                img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                warped = cv2.warpPerspective(img_rgb, classifier.matrix, (classifier.width, classifier.height))
                rotated = cv2.rotate(warped, cv2.ROTATE_180)
                mirrored = cv2.flip(rotated, 1)
                
                rank_crop = cv2.cvtColor(mirrored[0:110, :], cv2.COLOR_RGB2BGR)
                suit_crop = cv2.cvtColor(mirrored[110:, :], cv2.COLOR_RGB2BGR)

                #cv2.imwrite(str(output_dir / f"capture_{timestamp}_{label_str}_rank.jpg"), rank_crop)
                #cv2.imwrite(str(output_dir / f"capture_{timestamp}_{label_str}_suit.jpg"), suit_crop)

                result_text = f"Saved: {result['rank']} of {result['suit']}"
                print(f"Classification: {result['rank']} of {result['suit']} -> Saved to {frame_filename}")
            except Exception as e:
                result_text = f"Error: {e}"
                print(result_text)
            last_inference_time = current_time
            
        # Draw annotation (extraction area)
        cv2.polylines(frame, [pts_display], isClosed=True, color=(0, 255, 0), thickness=2)
        
        # Draw classification result
        cv2.putText(frame, result_text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(frame, f"Next update in: {max(0, int(inference_interval - (current_time - last_inference_time)) + 1)}s", 
                    (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)

        # Show the frame
        cv2.imshow("Card Classifier - Real-time", frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()