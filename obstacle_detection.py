import cv2
import numpy as np
import logging
import threading
from collections import deque
from state import state

logger = logging.getLogger(__name__)

class ObstacleDetector:
    """
    Vision-based obstacle detection and navigation assistance system.
    
    Features:
    - Vertical edge detection for obstacle identification.
    - Dynamic safety thresholds for different movement modes.
    - "Precision Mode" for aligning with narrow gaps/doors.
    - Continuous safety history to prevent flickering/hysteresis.
    """
    
    def __init__(self, width=640, height=480):
        self.width = width
        self.height = height
        
        # Detection Thresholds
        # Y-coordinate thresholds (0=top, 480=bottom)
        self.obstacle_threshold_y = 420  # Stop when obstacle is very close
        self.center_x_threshold = 310
        self.min_edge_pixels = 200      # Minimum edge pixels to consider valid visual input
        
        # Hysteresis / Safety History
        self.history_len = 12  # Approx 0.5-1.0s buffer
        self.block_history = deque(maxlen=self.history_len)
        self.lock = threading.Lock()
        
        # Public State
        self.latest_blockage = {
            'forward': False,
            'left': False,
            'right': False
        }
        
        # EMA Smoothing for Precision Mode
        self.last_gap_center = None
        
    def process(self, frame):
        """
        Process a video frame to detect obstacles and determine safe navigation actions.
        
        Args:
            frame (np.ndarray): Input video frame (BGR).
            
        Returns:
            tuple: (
                safe_actions (list): List of allowed actions ['FORWARD', 'LEFT', 'RIGHT', 'BACKWARD'],
                overlay (np.ndarray): Visualization frame,
                metrics (dict): Internal detection metrics
            )
        """
        if frame is None:
            return ["STOP"], None, {}

        # 1. Image Preprocessing & Edge Detection
        edges, total_edge_pixels = self._detect_edges(frame)
        h, w = edges.shape
        
        # 2. Column Scanning
        edge_points = self._scan_columns(edges, w, h)
        
        # Visualization Setup
        overlay = frame.copy()
        shapes = frame.copy()
        self._draw_scan_points(overlay, edge_points)

        # 3. Analyze Obstacle Distances
        # Divide view into chunks: Left, Center, Right
        # Center is narrower to focus on immediate path.
        center_width = len(edge_points) // 6
        side_width = (len(edge_points) - center_width) // 2
        
        c_left = self._get_chunk_average(edge_points[:side_width])
        c_fwd = self._get_chunk_average(edge_points[side_width : side_width + center_width])
        c_right = self._get_chunk_average(edge_points[side_width + center_width:])

        # 4. Check Safety Constraints
        is_blind = total_edge_pixels < self.min_edge_pixels
        instant_blocked = self._determine_blocked_directions(c_left, c_fwd, c_right, is_blind)
        
        # Update Safety History & Public State
        safe_actions = self._update_safety_state(instant_blocked, is_blind, shapes, overlay, w, h)

        # 5. AI-First Visualization (No Guidance Calculation)
        # In precision mode, we just provide *richer* visual overlays.
        # The AI decides where to go based on what it sees.
        if state.precision_mode:
            self._draw_ai_first_overlays(edge_points, c_fwd, w, h, overlay, shapes)

        # Blend Visualization
        alpha = 0.4
        cv2.addWeighted(shapes, alpha, overlay, 1 - alpha, 0, overlay)

        return safe_actions, overlay, {
            'c_left': c_left, 
            'c_fwd': c_fwd, 
            'c_right': c_right, 
            'edges': total_edge_pixels
        }

    def _detect_edges(self, frame):
        """Apply filters and Canny edge detection."""
        filtered = cv2.bilateralFilter(frame, 9, 75, 75)
        edges = cv2.Canny(filtered, 50, 150)
        total_pixels = np.count_nonzero(edges)
        return edges, total_pixels

    def _scan_columns(self, edges, w, h, step=5):
        """Scan columns to find the lowest (closest) edge pixel."""
        edge_points = []
        for x in range(0, w, step):
            detected_y = 0
            # Scan bottom-up
            for y in range(h - 1, -1, -1):
                if edges[y, x] == 255:
                    detected_y = y
                    break
            edge_points.append((x, detected_y))
        return edge_points

    def _draw_scan_points(self, overlay, edge_points):
        """Draw detected obstacles on the overlay."""
        for x, y in edge_points:
            if y > 0:
                cv2.circle(overlay, (x, y), 2, (0, 0, 255), -1)

    def _get_chunk_average(self, chunk, top_n=2):
        """
        Calculate average Y-position of the closest points in a chunk.
        Robust against single-pixel noise.
        """
        if not chunk:
            return 0
        ys = sorted([p[1] for p in chunk], reverse=True)  # Descending (Closest first)
        top_values = ys[:top_n]
        if not top_values:
            return 0
        return sum(top_values) / len(top_values)

    def _determine_blocked_directions(self, c_left, c_fwd, c_right, is_blind):
        """Determine which directions are unsafe. NO precision mode exceptions."""
        blocked = set()
        
        threshold = self.obstacle_threshold_y
        side_threshold = threshold + 50
        
        if is_blind:
            blocked.add("FORWARD")
        else:
            if c_fwd > threshold:
                blocked.add("FORWARD")
            if c_left > side_threshold:
                blocked.add("LEFT")
            if c_right > side_threshold:
                blocked.add("RIGHT")
                
        return blocked

    def _update_safety_state(self, instant_blocked, is_blind, shapes, overlay, w, h):
        """
        Update shared history buffer and determine final safe actions.
        Draws safety indicators on the overlay.
        """
        with self.lock:
            self.block_history.append(instant_blocked)
            
            # Combine history to filter noise
            persistent_blocked = set()
            for b_set in self.block_history:
                persistent_blocked.update(b_set)
            
            # Update public state
            self.latest_blockage = {
                'forward': "FORWARD" in persistent_blocked,
                'left': "LEFT" in persistent_blocked,
                'right': "RIGHT" in persistent_blocked
            }
            
        safe_actions = ["BACKWARD"] # Backward is mostly always safe (blind)
        
        # Visualize Blockages
        cx = w // 2
        cy = h // 2
        
        if is_blind:
            cv2.rectangle(shapes, (int(w*0.2), int(h*0.2)), (int(w*0.8), int(h*0.8)), (0, 0, 255), -1)
            cv2.putText(overlay, "BLOCKED (NO VISUALS)", (int(w*0.3), cy), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        else:
            if "FORWARD" in persistent_blocked:
                cv2.rectangle(shapes, (int(w*0.33), cy), (int(w*0.66), h), (0, 0, 255), -1)
            else:
                safe_actions.append("FORWARD")
                # Draw Safe Zone
                pts = np.array([[int(w*0.3), h], [int(w*0.7), h], [int(w*0.6), int(h*0.4)], [int(w*0.4), int(h*0.4)]], np.int32)
                cv2.fillPoly(shapes, [pts], (0, 255, 0))
                cv2.putText(overlay, "FWD OK", (int(w*0.45), int(h*0.8)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)

            if "LEFT" in persistent_blocked:
                cv2.rectangle(shapes, (0, cy), (int(w*0.33), h), (0, 0, 255), -1)
            else:
                safe_actions.append("LEFT")
                
            if "RIGHT" in persistent_blocked:
                cv2.rectangle(shapes, (int(w*0.66), cy), (w, h), (0, 0, 255), -1)
            else:
                safe_actions.append("RIGHT")
                
        return safe_actions

    def _draw_ai_first_overlays(self, edge_points, c_fwd, w, h, overlay, shapes):
        """
        AI-First Mode: Provide rich visual overlays for the AI to interpret.
        NO algorithmic path guidance - the AI decides where to go.
        """
        # 1. Red Danger Zones around obstacles
        for x, y in edge_points:
            if y > 200:
                radius = int(10 + (y - 200) * 0.15)
                color = (0, 0, 255)
                cv2.circle(shapes, (x, y), radius, color, -1)
        
        # 2. Heading Indicator (Cyan line showing "straight ahead")
        center_x = w // 2
        cv2.line(overlay, (center_x, h), (center_x, int(h * 0.3)), (255, 255, 0), 2)
        cv2.putText(overlay, "HEADING", (center_x - 30, int(h * 0.28)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
        
        # 3. Proximity Bar (Top bar showing how close the forward obstacle is)
        bar_height = 20
        bar_width = int((c_fwd / 480) * w)
        bar_color = (0, 255, 0) if c_fwd < 300 else (0, 255, 255) if c_fwd < 400 else (0, 0, 255)
        cv2.rectangle(overlay, (0, 0), (bar_width, bar_height), bar_color, -1)
        cv2.putText(overlay, f"PROX: {int(c_fwd)}", (10, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
