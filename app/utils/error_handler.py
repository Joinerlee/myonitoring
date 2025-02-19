import json
from pathlib import Path
from datetime import datetime
import os

class ErrorHandler:
    def __init__(self):
        self.error_log_path = "logs/errors.json"
        Path("logs").mkdir(exist_ok=True)
        
        if not os.path.exists(self.error_log_path):
            with open(self.error_log_path, 'w') as f:
                json.dump({"errors": []}, f)
    
    async def log_error(self, source: str, message: str):
        """에러 로깅"""
        try:
            print(f"[error_handler] 에러 발생: {source} - {message}")
            
            with open(self.error_log_path, 'r') as f:
                error_log = json.load(f)
            
            error_log["errors"].append({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "source": source,
                "message": message
            })
            
            with open(self.error_log_path, 'w') as f:
                json.dump(error_log, f, indent=2)
                
        except Exception as e:
            print(f"[error_handler] 에러 로깅 실패: {str(e)}")