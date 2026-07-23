#!/bin/bash

# pricesite 카탈로그(확장팩/카드 메타데이터) 동기화 스크립트
# 가격 수집(run_collect_*.sh)이 다 끝난 뒤에 돌아야 그날 수집된
# latest_market_price가 카탈로그 캐시에 반영된다.
cd /home/ubuntu/pricehub

# 가상환경 활성화
. venv/bin/activate

# 로그 디렉토리 생성
mkdir -p logs

# 시작 로그
echo "========================================" >> logs/sync_catalog.log
echo "시작: $(date)" >> logs/sync_catalog.log

python manage.py sync_catalog >> logs/sync_catalog.log 2>&1

# 종료 로그
echo "완료: $(date)" >> logs/sync_catalog.log
echo "========================================" >> logs/sync_catalog.log
