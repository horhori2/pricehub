# test_time_insert.py
import os
import django
from datetime import datetime, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from pricehub.models import JapanCard, JapanCardPrice
from django.utils import timezone
from django.utils.dateparse import parse_datetime

# 테스트용 카드 하나 가져오기
card = JapanCard.objects.first()

if not card:
    print("❌ 카드가 없습니다.")
    exit()

print(f"✅ 테스트 카드: {card.name}\n")

# 테스트 1: 3일 전 시간
print("=" * 60)
print("테스트 1: timedelta로 3일 전 시간 생성")
print("=" * 60)

past_time = timezone.now() - timedelta(days=3)
print(f"넣으려는 시간: {past_time}")

price1 = JapanCardPrice.objects.create(
    card=card,
    price=1000,
    source='테스트1',
    collected_at=past_time
)

print(f"저장된 시간:   {price1.collected_at}")
print(f"일치 여부:     {'✅ 성공' if abs((price1.collected_at - past_time).total_seconds()) < 1 else '❌ 실패'}\n")

# 테스트 2: ISO 문자열 파싱 (실제 import와 동일)
print("=" * 60)
print("테스트 2: ISO 문자열 파싱 (실제 import 방식)")
print("=" * 60)

# 2026-02-06 시간으로 ISO 문자열 생성
test_time_str = "2026-02-06T14:30:00+09:00"
print(f"ISO 문자열:    {test_time_str}")

parsed_time = parse_datetime(test_time_str)
print(f"파싱된 시간:   {parsed_time}")

if parsed_time and parsed_time.tzinfo is None:
    parsed_time = timezone.make_aware(parsed_time)
    print(f"aware 변환:    {parsed_time}")

price2 = JapanCardPrice.objects.create(
    card=card,
    price=2000,
    source='테스트2',
    collected_at=parsed_time
)

print(f"저장된 시간:   {price2.collected_at}")
print(f"일치 여부:     {'✅ 성공' if abs((price2.collected_at - parsed_time).total_seconds()) < 1 else '❌ 실패'}\n")

# DB에서 직접 조회
print("=" * 60)
print("DB에서 직접 조회")
print("=" * 60)

from django.db import connection
with connection.cursor() as cursor:
    cursor.execute(
        "SELECT id, collected_at FROM japan_card_price WHERE source LIKE '테스트%' ORDER BY id"
    )
    results = cursor.fetchall()
    for row in results:
        print(f"ID {row[0]}: {row[1]}")

# 정리
print("\n테스트 데이터 삭제 중...")
JapanCardPrice.objects.filter(source__startswith='테스트').delete()
print("✅ 완료\n")
