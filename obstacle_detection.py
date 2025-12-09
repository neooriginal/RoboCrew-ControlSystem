import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)

class ObstacleDetector:
    def __init__(self, width=640, height=480):
        self.width = width
        self.height = height
        # Thresholds from user request/deduced
        self.obstacle_threshold_y = 250
        self.center_x_threshold = 310
        
    def process(self, frame):
        """
        Process the frame to detect obstacles and determine navigation command.
        Returns:
            safe_actions (list): List of allowed actions ['FORWARD', 'LEFT', 'RIGHT', 'BACKWARD']
            overlay (np.ndarray): Frame with debug drawing
            metrics (dict): Internal metrics
        """
        if frame is None:
            return ["STOP"], None, {}

        # 1. Noise Reduction using Bilateral Filter
        filtered = cv2.bilateralFilter(frame, 9, 75, 75)
        
        # 2. Canny Edge Detection
        edges = cv2.Canny(filtered, 50, 150)
        
        h, w = edges.shape
        edge_points = []
        
        # Visualization setup
        overlay = frame.copy()
        
        # Create a separate layer for semi-transparent shapes
        shapes = frame.copy()
        
        # 3. Column Scan
        for x in range(0, w, 5):
            detected_y = 0 
            found = False
            for y in range(h - 1, -1, -1):
                if edges[y, x] == 255:
                    detected_y = y
                    found = True
                    break
            edge_points.append((x, detected_y))
            if found:
                cv2.circle(overlay, (x, detected_y), 2, (0, 0, 255), -1)

        # 4. Chunking & Metics
        num_points = len(edge_points)
        chunk_size = num_points // 3
        
        left_chunk = edge_points[:chunk_size]
        center_chunk = edge_points[chunk_size:2*chunk_size]
        right_chunk = edge_points[2*chunk_size:]
        
        def get_avg_y(chunk):
            if not chunk: return 0
            return sum(p[1] for p in chunk) / len(chunk)
            
        c_left = get_avg_y(left_chunk)
        c_fwd = get_avg_y(center_chunk)
        c_right = get_avg_y(right_chunk)

        # 5. Safety Logic (The "Prohibit" Logic)
        safe_actions = ["BACKWARD"] # Backward is mostly always safe in this context (blind luck)
        
        threshold = self.obstacle_threshold_y
        
        # Check Center for Forward
        # If Center is blocked -> No Forward
        if c_fwd <= threshold:
            safe_actions.append("FORWARD")
        else:
             # Draw Red Box on Center
             cv2.rectangle(shapes, (int(w*0.33), int(h*0.5)), (int(w*0.66), h), (0, 0, 255), -1)
             
        # Check Sides?
        # Actually, for "Turn Left", we check if the path we turn INTO is clear?
        # Or do we just check if we have space to turn?
        # Usually rotating in place (skid steer) is safe unless tight.
        # But if Left is blocked, turning Left might hit the corner.
        # Let's say: Safe to turn if that side isn't IMMEDIATELY in our face.
        
        side_threshold = threshold + 50 # Allow being slightly closer to sides before disabling turn
        
        if c_left <= side_threshold:
            safe_actions.append("LEFT")
            # Draw Green Arrow/Zone Left
            pts = np.array([[0, h], [0, h//2], [w//3, h//2], [0, h]], np.int32)
            # cv2.fillPoly(shapes, [pts], (0, 255, 0)) # Too much clutter maybe?
        else:
            # Blocked Left
            cv2.rectangle(shapes, (0, int(h*0.5)), (int(w*0.33), h), (0, 0, 255), -1)
            
        if c_right <= side_threshold:
            safe_actions.append("RIGHT")
        else:
            # Blocked Right
            cv2.rectangle(shapes, (int(w*0.66), int(h*0.5)), (w, h), (0, 0, 255), -1)
            
        # Draw "Safe Paths" (Green Zones)
        if "FORWARD" in safe_actions:
             # Draw Green Trapezoid for forward path
             pts = np.array([[int(w*0.3), h], [int(w*0.7), h], [int(w*0.6), int(h*0.4)], [int(w*0.4), int(h*0.4)]], np.int32)
             cv2.fillPoly(shapes, [pts], (0, 255, 0))
             cv2.putText(overlay, "FWD OK", (int(w*0.45), int(h*0.8)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
             
        # Blend overlay
        alpha = 0.4
        cv2.addWeighted(shapes, alpha, overlay, 1 - alpha, 0, overlay)
        
        # Text Info
        status_text = "SAFE: " + " ".join([a[0] for a in safe_actions if a != "BACKWARD"])
        cv2.putText(overlay, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(overlay, f"L:{int(c_left)} C:{int(c_fwd)} R:{int(c_right)}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

        return safe_actions, overlay, {
            'c_left': c_left, 'c_fwd': c_fwd, 'c_right': c_right
        }

