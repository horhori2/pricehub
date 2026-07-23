# delete_digimon_data.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from pricehub.models import DigimonCard, DigimonCardPrice, DigimonExpansion


def delete_all_digimon_data():
    """모든 디지몬 카드 데이터 삭제"""
    print("\n" + "=" * 80)
    print("⚠️  디지몬 카드 데이터 삭제")
    print("=" * 80 + "\n")

    expansion_count = DigimonExpansion.objects.count()
    card_count      = DigimonCard.objects.count()
    price_count     = DigimonCardPrice.objects.count()

    print("현재 데이터:")
    print(f"  📦 확장팩: {expansion_count}개")
    print(f"  🎴 카드: {card_count}개")
    print(f"  💰 가격 기록: {price_count}개")
    print()

    if card_count == 0 and expansion_count == 0:
        print("❌ 삭제할 데이터가 없습니다.")
        return

    confirm = input("⚠️  정말로 모든 디지몬 데이터를 삭제하시겠습니까? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("취소되었습니다.")
        return

    confirm2 = input("⚠️  이 작업은 되돌릴 수 없습니다. 계속하시겠습니까? (DELETE 입력): ").strip()
    if confirm2 != 'DELETE':
        print("취소되었습니다.")
        return

    print("\n삭제 중...")

    deleted_prices = DigimonCardPrice.objects.all().delete()
    print(f"✅ 가격 기록 삭제: {deleted_prices[0]}개")

    deleted_cards = DigimonCard.objects.all().delete()
    print(f"✅ 카드 삭제: {deleted_cards[0]}개")

    deleted_expansions = DigimonExpansion.objects.all().delete()
    print(f"✅ 확장팩 삭제: {deleted_expansions[0]}개")

    print("\n" + "=" * 80)
    print("✅ 모든 디지몬 카드 데이터가 삭제되었습니다.")
    print("=" * 80)


def delete_digimon_cards_only():
    """카드 데이터만 삭제 (확장팩 유지)"""
    print("\n" + "=" * 80)
    print("⚠️  디지몬 카드 데이터만 삭제 (확장팩 유지)")
    print("=" * 80 + "\n")

    expansion_count = DigimonExpansion.objects.count()
    card_count      = DigimonCard.objects.count()
    price_count     = DigimonCardPrice.objects.count()

    print("현재 데이터:")
    print(f"  📦 확장팩: {expansion_count}개 (유지됨)")
    print(f"  🎴 카드: {card_count}개 (삭제 대상)")
    print(f"  💰 가격 기록: {price_count}개 (삭제 대상)")
    print()

    if card_count == 0:
        print("❌ 삭제할 카드가 없습니다.")
        return

    confirm = input("⚠️  모든 디지몬 카드 데이터를 삭제하시겠습니까? (확장팩은 유지) (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("취소되었습니다.")
        return

    print("\n삭제 중...")

    deleted_prices = DigimonCardPrice.objects.all().delete()
    print(f"✅ 가격 기록 삭제: {deleted_prices[0]}개")

    deleted_cards = DigimonCard.objects.all().delete()
    print(f"✅ 카드 삭제: {deleted_cards[0]}개")

    print("\n" + "=" * 80)
    print("✅ 디지몬 카드 데이터가 삭제되었습니다. (확장팩은 유지)")
    print("=" * 80)


def delete_digimon_prices_only():
    """가격 데이터만 삭제 (카드와 확장팩 유지)"""
    print("\n" + "=" * 80)
    print("⚠️  디지몬 가격 데이터만 삭제")
    print("=" * 80 + "\n")

    price_count = DigimonCardPrice.objects.count()

    print("현재 데이터:")
    print(f"  💰 가격 기록: {price_count}개 (삭제 대상)")
    print()

    if price_count == 0:
        print("❌ 삭제할 가격 데이터가 없습니다.")
        return

    confirm = input("⚠️  모든 디지몬 가격 데이터를 삭제하시겠습니까? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("취소되었습니다.")
        return

    print("\n삭제 중...")

    deleted_prices = DigimonCardPrice.objects.all().delete()
    print(f"✅ 가격 기록 삭제: {deleted_prices[0]}개")

    print("\n" + "=" * 80)
    print("✅ 디지몬 가격 데이터가 삭제되었습니다.")
    print("=" * 80)


def delete_digimon_expansion():
    """특정 확장팩 데이터 삭제"""
    print("\n" + "=" * 80)
    print("⚠️  특정 확장팩 데이터 삭제")
    print("=" * 80 + "\n")

    expansions = DigimonExpansion.objects.all().order_by('-created_at')
    if not expansions:
        print("❌ 등록된 확장팩이 없습니다.")
        return

    print("사용 가능한 확장팩:")
    for expansion in expansions:
        card_count  = DigimonCard.objects.filter(expansion=expansion).count()
        price_count = DigimonCardPrice.objects.filter(card__expansion=expansion).count()
        print(f"  - {expansion.code}: {expansion.name} (카드 {card_count}개, 가격 {price_count}개)")

    expansion_code = input("\n삭제할 확장팩 코드를 입력하세요: ").strip()

    try:
        expansion = DigimonExpansion.objects.get(code=expansion_code)
    except DigimonExpansion.DoesNotExist:
        print(f"❌ 확장팩 '{expansion_code}'를 찾을 수 없습니다.")
        return

    card_count  = DigimonCard.objects.filter(expansion=expansion).count()
    price_count = DigimonCardPrice.objects.filter(card__expansion=expansion).count()

    print(f"\n삭제 대상: {expansion.name} ({expansion.code})")
    print(f"  🎴 카드: {card_count}개")
    print(f"  💰 가격 기록: {price_count}개")
    print()

    confirm = input("⚠️  해당 확장팩의 모든 데이터를 삭제하시겠습니까? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("취소되었습니다.")
        return

    print("\n삭제 중...")

    deleted_prices = DigimonCardPrice.objects.filter(card__expansion=expansion).delete()
    print(f"✅ 가격 기록 삭제: {deleted_prices[0]}개")

    deleted_cards = DigimonCard.objects.filter(expansion=expansion).delete()
    print(f"✅ 카드 삭제: {deleted_cards[0]}개")

    deleted_expansion = expansion.delete()
    print(f"✅ 확장팩 삭제: {expansion.name}")

    print("\n" + "=" * 80)
    print(f"✅ {expansion.name} 데이터가 삭제되었습니다.")
    print("=" * 80)


if __name__ == '__main__':
    print("\n🦕 디지몬 카드 데이터 삭제 도구")
    print("=" * 80)
    print("\n선택하세요:")
    print("  1. 모든 데이터 삭제 (확장팩 + 카드 + 가격)")
    print("  2. 카드 데이터만 삭제 (확장팩 유지)")
    print("  3. 가격 데이터만 삭제 (카드 유지)")
    print("  4. 특정 확장팩 삭제")
    print("  5. 취소")

    choice = input("\n선택 (1/2/3/4/5): ").strip()

    if choice == '1':
        delete_all_digimon_data()
    elif choice == '2':
        delete_digimon_cards_only()
    elif choice == '3':
        delete_digimon_prices_only()
    elif choice == '4':
        delete_digimon_expansion()
    elif choice == '5':
        print("취소되었습니다.")
    else:
        print("❌ 잘못된 선택입니다.")
