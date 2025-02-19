#!/bin/bash

# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
source venv/bin/activate

# 시스템 패키지 링크 생성
# GPIO 관련 패키지를 가상환경에 연결
ln -s /usr/lib/python3/dist-packages/RPi /home/$USER/Desktop/myonitoring/venv/lib/python3.11/site-packages/
ln -s /usr/lib/python3/dist-packages/rpi_gpio.py /home/$USER/Desktop/myonitoring/venv/lib/python3.11/site-packages/
ln -s /usr/lib/python3/dist-packages/pigpio.py /home/$USER/Desktop/myonitoring/venv/lib/python3.11/site-packages/

# 필요한 파이썬 패키지 설치
pip install fastapi
pip install uvicorn
pip install python-multipart
pip install pillow

echo "가상환경 설정 완료" 