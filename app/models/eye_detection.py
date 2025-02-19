# app/models/eye_detection.py

import cv2
import numpy as np
from typing import Dict, List, Optional, Tuple
import tensorflow as tf
import os
from inference_sdk import InferenceHTTPClient
from datetime import datetime
import json

class EyeDetectionModel:
    """고양이 눈 질병 감지 AI 모델"""
    
    def __init__(self, 
                 disease_model_path: str = "models/eye_detection/model.tflite",
                 api_url: str = os.environ.get('RF_API_URL'),
                 api_key: str = os.environ.get('RF_API_KEY')):
        """
        Args:
            disease_model_path (str): 질병 감지 TFLite 모델 경로
            api_url (str): Roboflow API URL
            api_key (str): Roboflow API Key
        """
        try:
            print("[eye_detection] 모델 초기화 시작...")
            
            # 눈 감지 API 클라이언트 초기화
            self.eye_detector = InferenceHTTPClient(
                api_url=api_url,
                api_key=api_key
            )
            
            # 질병 감지 모델 초기화
            self.interpreter = tf.lite.Interpreter(model_path=disease_model_path)
            self.interpreter.allocate_tensors()
            
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()
            
            self._is_initialized = True
            print("[eye_detection] 초기화 완료")
            
        except Exception as e:
            print(f"[eye_detection] 초기화 실패: {str(e)}")
            self._is_initialized = False
    
    def detect_eyes(self, image_path: str) -> List[Dict]:
        """이미지에서 고양이 눈 위치 감지"""
        print(f"[eye_detection] 눈 감지 시작: {image_path}")
        try:
            result = self.eye_detector.infer(image_path, model_id="cat-eye-2mdft-8k8ts/2")
            eyes = []
            
            for pred in result['predictions']:
                if pred['confidence'] > 0.7:  # 신뢰도 70% 이상만 처리
                    eye = {
                        'x': int(pred['x']),
                        'y': int(pred['y']),
                        'width': int(pred['width']),
                        'height': int(pred['height']),
                        'confidence': pred['confidence']
                    }
                    eyes.append(eye)
                    print(f"[eye_detection] 눈 감지됨: {eye}")
            
            return eyes
            
        except Exception as e:
            print(f"[eye_detection] 눈 감지 실패: {str(e)}")
            return []
    
    def crop_eye(self, image: np.ndarray, eye: Dict) -> np.ndarray:
        """감지된 눈 영역 추출"""
        x, y = eye['x'], eye['y']
        w, h = eye['width'], eye['height']
        
        # 여유 있게 잘라내기 (20% 더 크게)
        margin_w = int(w * 0.2)
        margin_h = int(h * 0.2)
        
        x1 = max(0, x - w//2 - margin_w)
        y1 = max(0, y - h//2 - margin_h)
        x2 = min(image.shape[1], x + w//2 + margin_w)
        y2 = min(image.shape[0], y + h//2 + margin_h)
        
        return image[y1:y2, x1:x2]
    
    def analyze_eye(self, eye_image: np.ndarray) -> Dict:
        """개별 눈 이미지 질병 분석"""
        try:
            # 이미지 전처리
            processed_img = cv2.resize(eye_image, (224, 224))
            processed_img = processed_img.astype(np.float32) / 255.0
            processed_img = np.expand_dims(processed_img, axis=0)
            
            # 모델 추론
            self.interpreter.set_tensor(self.input_details[0]['index'], processed_img)
            self.interpreter.invoke()
            
            # 결과 추출
            output_data = self.interpreter.get_tensor(self.output_details[0]['index'])
            
            diseases = {
                "blepharitis": float(output_data[0][0]),
                "conjunctivitis": float(output_data[0][1]),
                "corneal_sequestrum": float(output_data[0][2]),
                "keratitis": float(output_data[0][3]),
                "ulcer": float(output_data[0][4])
            }
            
            return diseases
            
        except Exception as e:
            print(f"[eye_detection] 눈 분석 실패: {str(e)}")
            return {}
    
    def process_image(self, image_path: str) -> Optional[Dict]:
        """이미지 처리 및 분석"""
        if not self._is_initialized:
            print("[eye_detection] 모델이 초기화되지 않았습니다")
            return None
            
        try:
            print(f"[eye_detection] 이미지 처리 시작: {image_path}")
            
            # 이미지 로드
            image = cv2.imread(image_path)
            if image is None:
                raise Exception("이미지를 불러올 수 없습니다")
            
            # 눈 감지
            eyes = self.detect_eyes(image_path)
            if not eyes:
                print("[eye_detection] 눈이 감지되지 않았습니다")
                return None
            
            results = []
            for i, eye in enumerate(eyes):
                # 눈 영역 추출
                eye_img = self.crop_eye(image, eye)
                
                # 질병 분석
                diseases = self.analyze_eye(eye_img)
                
                # 결과 저장
                result = {
                    "eye_id": i,
                    "position": eye,
                    "diseases": diseases
                }
                results.append(result)
                
                print(f"[eye_detection] 눈 {i} 분석 완료: {diseases}")
            
            # 종합 결과
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            final_result = {
                "timestamp": timestamp,
                "image_path": image_path,
                "eyes": results
            }
            
            return final_result
            
        except Exception as e:
            print(f"[eye_detection] 이미지 처리 실패: {str(e)}")
            return None
    
    def get_best_eye_results(self, results: List[Dict]) -> Optional[Dict]:
        """여러 이미지 중 최상의 눈 감지 결과 선택"""
        if not results:
            print("[eye_detection] 분석 결과가 없습니다")
            return None
        
        try:
            print("[eye_detection] 최적의 결과 선택 중...")
            
            # 각 이미지별로 양쪽 눈의 평균 신뢰도 계산
            best_result = None
            best_confidence = 0
            
            for result in results:
                if not result.get('eyes'):
                    continue
                    
                # 양쪽 눈이 모두 감지된 경우만 고려
                if len(result['eyes']) == 2:
                    avg_confidence = (
                        result['eyes'][0]['position']['confidence'] +
                        result['eyes'][1]['position']['confidence']
                    ) / 2
                    
                    # 질병 감지 확률의 최대값도 고려
                    max_disease_prob = max(
                        max(eye['diseases'].values())
                        for eye in result['eyes']
                    )
                    
                    # 종합 점수 계산 (신뢰도 70%, 질병 확률 30% 반영)
                    total_score = (avg_confidence * 0.7) + (max_disease_prob * 0.3)
                    
                    if total_score > best_confidence:
                        best_confidence = total_score
                        best_result = result
                        print(f"[eye_detection] 새로운 최적 결과 발견 (점수: {total_score:.3f})")
            
            if best_result:
                print(f"[eye_detection] 최종 선택된 이미지: {best_result['image_path']}")
                
                # 선택되지 않은 이미지들 삭제
                for result in results:
                    if result != best_result:
                        try:
                            os.remove(result['image_path'])
                            print(f"[eye_detection] 미사용 이미지 삭제: {result['image_path']}")
                        except Exception as e:
                            print(f"[eye_detection] 이미지 삭제 실패: {str(e)}")
                
                return best_result
            
            print("[eye_detection] 적합한 결과를 찾을 수 없습니다")
            return None
            
        except Exception as e:
            print(f"[eye_detection] 결과 선택 중 오류 발생: {str(e)}")
            return None
    
    def batch_process(self, image_paths: List[str]) -> Optional[Dict]:
        """여러 이미지 일괄 처리 후 최적의 결과 반환"""
        print(f"[eye_detection] 일괄 처리 시작 (이미지 {len(image_paths)}개)")
        
        # 모든 이미지 처리
        results = []
        for image_path in image_paths:
            result = self.process_image(image_path)
            if result:
                results.append(result)
        
        print(f"[eye_detection] 일괄 처리 완료 (성공: {len(results)}개)")
        
        # 최적의 결과 선택
        best_result = self.get_best_eye_results(results)
        
        if best_result:
            # Firebase 저장을 위한 데이터 구조 변환
            firebase_data = {
                "timestamp": best_result["timestamp"],
                "image_path": best_result["image_path"],
                "left_eye": None,
                "right_eye": None
            }
            
            # 왼쪽/오른쪽 눈 구분 (x 좌표로 판단)
            if len(best_result["eyes"]) == 2:
                eye1, eye2 = best_result["eyes"]
                if eye1["position"]["x"] < eye2["position"]["x"]:
                    firebase_data["left_eye"] = eye1
                    firebase_data["right_eye"] = eye2
                else:
                    firebase_data["left_eye"] = eye2
                    firebase_data["right_eye"] = eye1
            
            return firebase_data
        
        return None
