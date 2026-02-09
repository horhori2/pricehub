#!/bin/bash

# 원피스 카드 가격 수집 스크립트
cd /home/ubuntu/pricehub

# 가상환경 활성화
. venv/bin/activate

# 로그 디렉토리 생성
mkdir -p logs

# 환경변수 로드
if [ -f .env ]; then
    export $(grep -v '^#' .env | grep -v '^$' | xargs)
fi

# 시작 로그
echo "========================================" >> logs/collect_onepiece_prices.log
echo "시작: $(date)" >> logs/collect_onepiece_prices.log

# Python 스크립트 실행 (모든 카드 수집)
python collect_onepiece_prices.py << EOF
1
yes
EOF

# 종료 로그
echo "완료: $(date)" >> logs/collect_onepiece_prices.log
echo "========================================" >> logs/collect_onepiece_prices.log
