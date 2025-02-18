import json
from pathlib import Path
from datetime import datetime

class ErrorHandler:
    def __init__(self, error_dir="data/error_logs"):
        self.error_dir = Path(error_dir)
        self.error_dir.mkdir(parents=True, exist_ok=True)
        
    def log_error(self, error_type: str, error_message: str):
        timestamp = datetime.now().isoformat()
        error_data = {
            "type": error_type,
            "message": error_message,
            "timestamp": timestamp
        }
        
        error_file = self.error_dir / f"error_{timestamp}.json"
        with open(error_file, 'w') as f:
            json.dump(error_data, f, indent=2)