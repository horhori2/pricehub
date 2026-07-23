# import_japan_prices.py
import os
import django
import json
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from pricehub.models import JapanCard, JapanCardPrice
from django.utils import timezone
from django.utils.dateparse import parse_datetime

print("\n" + "=" * 80)
print("🗾 일본판 카드 가격 데이터 가져오기")
print("=" * 80 + "\n")

# JSON 파일 확인
import glob
json_files = glob.glob("japan_prices_*.json")

if not json_files:
    print("❌ japan_prices_*.json 파일을 찾을 수 없습니다.")
    sys.exit(1)

# 파일 목록 표시
print("사용 가능한 파일:")
for idx, filename in enumerate(sorted(json_files, reverse=True), 1):
    file_size = os.path.getsize(filename) / 1024
    print(f"  {idx}. {filename} ({file_size:.2f} KB)")

if len(json_files) == 1:
    selected_file = json_files[0]
    print(f"\n📁 자동 선택: {selected_file}")
else:
    try:
        file_idx = int(input("\n파일 번호 선택: ").strip()) - 1
        json_files_sorted = sorted(json_files, reverse=True)
        if 0 <= file_idx < len(json_files_sorted):
            selected_file = json_files_sorted[file_idx]
        else:
            print("❌ 잘못된 번호입니다.")
            sys.exit(1)
    except (ValueError, KeyboardInterrupt):
        print("\n❌ 취소되었습니다.")
        sys.exit(1)

# JSON 파일 읽기
print("\n📖 파일 읽는 중...")
try:
    with open(selected_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
except Exception as e:
    print(f"❌ 파일 읽기 실패: {e}")
    sys.exit(1)

print(f"\n📊 파일 정보:")
print(f"  내보낸 날짜: {data.get('export_date', 'N/A')}")
print(f"  데이터 기간: {data.get('date_range', 'N/A')}")
print(f"  가격 데이터: {len(data.get('prices', []))}개")

if not data.get('prices'):
    print("\n❌ 가격 데이터가 없습니다.")
    sys.exit(1)

# 확인
try:
    confirm = input("\n이 데이터를 가져오시겠습니까? (yes/no): ").strip().lower()
except KeyboardInterrupt:
    print("\n❌ 취소되었습니다.")
    sys.exit(0)

if confirm != 'yes':
    print("취소되었습니다.")
    sys.exit(0)

# 중복 처리 옵션
print("\n중복 데이터 처리 방법:")
print("  1. 건너뛰기 (기존 데이터 유지)")
print("  2. 덮어쓰기 (기존 데이터 삭제 후 추가)")

try:
    dup_choice = input("\n선택 (1/2): ").strip()
except KeyboardInterrupt:
    print("\n❌ 취소되었습니다.")
    sys.exit(0)

if dup_choice not in ['1', '2']:
    dup_choice = '1'
    print("기본값 선택: 건너뛰기")

# 가격 데이터 가져오기
print("\n" + "=" * 80)
print("데이터 가져오는 중...")
print("=" * 80 + "\n")

created_count = 0
skipped_count = 0
error_count = 0
not_found_count = 0

for idx, price_data in enumerate(data['prices'], 1):
    try:
        # 1. 카드 찾기
        shop_code = price_data.get('shop_product_code')
        if not shop_code:
            error_count += 1
            continue
        
        try:
            card = JapanCard.objects.get(shop_product_code=shop_code)
        except JapanCard.DoesNotExist:
            not_found_count += 1
            continue
        
        # 2. 수집 시간 파싱
        collected_at_str = price_data.get('collected_at')
        if not collected_at_str:
            error_count += 1
            continue
        
        # parse_datetime 사용
        collected_at = parse_datetime(collected_at_str)
        
        if collected_at is None:
            error_count += 1
            if error_count <= 3:
                print(f"  ⚠️  시간 파싱 실패 [{idx}]: {collected_at_str}")
            continue
        
        # timezone-aware 확인
        if collected_at.tzinfo is None:
            collected_at = timezone.make_aware(collected_at)
        
        # 3. 중복 체크
        existing = JapanCardPrice.objects.filter(
            card=card,
            collected_at=collected_at
        )
        
        if existing.exists():
            if dup_choice == '2':
                existing.delete()
            else:
                skipped_count += 1
                continue
        
        # 4. 가격 데이터 생성 ★★★
        JapanCardPrice.objects.create(
            card=card,
            price=float(price_data.get('price', 0)),
            source=price_data.get('source', ''),
            collected_at=collected_at  # ★ 파싱한 시간 사용
        )
        
        created_count += 1
        
        # 진행 상황 출력
        if idx % 500 == 0 or idx <= 10:
            print(f"  [{idx}/{len(data['prices'])}] 추가: {created_count}, 건너뜀: {skipped_count}, 카드없음: {not_found_count}")
    
    except Exception as e:
        error_count += 1
        if error_count <= 5:
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

# 샘플 확인
if created_count > 0:
    print("\n📋 샘플 데이터 확인:")
    latest = JapanCardPrice.objects.order_by('-id')[:5]
    for p in latest:
        print(f"  {p.card.name}: ¥{p.price}, 수집: {p.collected_at}")

print()