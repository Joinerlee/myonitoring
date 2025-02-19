from pathlib import Path
import json
import shutil
import os

class FileManager:
    def __init__(self, base_dir="data"):
        self.base_dir = Path(base_dir)
        self.setup_directories()
        self.temp_files = []
        
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

    def add_temp_file(self, file_path: str):
        self.temp_files.append(file_path)
        
    async def cleanup(self):
        """임시 파일 정리"""
        print("[file_manager] 임시 파일 정리 시작")
        for file_path in self.temp_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"[file_manager] 파일 삭제: {file_path}")
            except Exception as e:
                print(f"[file_manager] 파일 삭제 실패: {file_path} - {str(e)}")
        self.temp_files.clear()