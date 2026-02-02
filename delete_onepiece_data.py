# delete_onepiece_data.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from pricehub.models import OnePieceCard, OnePieceCardPrice, OnePieceTargetStorePrice, OnePieceExpansion


def delete_all_onepiece_data():
    """모든 원피스 카드 데이터 삭제"""
    print("\n" + "=" * 80)
    print("⚠️  원피스 카드 데이터 삭제")
    print("=" * 80 + "\n")
    
    # 현재 데이터 수 확인
    card_count = OnePieceCard.objects.count()
    price_count = OnePieceCardPrice.objects.count()
    target_price_count = OnePieceTargetStorePrice.objects.count()
    expansion_count = OnePieceExpansion.objects.count()
    
    print("현재 데이터:")
    print(f"  📦 확장팩: {expansion_count}개")
    print(f"  🎴 카드: {card_count}개")
    print(f"  💰 일반 가격 기록: {price_count}개")
    print(f"  👑 카드킹덤 가격 기록: {target_price_count}개")
    print()
    
    if card_count == 0 and expansion_count == 0:
        print("❌ 삭제할 데이터가 없습니다.")
        return
    
    # 삭제 확인
    confirm = input("⚠️  정말로 모든 원피스 데이터를 삭제하시겠습니까? (yes/no): ").strip().lower()
    
    if confirm != 'yes':
        print("취소되었습니다.")
        return
    
    # 재확인
    confirm2 = input("⚠️  이 작업은 되돌릴 수 없습니다. 계속하시겠습니까? (DELETE 입력): ").strip()
    
    if confirm2 != 'DELETE':
        print("취소되었습니다.")
        return
    
    print("\n삭제 중...")
    
    # 1. 가격 데이터 삭제 (외래키 관계로 먼저 삭제)
    deleted_prices = OnePieceCardPrice.objects.all().delete()
    print(f"✅ 일반 가격 기록 삭제: {deleted_prices[0]}개")
    
    deleted_target_prices = OnePieceTargetStorePrice.objects.all().delete()
    print(f"✅ 카드킹덤 가격 기록 삭제: {deleted_target_prices[0]}개")
    
    # 2. 카드 데이터 삭제
    deleted_cards = OnePieceCard.objects.all().delete()
    print(f"✅ 카드 삭제: {deleted_cards[0]}개")
    
    # 3. 확장팩 데이터 삭제
    deleted_expansions = OnePieceExpansion.objects.all().delete()
    print(f"✅ 확장팩 삭제: {deleted_expansions[0]}개")
    
    print("\n" + "=" * 80)
    print("✅ 모든 원피스 카드 데이터가 삭제되었습니다.")
    print("=" * 80)


def delete_onepiece_cards_only():
    """카드 데이터만 삭제 (확장팩은 유지)"""
    print("\n" + "=" * 80)
    print("⚠️  원피스 카드 데이터만 삭제 (확장팩 유지)")
    print("=" * 80 + "\n")
    
    # 현재 데이터 수 확인
    card_count = OnePieceCard.objects.count()
    price_count = OnePieceCardPrice.objects.count()
    target_price_count = OnePieceTargetStorePrice.objects.count()
    expansion_count = OnePieceExpansion.objects.count()
    
    print("현재 데이터:")
    print(f"  📦 확장팩: {expansion_count}개 (유지됨)")
    print(f"  🎴 카드: {card_count}개 (삭제 대상)")
    print(f"  💰 일반 가격 기록: {price_count}개 (삭제 대상)")
    print(f"  👑 카드킹덤 가격 기록: {target_price_count}개 (삭제 대상)")
    print()
    
    if card_count == 0:
        print("❌ 삭제할 카드가 없습니다.")
        return
    
    # 삭제 확인
    confirm = input("⚠️  모든 원피스 카드 데이터를 삭제하시겠습니까? (확장팩은 유지) (yes/no): ").strip().lower()
    
    if confirm != 'yes':
        print("취소되었습니다.")
        return
    
    print("\n삭제 중...")
    
    # 1. 가격 데이터 삭제
    deleted_prices = OnePieceCardPrice.objects.all().delete()
    print(f"✅ 일반 가격 기록 삭제: {deleted_prices[0]}개")
    
    deleted_target_prices = OnePieceTargetStorePrice.objects.all().delete()
    print(f"✅ 카드킹덤 가격 기록 삭제: {deleted_target_prices[0]}개")
    
    # 2. 카드 데이터 삭제
    deleted_cards = OnePieceCard.objects.all().delete()
    print(f"✅ 카드 삭제: {deleted_cards[0]}개")
    
    print("\n" + "=" * 80)
    print("✅ 원피스 카드 데이터가 삭제되었습니다. (확장팩은 유지)")
    print("=" * 80)


def delete_onepiece_prices_only():
    """가격 데이터만 삭제 (카드와 확장팩은 유지)"""
    print("\n" + "=" * 80)
    print("⚠️  원피스 가격 데이터만 삭제")
    print("=" * 80 + "\n")
    
    # 현재 데이터 수 확인
    price_count = OnePieceCardPrice.objects.count()
    target_price_count = OnePieceTargetStorePrice.objects.count()
    
    print("현재 데이터:")
    print(f"  💰 일반 가격 기록: {price_count}개 (삭제 대상)")
    print(f"  👑 카드킹덤 가격 기록: {target_price_count}개 (삭제 대상)")
    print()
    
    if price_count == 0 and target_price_count == 0:
        print("❌ 삭제할 가격 데이터가 없습니다.")
        return
    
    # 삭제 확인
    confirm = input("⚠️  모든 원피스 가격 데이터를 삭제하시겠습니까? (yes/no): ").strip().lower()
    
    if confirm != 'yes':
        print("취소되었습니다.")
        return
    
    print("\n삭제 중...")
    
    # 가격 데이터 삭제
    deleted_prices = OnePieceCardPrice.objects.all().delete()
    print(f"✅ 일반 가격 기록 삭제: {deleted_prices[0]}개")
    
    deleted_target_prices = OnePieceTargetStorePrice.objects.all().delete()
    print(f"✅ 카드킹덤 가격 기록 삭제: {deleted_target_prices[0]}개")
    
    print("\n" + "=" * 80)
    print("✅ 원피스 가격 데이터가 삭제되었습니다.")
    print("=" * 80)


if __name__ == '__main__':
    print("\n🏴‍☠️ 원피스 카드 데이터 삭제 도구")
    print("=" * 80)
    print("\n선택하세요:")
    print("  1. 모든 데이터 삭제 (확장팩 + 카드 + 가격)")
    print("  2. 카드 데이터만 삭제 (확장팩 유지)")
    print("  3. 가격 데이터만 삭제 (카드 유지)")
    print("  4. 취소")
    
    choice = input("\n선택 (1/2/3/4): ").strip()
    
    if choice == '1':
        delete_all_onepiece_data()
    elif choice == '2':
        delete_onepiece_cards_only()
    elif choice == '3':
        delete_onepiece_prices_only()
    elif choice == '4':
        print("취소되었습니다.")
    else:
        print("❌ 잘못된 선택입니다.")