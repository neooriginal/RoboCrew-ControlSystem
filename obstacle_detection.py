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
            command (str): 'FORWARD', 'LEFT', 'RIGHT', or 'STOP'
            overlay (np.ndarray): Frame with debug drawing
            metadata (dict): Internal metrics
        """
        if frame is None:
            return "STOP", None, {}

        # 1. Noise Reduction using Bilateral Filter
        # User: "reduces the noise... keeps the edges fairly sharp"
        filtered = cv2.bilateralFilter(frame, 9, 75, 75)
        
        # 2. Canny Edge Detection
        # User uses Canny. Thresholds not specified, using standard or previous 50, 150
        edges = cv2.Canny(filtered, 50, 150)
        
        # 3. Scan columns
        # User: "FOR the length of width of the frame with the interval of five pixel"
        # User: "FOR the length of height... if pixel value = 255 then Break"
        # User: "Append this pixel co-ordinates to Edge array"
        # User: "Draw line with point at the bottom edge to respective point in edge array"
        
        edge_points = [] # List of (x, y) where y is the 'limit' of free space (obstacle position)
        
        # Visualization setup
        overlay = frame.copy()
        h, w = edges.shape
        
        for x in range(0, w, 5):
            detected_y = 0 # Default to top (far away)
            
            # Scan from bottom up?
            # User says "Draw line with point at the bottom edge to respective point in edge array"
            # If we scan top-down (0 to H), the first edge we hit is the "highest" point of object?
            # Usually for ground robots, we scan Bottom->Top to find the "feet" of the obstacle.
            # BUT, the user code behavior:
            # "if pixel value = 255 then Break"
            # If we scan from Bottom (H-1) to 0:
            #   Break at obstacle. Y is large (e.g. 400).
            # If no obstacle, we go to 0. Y is 0.
            # This matches "c_forward > 250" (Large Y = Close Obstacle).
            
            found = False
            for y in range(h - 1, -1, -1):
                if edges[y, x] == 255:
                    detected_y = y
                    found = True
                    break
            
            # If not found, detected_y remains 0 (horizon/far)
            edge_points.append((x, detected_y))
            
            # Visualization: Draw line from bottom to edge point
            # "Draw line with point at the bottom edge to respective point in edge array"
            cv2.line(overlay, (x, h-1), (x, detected_y), (0, 255, 0), 1)
            # Draw the point
            if found:
                cv2.circle(overlay, (x, detected_y), 2, (0, 0, 255), -1)

        # 4. Chunking
        # "FOR the length of Edge array with the interval of ‘length of Edge array/3’"
        # "Store Edge array as three chunks"
        
        num_points = len(edge_points)
        chunk_size = num_points // 3
        
        # Left, Center, Right (Assuming scan 0..W goes Left..Right)
        left_chunk = edge_points[:chunk_size]
        center_chunk = edge_points[chunk_size:2*chunk_size]
        right_chunk = edge_points[2*chunk_size:]
        
        # 5. Calculate Averages
        # "Calculate the average of each chunks and store in variable ‘c[left, forward, right]’"
        # Average of Y coordinates
        
        def get_avg_y(chunk):
            if not chunk: return 0
            return sum(p[1] for p in chunk) / len(chunk)
            
        c_left = get_avg_y(left_chunk)
        c_fwd = get_avg_y(center_chunk)
        c_right = get_avg_y(right_chunk)
        
        # Visualization: Draw 3 specific lines from center bottom
        # "Draw three lines to these three points from center of bottom edge of the frame"
        center_bottom = (w // 2, h - 1)
        
        # Visualizing the average points (using center X of each chunk for visualization)
        # Left chunk center X ~ chunk_size/2 * 5
        # Center chunk center X ~ (chunk_size + chunk_size/2) * 5
        # Right chunk center X ~ (2*chunk_size + chunk_size/2) * 5
        
        cv2.line(overlay, center_bottom, (w // 6, int(c_left)), (255, 0, 0), 2)
        cv2.line(overlay, center_bottom, (w // 2, int(c_fwd)), (255, 0, 0), 2)
        cv2.line(overlay, center_bottom, (5 * w // 6, int(c_right)), (255, 0, 0), 2)

        # 6. Warning Logic
        # User request: "only make this in the AI mode... inform the AI if it cant fit... dont steer against the AI just warn it."
        
        threshold = self.obstacle_threshold_y
        blocked_left = c_left > threshold
        blocked_fwd = c_fwd > threshold
        blocked_right = c_right > threshold
        
        warning_msg = ""
        status_color = (0, 255, 0) # Green (Clear)
        
        if blocked_fwd:
            warning_msg = "OBSTACLE AHEAD"
            status_color = (0, 0, 255) # Red
        elif blocked_left and blocked_right:
            warning_msg = "NARROW GAP - MIGHT NOT FIT"
            status_color = (0, 165, 255) # Orange
        elif blocked_left:
            warning_msg = "OBSTACLE LEFT"
            status_color = (0, 255, 255) # Yellow
        elif blocked_right:
            warning_msg = "OBSTACLE RIGHT"
            status_color = (0, 255, 255) # Yellow
            
        # Draw Status
        if warning_msg:
            cv2.putText(overlay, f"{warning_msg}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
        else:
            cv2.putText(overlay, "PATH CLEAR", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            
        cv2.putText(overlay, f"L:{int(c_left)} C:{int(c_fwd)} R:{int(c_right)}", (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # We pass the warning string instead of a command
        return warning_msg, overlay, {
            'c_left': c_left,
            'c_fwd': c_fwd,
            'c_right': c_right,
            'blocked_left': blocked_left,
            'blocked_fwd': blocked_fwd,
            'blocked_right': blocked_right
        }

