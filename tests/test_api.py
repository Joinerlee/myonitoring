import requests
import json

# API 엔드포인트 URL - 정확한 서버 주소로 수정
url = 'https://myonitoring.site/api/data-collection'  # 실제 서버 주소로 변경해주세요

# 전송할 데이터
data = {
    'data_type': 'intake',
    'amount': 15.0,
    'duration': 2.5
} 

# 헤더 설정
headers = {
    'Content-Type': 'application/json'
}

try:
    # POST 요청 보내기
    response = requests.post(url, json=data, headers=headers)
    
    # 응답 확인
    response.raise_for_status()
    
    # 응답 출력
    print('상태 코드:', response.status_code)
    print('응답 내용:', response.text)
    
except requests.exceptions.RequestException as e:
    print('에러 발생:', e)  