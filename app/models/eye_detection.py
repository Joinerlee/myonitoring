# app/models/eye_detection.py

import cv2
import numpy as np
from typing import Dict, List, Optional
import tensorflow as tf

class EyeDetectionModel:
    """고양이 눈 질병 감지 AI 모델"""
    
    def __init__(self, model_path: str = "models/eye_detection/model.tflite"):
        """
        Args:
            model_path (str): TFLite 모델 파일 경로
        """
        try:
            self.interpreter = tf.lite.Interpreter(model_path=model_path)
            self.interpreter.allocate_tensors()
            
            # 입출력 텐서 정보 가져오기
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()
            
            self._is_initialized = True
            
        except Exception as e:
            print(f"AI 모델 초기화 실패: {str(e)}")
            self._is_initialized = False
    
    def process_image(self, image_path: str) -> Optional[Dict]:
        """이미지 처리 및 분석[1]"""
        if not self._is_initialized:
            return None
            
        try:
            # 이미지 전처리
            image = cv2.imread(image_path)
            image = cv2.resize(image, (224, 224))  # 모델 입력 크기에 맞게 조정
            image = image.astype(np.float32) / 255.0
            image = np.expand_dims(image, axis=0)
            
            # 모델 추론
            self.interpreter.set_tensor(self.input_details[0]['index'], image)
            self.interpreter.invoke()
            
            # 결과 추출
            output_data = self.interpreter.get_tensor(self.output_details[0]['index'])
            
            return {
                "disease_probability": float(output_data[0][0]),
                "image_path": image_path
            }
            
        except Exception as e:
            print(f"이미지 처리 실패: {str(e)}")
            return None
    
    def batch_process(self, image_paths: List[str]) -> List[Dict]:
        """여러 이미지 일괄 처리[2]"""
        results = []
        for image_path in image_paths:
            result = self.process_image(image_path)
            if result:
                results.append(result)
        return results
