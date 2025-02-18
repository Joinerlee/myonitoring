from pathlib import Path
import json
import shutil

class FileManager:
    def __init__(self, base_dir="data"):
        self.base_dir = Path(base_dir)
        self.setup_directories()
        
    def setup_directories(self):
        """필요한 디렉토리 생성"""
        dirs = ["images", "schedule", "error_logs", "reservation"]
        for dir_name in dirs:
            (self.base_dir / dir_name).mkdir(parents=True, exist_ok=True)
            
    def save_schedule(self, schedule_data: dict):
        """스케줄 저장"""
        schedule_file = self.base_dir / "schedule" / "feeding_schedule.json"
        with open(schedule_file, 'w') as f:
            json.dump(schedule_data, f, indent=2)
            
    def cleanup_old_files(self, directory: str, max_age_days: int = 7):
        """오래된 파일 정리"""
        target_dir = self.base_dir / directory
        # 파일 정리 로직