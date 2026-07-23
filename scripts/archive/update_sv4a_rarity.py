import os
import django
 
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
 
from pricehub.models import Card
 
EXPANSION_CODE = 'SV4A'
START_NUM = 191
END_NUM   = 319
FROM_RARITY = 'C'
TO_RARITY   = '이로치'
 
 
def update_rarity():
    print(f"\n{'='*60}")
    print(f"  SV4A {START_NUM}~{END_NUM}번 레어도 변경: {FROM_RARITY} → {TO_RARITY}")
    print(f"{'='*60}\n")
 
    # 대상 카드 조회 (shop_product_code 패턴 기반)
    candidates = Card.objects.filter(
        expansion__code=EXPANSION_CODE,
        rarity=FROM_RARITY,
    ).select_related('expansion')
 
    # 카드번호를 숫자로 비교하여 191~319 범위 필터링
    target_codes = []
    for card in candidates:
        # shop_product_code 예: PKM-SV4A-191-K
        parts = card.shop_product_code.split('-')
        # 형식: PKM - SV4A - <num> - K
        if len(parts) >= 3:
            try:
                num = int(parts[2])
                if START_NUM <= num <= END_NUM:
                    target_codes.append(card.shop_product_code)
            except ValueError:
                pass
 
    target_qs = Card.objects.filter(shop_product_code__in=target_codes)
    count = target_qs.count()
 
    if count == 0:
        print("⚠️  변경 대상 카드가 없습니다.")
        print("   - 확장팩 코드, 레어도, 번호 범위를 확인하세요.")
        return
 
    print(f"📋 변경 대상: {count}개 카드\n")
 
    # 미리보기 (첫 5개 + 마지막 5개)
    preview = list(target_qs.order_by('card_number'))
    show = preview[:5] + (['...'] if count > 10 else []) + (preview[-5:] if count > 5 else [])
    for item in show:
        if item == '...':
            print(f"   ... (중간 {count - 10}개 생략)")
        else:
            print(f"   {item.shop_product_code}  |  {item.card_number}  |  {item.name}  |  {item.rarity}")
 
    print()
    confirm = input(f"위 {count}개 카드의 레어도를 '{TO_RARITY}'로 변경하시겠습니까? (yes/no): ").strip()
    if confirm.lower() != 'yes':
        print("❌ 취소되었습니다.")
        return
 
    updated = target_qs.update(rarity=TO_RARITY)
    print(f"\n✅ {updated}개 카드 레어도 변경 완료: {FROM_RARITY} → {TO_RARITY}")
 
 
if __name__ == '__main__':
    update_rarity()