# import_japan_prices.py
import os
import django
import json
import sys
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from pricehub.models import JapanCard, JapanCardPrice
from django.utils import timezone
import pytz

print("\n" + "=" * 80)
print("🗾 일본판 카드 가격 데이터 가져오기")
print("=" * 80 + "\n")

# JSON 파일 확인
import glob
json_files = glob.glob("japan_prices_*.json")

if not json_files:
    print("❌ japan_prices_*.json 파일을 찾을 수 없습니다.")
    exit()

# 파일 목록 표시
print("사용 가능한 파일:")
for idx, filename in enumerate(sorted(json_files, reverse=True), 1):
    file_size = os.path.getsize(filename) / 1024
    print(f"  {idx}. {filename} ({file_size:.2f} KB)")

if len(json_files) == 1:
    selected_file = json_files[0]
    print(f"\n📁 선택된 파일: {selected_file}")
else:
    file_idx = int(input("\n파일 번호 선택: ").strip()) - 1
    if 0 <= file_idx < len(json_files):
        selected_file = sorted(json_files, reverse=True)[file_idx]
    else:
        print("❌ 잘못된 번호입니다.")
        exit()

# JSON 파일 읽기
print("\n파일 읽는 중...")
with open(selected_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"\n📊 파일 정보:")
print(f"  내보낸 날짜: {data['export_date']}")
print(f"  데이터 기간: {data['date_range']}")
print(f"  가격 데이터: {len(data['prices'])}개")

# 확인
confirm = input("\n이 데이터를 가져오시겠습니까? (yes/no): ").strip().lower()

if confirm != 'yes':
    print("취소되었습니다.")
    exit()

# 중복 처리 옵션
print("\n중복 데이터 처리 방법:")
print("  1. 건너뛰기 (기존 데이터 유지)")
print("  2. 덮어쓰기 (기존 데이터 삭제 후 추가)")

dup_choice = input("\n선택 (1/2): ").strip()

# 한국 시간대
kst = pytz.timezone('Asia/Seoul')

# 가격 데이터 가져오기
print("\n데이터 가져오는 중...")

created_count = 0
skipped_count = 0
error_count = 0
not_found_count = 0

for idx, price_data in enumerate(data['prices'], 1):
    try:
        # 카드 찾기
        try:
            card = JapanCard.objects.get(shop_product_code=price_data['shop_product_code'])
        except JapanCard.DoesNotExist:
            not_found_count += 1
            if idx % 100 == 0:
                print(f"  처리 중: {idx}/{len(data['prices'])} (카드 없음: {not_found_count})")
            continue
        
        # 수집 시간 파싱
        collected_at = datetime.fromisoformat(price_data['collected_at'])
        
        # timezone-aware로 변환
        if collected_at.tzinfo is None:
            collected_at = kst.localize(collected_at)
        
        # 중복 체크
        exists = JapanCardPrice.objects.filter(
            card=card,
            collected_at=collected_at
        ).exists()
        
        if exists:
            if dup_choice == '2':
                # 덮어쓰기: 기존 삭제 후 추가
                JapanCardPrice.objects.filter(
                    card=card,
                    collected_at=collected_at
                ).delete()
                
                JapanCardPrice.objects.create(
                    card=card,
                    price=price_data['price'],
                    source=price_data['source'],
                    collected_at=collected_at
                )
                created_count += 1
            else:
                # 건너뛰기
                skipped_count += 1
        else:
            # 새로 추가
            JapanCardPrice.objects.create(
                card=card,
                price=price_data['price'],
                source=price_data['source'],
                collected_at=collected_at
            )
            created_count += 1
        
        if idx % 100 == 0:
            print(f"  처리 중: {idx}/{len(data['prices'])} (추가: {created_count}, 건너뜀: {skipped_count})")
    
    except Exception as e:
        error_count += 1
        if error_count <= 5:  # 처음 5개 에러만 출력
            print(f"  ⚠️  오류 [{idx}]: {e}")
        continue

# 결과 출력
print("\n" + "=" * 80)
print("✅ 가져오기 완료!")
print("=" * 80)
print(f"✅ 추가된 가격: {created_count}개")
print(f"⏭️  건너뛴 가격: {skipped_count}개")
print(f"❌ 카드 없음: {not_found_count}개")
print(f"⚠️  오류 발생: {error_count}개")
print(f"📝 총 처리: {len(data['prices'])}개")
print()