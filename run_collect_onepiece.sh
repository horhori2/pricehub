# 원피스 카드 가격 수집 스크립트
cd /home/ubuntu/pricehub
source venv/bin/activate

# 로그 디렉토리 생성
mkdir -p logs

# 환경변수 로드
export $(cat .env | xargs)

# Python 스크립트 실행 (모든 카드 수집)
python collect_onepiece_prices.py << EOF
1
yes
EOF

echo "원피스 카드 가격 수집 완료: $(date)" >> logs/collect_onepiece_prices.log
