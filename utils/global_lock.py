"""
Simple global lock to prevent VMS/DIR conflicts
"""
import threading
import time

class GlobalLock:
    def __init__(self):
        self.lock = threading.Lock()
        self.current_process = None  # 'vms', 'dir', or None
    
    def acquire(self, process_name, timeout=5):
        """Try to acquire lock for a process"""
        start_time = time.time()
        
        # Try multiple times to get the lock
        while time.time() - start_time < timeout:
            if self.lock.acquire(timeout=1):
                self.current_process = process_name
                print(f"🔒 LOCK ACQUIRED by {process_name.upper()}")
                return True
            time.sleep(0.5)
        
        print(f"❌ Could not acquire lock for {process_name} after {timeout}s")
        return False
    
    def release(self, process_name):
        """Release lock"""
        if self.current_process == process_name:
            self.current_process = None
            self.lock.release()
            print(f"🔓 LOCK RELEASED by {process_name.upper()}")
            return True
        elif self.current_process:
            print(f"⚠️  Lock held by {self.current_process}, not {process_name}")
        return False
    
    def is_processing(self, process_name=None):
        """Check if processing is happening"""
        if process_name:
            return self.current_process == process_name
        return self.current_process is not None
    
    def wait_if_processing(self, process_name, check_interval=3, max_wait=300):
        """Wait if another process is running"""
        if self.current_process and self.current_process != process_name:
            print(f"⏳ {process_name.upper()} waiting for {self.current_process.upper()} to finish...")
            
            # Wait for other process to finish
            wait_start = time.time()
            while time.time() - wait_start < max_wait:
                if not self.current_process or self.current_process == process_name:
                    return True
                time.sleep(check_interval)
            
            print(f"⚠️  {process_name} waited {max_wait}s, proceeding anyway")
            return False
        return True

# Global instance
global_lock = GlobalLock()