#!/bin/bash

# 필요한 시스템 패키지 확인
echo "시스템 패키지 확인 중..."
PACKAGES="python3-rpi.gpio python3-pigpio libgpiod2"
for pkg in $PACKAGES; do
    if ! dpkg -l | grep -q "^ii  $pkg "; then
        echo "$pkg 패키지가 필요합니다. 설치하시겠습니까? (y/n)"
        read answer
        if [ "$answer" = "y" ]; then
            sudo apt-get install -y $pkg
        fi
    fi
done

# pigpiod 데몬 상태 확인 및 시작
if ! systemctl is-active --quiet pigpiod; then
    echo "pigpiod 데몬을 시작합니다..."
    sudo systemctl start pigpiod
    sudo systemctl enable pigpiod
fi

# GPIO 접근 권한 설정
if ! groups $USER | grep -q "gpio"; then
    echo "사용자를 gpio 그룹에 추가합니다..."
    sudo usermod -a -G gpio,video $USER
fi

# /dev/gpiomem 권한 설정
sudo chmod a+rw /dev/gpiomem

# 가상환경 생성
echo "가상환경 생성 중..."
python3 -m venv venv

# 가상환경 활성화
source venv/bin/activate

# 시스템 패키지 링크 생성
VENV_SITE_PACKAGES="venv/lib/python3.*/site-packages"
DIST_PACKAGES="/usr/lib/python3/dist-packages"

echo "시스템 패키지 링크 생성 중..."
for package in "RPi" "rpi_gpio.py" "pigpio.py"; do
    if [ -e "$DIST_PACKAGES/$package" ]; then
        ln -sf "$DIST_PACKAGES/$package" $VENV_SITE_PACKAGES/
    fi
done

# 필요한 파이썬 패키지 설치
echo "Python 패키지 설치 중..."
pip install --upgrade pip
pip install fastapi uvicorn python-multipart pillow

echo "가상환경 설정 완료"
echo "다음 명령어로 실행하세요:"
echo "source venv/bin/activate"
echo "sudo $(which python3) app/main.py" 