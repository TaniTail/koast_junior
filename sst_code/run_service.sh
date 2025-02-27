#!/bin/sh

# 서비스 등록
sudo systemctl daemon-reload

# 서비스 시작
sudo systemctl start stt-server-test

# 부팅 시 자동 시작 설정
sudo systemctl enable stt-server-test

# 상태 확인
sudo systemctl status stt-server-test

# 로그 확인
sudo journalctl -u stt-server-test -f

## 서비스 중지
#sudo systemctl stop stt-server
#
## 서비스 재시작
#sudo systemctl restart stt-server
#
## 서비스 비활성화
#sudo systemctl disable stt-server
