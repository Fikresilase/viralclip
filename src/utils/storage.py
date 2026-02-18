
import os
import shutil
import tempfile
import uuid

class StorageManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(StorageManager, cls).__new__(cls)
            cls._instance.temp_dir = os.path.join(tempfile.gettempdir(), "ContentFactory_Cache")
            os.makedirs(cls._instance.temp_dir, exist_ok=True)
        return cls._instance

    def get_new_path(self, filename=None, ext=".mp4"):
        if not filename:
            filename = f"clip_{uuid.uuid4().hex}{ext}"
        return os.path.join(self.temp_dir, filename)

    def cleanup(self):
        """Call this when App closes or on launch to clear old cache"""
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                os.makedirs(self.temp_dir, exist_ok=True) # Recreate empty dir
            print("[StorageManager] Cleanup complete.")
        except Exception as e:
            print(f"[StorageManager] Cleanup failed: {e}")
