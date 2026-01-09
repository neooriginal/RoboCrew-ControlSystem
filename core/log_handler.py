
import logging
from collections import deque
from datetime import datetime
import threading

class CircularLogHandler(logging.Handler):
    """
    A logging handler that stores a fixed number of recent log records in memory.
    Thread-safe implementation using logging.Handler's lock.
    """
    def __init__(self, capacity=100):
        super().__init__()
        self.capacity = capacity
        # Thread-safe deque with fixed length
        self.records = deque(maxlen=capacity)
        # Initialize the standard Handler lock
        self.createLock()
        
    def emit(self, record):
        try:
            msg = self.format(record)
            
            # Create a structured dict for the frontend
            log_entry = {
                'timestamp': datetime.fromtimestamp(record.created).strftime('%H:%M:%S'),
                'level': record.levelname,
                'message': record.getMessage(), 
                'module': record.module,
                'created': record.created  # Raw timestamp for filtering
            }
            
            # emit() is already protected by self.acquire() in the parent handle() method
            # so we can safely modify self.records
            self.records.append(log_entry)
                
        except Exception:
            self.handleError(record)

    def get_logs(self, since=0):
        """
        Get logs created after the 'since' timestamp.
        """
        # Use the handler's lock to ensure thread safety during read
        self.acquire()
        try:
            # If since is 0, return all
            if since == 0:
                return list(self.records)
            
            # Otherwise filter
            return [r for r in self.records if r['created'] > since]
        finally:
            self.release()
