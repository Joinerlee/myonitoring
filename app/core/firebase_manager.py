# app/core/firebase_manager.py

import firebase_admin
from firebase_admin import credentials, db
import logging
from datetime import datetime
from typing import Dict, Optional

class FirebaseManager:
    """Firebase 실시간 데이터베이스 관리 클래스"""
    
    def __init__(self, 
                 cert_path: str = "config/firebase-cert.json",
                 db_url: str = "https://your-project.firebaseio.com"):
        """
        Args:
            cert_path (str): Firebase 인증 키 파일 경로
            db_url (str): Firebase 데이터베이스 URL
        """
        try:
            cred = credentials.Certificate(cert_path)
            firebase_admin.initialize_app(cred, {
                'databaseURL': db_url
            })
            self._is_initialized = True
            
            # 로거 설정
            self.logger = self._setup_logger()
            
        except Exception as e:
            print(f"Firebase 초기화 실패: {str(e)}")
            self._is_initialized = False
    
    def _setup_logger(self) -> logging.Logger:
        """로깅 시스템 설정[2]"""
        logger = logging.getLogger('firebase')
        logger.setLevel(logging.INFO)
        
        # 파일 핸들러 설정
        handler = logging.FileHandler('logs/firebase.log')
        handler.setLevel(logging.INFO)
        
        # 포맷터 설정
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def save_detection_result(self, data: Dict) -> bool:
        """눈 질병 감지 결과 저장[3]"""
        if not self._is_initialized:
            return False
            
        try:
            ref = db.reference('eye_detections')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            result = ref.child(timestamp).set({
                'disease_probability': data['disease_probability'],
                'image_path': data['image_path'],
                'timestamp': timestamp
            })
            
            self.logger.info(f"감지 결과 저장 성공: {timestamp}")
            return True
            
        except Exception as e:
            self.logger.error(f"감지 결과 저장 실패: {str(e)}")
            return False
