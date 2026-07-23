# add_missing_card.py
import os
import django

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from pricehub.models import Expansion, Card

# ========================================
# 여기에 등록할 카드 정보를 입력하세요
# ========================================

CARDS_TO_ADD = [
    {
        'expansion_code': 'M2',           # 확장팩 코드
        'card_number': '116',             # 카드번호
        'card_name': '메가리자몽 ex',     # 카드명
        'rarity': 'MUR',                  # 레어도
        'image_url': '',  # 이미지 URL
    },
    {
        'expansion_code': 'M2',           # 확장팩 코드
        'card_number': '106',             # 카드번호
        'card_name': '블래리의 한 수',     # 카드명
        'rarity': 'SR',                  # 레어도
        'image_url': '',  # 이미지 URL
    },
    {
        'expansion_code': 'M2A',           # 확장팩 코드
        'card_number': '234',             # 카드번호
        'card_name': '피카츄 ex',     # 카드명
        'rarity': 'SAR',                  # 레어도
        'image_url': '',  # 이미지 URL
    },
    {
        'expansion_code': 'M2A',           # 확장팩 코드
        'card_number': '235',             # 카드번호
        'card_name': '메가저리더프 ex',     # 카드명
        'rarity': 'SAR',                  # 레어도
        'image_url': '',  # 이미지 URL
    },
    {
        'expansion_code': 'M2A',           # 확장팩 코드
        'card_number': '249',             # 카드번호
        'card_name': '서퍼',     # 카드명
        'rarity': 'SAR',                  # 레어도
        'image_url': '',  # 이미지 URL
    },
    {
        'expansion_code': 'M2A',           # 확장팩 코드
        'card_number': '250',             # 카드번호
        'card_name': '메가망나뇽 ex',     # 카드명
        'rarity': 'MUR',                  # 레어도
        'image_url': '',  # 이미지 URL
    },
    {
        'expansion_code': 'M1S',           # 확장팩 코드
        'card_number': '092',             # 카드번호
        'card_name': '메가가디안 ex',     # 카드명
        'rarity': 'MUR',                  # 레어도
        'image_url': '',  # 이미지 URL
    },
    {
        'expansion_code': 'M1L',           # 확장팩 코드
        'card_number': '092',             # 카드번호
        'card_name': '메가루카리오 ex',     # 카드명
        'rarity': 'MUR',                  # 레어도
        'image_url': '',  # 이미지 URL
    },
]

# ========================================
# 여기서부터는 수정하지 마세요
# ========================================

def generate_shop_product_code(expansion_code: str, card_number: str, rarity: str) -> str:
    """네이버 상품코드 생성"""
    base_code = f'PKM-{expansion_code}-{card_number}-K'
    
    if rarity == '몬스터볼':
        return f'{base_code}-V1'
    elif rarity == '마스터볼':
        return f'{base_code}-V2'
    elif rarity == '미러':
        return f'{base_code}-V3'
    else:
        return base_code


def add_missing_cards():
    """누락된 카드 DB에 추가"""
    print("\n" + "=" * 80)
    print("📝 누락된 카드 등록 시작")
    print("=" * 80 + "\n")
    
    added_count = 0
    updated_count = 0
    error_count = 0
    
    for idx, card_data in enumerate(CARDS_TO_ADD, 1):
        expansion_code = card_data['expansion_code']
        card_number = card_data['card_number']
        card_name = card_data['card_name']
        rarity = card_data['rarity']
        image_url = card_data.get('image_url', '')
        
        print(f"[{idx}/{len(CARDS_TO_ADD)}] 처리 중...")
        print(f"  확장팩: {expansion_code}")
        print(f"  카드번호: {card_number}")
        print(f"  카드명: {card_name}")
        print(f"  레어도: {rarity}")
        
        try:
            # 확장팩 확인
            try:
                expansion = Expansion.objects.get(code=expansion_code)
                print(f"  확장팩 확인: {expansion.name}")
            except Expansion.DoesNotExist:
                print(f"  ❌ 오류: 확장팩 '{expansion_code}'를 찾을 수 없습니다.")
                error_count += 1
                continue
            
            # 레어도 확인
            valid_rarities = [choice[0] for choice in Card.RARITY_CHOICES]
            if rarity not in valid_rarities:
                print(f"  ⚠️  경고: 레어도 '{rarity}'가 유효하지 않습니다. 사용 가능한 레어도:")
                print(f"  {', '.join(valid_rarities)}")
                print(f"  'C'로 저장합니다.")
                rarity = 'C'
            
            # 상품코드 생성
            shop_product_code = generate_shop_product_code(expansion_code, card_number, rarity)
            print(f"  상품코드: {shop_product_code}")
            
            # 카드 저장 (중복 시 업데이트)
            card, created = Card.objects.update_or_create(
                shop_product_code=shop_product_code,
                defaults={
                    'expansion': expansion,
                    'card_number': card_number,
                    'name': card_name,
                    'rarity': rarity,
                    'image_url': image_url
                }
            )
            
            if created:
                print(f"  ✅ 새로운 카드 등록 완료!")
                added_count += 1
            else:
                print(f"  ✅ 기존 카드 업데이트 완료!")
                updated_count += 1
            
            print()
            
        except Exception as e:
            print(f"  ❌ 오류 발생: {e}")
            error_count += 1
            print()
            continue
    
    # 결과 출력
    print("=" * 80)
    print("📊 등록 완료")
    print("=" * 80)
    print(f"✅ 새로 등록: {added_count}개")
    print(f"🔄 업데이트: {updated_count}개")
    print(f"❌ 오류: {error_count}개")
    print(f"📝 총 처리: {len(CARDS_TO_ADD)}개")


if __name__ == '__main__':
    print("\n⚠️  주의: 스크립트를 실행하기 전에 CARDS_TO_ADD 리스트를 확인하세요!")
    print("현재 등록할 카드:")
    for idx, card in enumerate(CARDS_TO_ADD, 1):
        print(f"  {idx}. [{card['expansion_code']}] {card['card_name']} ({card['card_number']}) - {card['rarity']}")
    
    confirm = input("\n계속 진행하시겠습니까? (yes/no): ")
    
    if confirm.lower() == 'yes':
        add_missing_cards()
    else:
        print("취소되었습니다.")