# export_japan_prices.py
import os
import django
import json
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from pricehub.models import JapanCardPrice

print("\n" + "=" * 80)
print("🗾 일본판 카드 가격 데이터 내보내기")
print("=" * 80 + "\n")

# 날짜 필터 옵션
print("내보낼 가격 데이터 범위를 선택하세요:")
print("  1. 오늘 수집한 데이터만")
print("  2. 최근 7일 데이터")
print("  3. 최근 30일 데이터")
print("  4. 전체 데이터")

choice = input("\n선택 (1/2/3/4): ").strip()

# 날짜 필터 적용
from datetime import timedelta
from django.utils import timezone

now = timezone.now()

if choice == '1':
    start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    date_label = "오늘"
elif choice == '2':
    start_date = now - timedelta(days=7)
    date_label = "최근 7일"
elif choice == '3':
    start_date = now - timedelta(days=30)
    date_label = "최근 30일"
else:
    start_date = None
    date_label = "전체"

# 가격 데이터 쿼리
if start_date:
    prices = JapanCardPrice.objects.filter(
        collected_at__gte=start_date
    ).select_related('card__expansion')
else:
    prices = JapanCardPrice.objects.all().select_related('card__expansion')

total_count = prices.count()

if total_count == 0:
    print(f"\n❌ {date_label} 가격 데이터가 없습니다.")
    exit()

print(f"\n📊 {date_label} 가격 데이터: {total_count}개")

# JSON 데이터 준비
data = {
    'export_date': now.isoformat(),
    'date_range': date_label,
    'prices': []
}

print("\n데이터 처리 중...")

for idx, price in enumerate(prices, 1):
    data['prices'].append({
        'shop_product_code': price.card.shop_product_code,
        'price': float(price.price),
        'source': price.source,
        'collected_at': price.collected_at.isoformat(),
    })
    
    if idx % 100 == 0:
        print(f"  처리 중: {idx}/{total_count}")

# 파일명 생성 (날짜 포함)
filename = f"japan_prices_{now.strftime('%Y%m%d_%H%M%S')}.json"

# JSON 파일로 저장
with open(filename, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("\n" + "=" * 80)
print("✅ 내보내기 완료!")
print("=" * 80)
print(f"📁 파일: {filename}")
print(f"📊 가격 데이터: {len(data['prices'])}개")
print(f"📅 수집 기간: {date_label}")
print(f"💾 파일 크기: {os.path.getsize(filename) / 1024:.2f} KB")
print()