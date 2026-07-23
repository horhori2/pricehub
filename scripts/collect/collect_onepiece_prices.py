# collect_onepiece_prices.py
import os
import sys
import django
from datetime import datetime
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from pricehub.models import OnePieceCard, OnePieceCardPrice, OnePieceExpansion
from pricehub.utils import get_onepiece_all_prices


def collect_prices_for_all_cards():
    """모든 원피스 카드의 가격 수집"""
    print("\n" + "=" * 80)
    print("🏴‍☠️ 원피스 카드 가격 수집 시작")
    print("=" * 80)
    print(f"📅 수집 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    cards = OnePieceCard.objects.select_related('expansion').all()
    total_cards = cards.count()

    if total_cards == 0:
        print("❌ 등록된 카드가 없습니다.")
        return

    print(f"📊 총 {total_cards}개 카드 처리 시작\n")

    success_count = 0
    general_found = 0
    error_count = 0

    for idx, card in enumerate(cards, 1):
        try:
            print(f"[{idx}/{total_cards}] {card.name} ({card.card_number}) - {card.expansion.name}")

            if card.rarity == 'SP':
                print(f"  🔍 SP 카드 - 검색어: SP {card.card_number}")
            elif card.rarity == 'MANGA':
                print(f"  🎨 망가 카드 - 검색어: 망가 {card.card_number}")

            result = get_onepiece_all_prices(
                card_name=card.name,
                rarity=card.rarity,
                expansion_name=card.expansion.name,
                card_number=card.card_number,
            )

            general_price, valid_count, mall_name = result['general_price']
            valid_items = result['valid_items']

            if general_price:
                OnePieceCardPrice.objects.create(
                    card=card,
                    price=general_price,
                    source=mall_name or '알 수 없음',
                    raw_data=valid_items,
                )
                # 최신 raw_data / 시장 최저가 캐시 업데이트
                card.latest_raw_data = valid_items
                card.latest_market_price = int(general_price)
                card.save(update_fields=['latest_raw_data', 'latest_market_price'])
                general_found += 1
                print(f"  ✅ 저장: {int(general_price)}원 ({mall_name})")
            else:
                print(f"  ⚠️  최저가 없음")

            success_count += 1
            print()
            time.sleep(0.3)

        except Exception as e:
            print(f"  ❌ 오류: {e}")
            error_count += 1
            print()
            continue

    print("=" * 80)
    print("📊 가격 수집 완료")
    print("=" * 80)
    print(f"✅ 성공: {success_count}개")
    print(f"💰 최저가 발견: {general_found}개")
    print(f"❌ 오류: {error_count}개")
    if total_cards > 0:
        print(f"📈 성공률: {(general_found / total_cards * 100):.1f}%")


def collect_prices_for_expansion(expansion_code: str):
    """특정 확장팩의 카드 가격 수집"""
    print("\n" + "=" * 80)
    print(f"🏴‍☠️ 원피스 카드 가격 수집 - {expansion_code}")
    print("=" * 80)
    print(f"📅 수집 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    try:
        expansion = OnePieceExpansion.objects.get(code=expansion_code)
    except OnePieceExpansion.DoesNotExist:
        print(f"❌ 확장팩 '{expansion_code}'를 찾을 수 없습니다.")
        return

    print(f"📦 확장팩: {expansion.name}")

    cards = OnePieceCard.objects.filter(expansion=expansion).select_related('expansion')
    total_cards = cards.count()

    if total_cards == 0:
        print("❌ 해당 확장팩에 등록된 카드가 없습니다.")
        return

    print(f"📊 총 {total_cards}개 카드 처리 시작\n")

    success_count = 0
    general_found = 0
    error_count = 0

    for idx, card in enumerate(cards, 1):
        try:
            print(f"[{idx}/{total_cards}] {card.name} ({card.card_number}) - {card.rarity}")

            if card.rarity == 'SP':
                print(f"  🔍 SP 카드 - 검색어: SP {card.card_number}")
            elif card.rarity == 'MANGA':
                print(f"  🎨 망가 카드 - 검색어: 망가 {card.card_number}")

            result = get_onepiece_all_prices(
                card_name=card.name,
                rarity=card.rarity,
                expansion_name=card.expansion.name,
                card_number=card.card_number,
            )

            general_price, valid_count, mall_name = result['general_price']
            if general_price:
                OnePieceCardPrice.objects.create(
                    card=card,
                    price=general_price,
                    source=mall_name or '알 수 없음'
                )
                general_found += 1
                print(f"  ✅ 저장: {int(general_price)}원 ({mall_name})")
            else:
                print(f"  ⚠️  최저가 없음")

            success_count += 1
            print()
            time.sleep(0.3)

        except Exception as e:
            print(f"  ❌ 오류: {e}")
            error_count += 1
            print()
            continue

    print("=" * 80)
    print("📊 가격 수집 완료")
    print("=" * 80)
    print(f"✅ 성공: {success_count}개")
    print(f"💰 최저가 발견: {general_found}개")
    print(f"❌ 오류: {error_count}개")


def test_single_card(card_id: int):
    """단일 카드 테스트"""
    print("\n" + "=" * 80)
    print("🧪 단일 카드 가격 수집 테스트")
    print("=" * 80 + "\n")

    try:
        card = OnePieceCard.objects.select_related('expansion').get(id=card_id)
    except OnePieceCard.DoesNotExist:
        print(f"❌ ID {card_id}인 카드를 찾을 수 없습니다.")
        return

    print(f"카드 정보:")
    print(f"  ID: {card.id}")
    print(f"  카드명: {card.name}")
    print(f"  카드번호: {card.card_number}")
    print(f"  확장팩: {card.expansion.name}")
    print(f"  레어도: {card.rarity}")

    if card.rarity == 'SP':
        print(f"  🔍 검색어: SP {card.card_number}")
    elif card.rarity == 'MANGA':
        print(f"  🔍 검색어: 망가 {card.card_number}")
    else:
        print(f"  🔍 검색어: {card.name} {card.card_number} {card.expansion.name}")

    print()

    result = get_onepiece_all_prices(
        card_name=card.name,
        rarity=card.rarity,
        expansion_name=card.expansion.name,
        card_number=card.card_number,
    )

    general_price, valid_count, mall_name = result['general_price']

    print("=" * 80)
    print("📊 검색 결과")
    print("=" * 80)

    if general_price:
        print(f"💰 일반 최저가: {int(general_price)}원 ({mall_name})")
        print(f"   유효 상품 수: {valid_count}개")
    else:
        print(f"⚠️  일반 최저가: 없음")

    save = input("\nDB에 저장하시겠습니까? (yes/no): ").strip().lower()
    if save == 'yes':
        if general_price:
            OnePieceCardPrice.objects.create(
                card=card,
                price=general_price,
                source=mall_name or '알 수 없음'
            )
            print("✅ 저장 완료")
    else:
        print("저장을 취소했습니다.")


if __name__ == '__main__':
    print("\n🏴‍☠️ 원피스 카드 가격 수집 도구")
    print("=" * 80)
    print("\n선택하세요:")
    print("  1. 모든 카드 가격 수집")
    print("  2. 특정 확장팩 가격 수집")
    print("  3. 단일 카드 테스트")
    print("  4. 종료")

    choice = input("\n선택 (1/2/3/4): ").strip()

    if choice == '1':
        confirm = input("모든 카드의 가격을 수집하시겠습니까? (yes/no): ")
        if confirm.lower() == 'yes':
            collect_prices_for_all_cards()

    elif choice == '2':
        expansions = OnePieceExpansion.objects.all().order_by('-created_at')
        if not expansions:
            print("❌ 등록된 확장팩이 없습니다.")
        else:
            print("\n사용 가능한 확장팩:")
            for expansion in expansions:
                card_count = OnePieceCard.objects.filter(expansion=expansion).count()
                print(f"  - {expansion.code}: {expansion.name} ({card_count}장)")
            expansion_code = input("\n확장팩 코드를 입력하세요: ").strip()
            collect_prices_for_expansion(expansion_code)

    elif choice == '3':
        recent_cards = OnePieceCard.objects.select_related('expansion').order_by('-created_at')[:10]
        if not recent_cards:
            print("❌ 등록된 카드가 없습니다.")
        else:
            print("\n최근 등록된 카드:")
            for card in recent_cards:
                sp_tag = " [SP]" if card.rarity == 'SP' else ""
                manga_tag = " [망가]" if card.rarity == 'MANGA' else ""
                print(f"  ID {card.id}: {card.name} ({card.card_number}) - {card.expansion.name}{sp_tag}{manga_tag}")
            card_id = int(input("\n카드 ID를 입력하세요: ").strip())
            test_single_card(card_id)

    elif choice == '4':
        print("종료합니다.")

    else:
        print("❌ 잘못된 선택입니다.")