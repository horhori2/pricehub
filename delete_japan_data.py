# delete_japan_data.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from pricehub.models import JapanCard, JapanCardPrice, JapanTargetStorePrice, JapanExpansion


def delete_all_japan_data():
    """모든 일본판 카드 데이터 삭제"""
    print("\n" + "=" * 80)
    print("⚠️  일본판 카드 데이터 삭제")
    print("=" * 80 + "\n")
    
    # 현재 데이터 수 확인
    card_count = JapanCard.objects.count()
    price_count = JapanCardPrice.objects.count()
    expansion_count = JapanExpansion.objects.count()
    
    print("현재 데이터:")
    print(f"  📦 확장팩: {expansion_count}개")
    print(f"  🎴 카드: {card_count}개")
    print(f"  💰 가격 기록: {price_count}개")
    print()
    
    if card_count == 0 and expansion_count == 0:
        print("❌ 삭제할 데이터가 없습니다.")
        return
    
    # 삭제 확인
    confirm = input("⚠️  정말로 모든 일본판 데이터를 삭제하시겠습니까? (yes/no): ").strip().lower()
    
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
    deleted_prices = JapanCardPrice.objects.all().delete()
    print(f"✅ 가격 기록 삭제: {deleted_prices[0]}개")
    
    # 2. 카드 데이터 삭제
    deleted_cards = JapanCard.objects.all().delete()
    print(f"✅ 카드 삭제: {deleted_cards[0]}개")
    
    # 3. 확장팩 데이터 삭제
    deleted_expansions = JapanExpansion.objects.all().delete()
    print(f"✅ 확장팩 삭제: {deleted_expansions[0]}개")
    
    print("\n" + "=" * 80)
    print("✅ 모든 일본판 카드 데이터가 삭제되었습니다.")
    print("=" * 80)


def delete_japan_cards_only():
    """카드 데이터만 삭제 (확장팩은 유지)"""
    print("\n" + "=" * 80)
    print("⚠️  일본판 카드 데이터만 삭제 (확장팩 유지)")
    print("=" * 80 + "\n")
    
    # 현재 데이터 수 확인
    card_count = JapanCard.objects.count()
    price_count = JapanCardPrice.objects.count()
    expansion_count = JapanExpansion.objects.count()
    
    print("현재 데이터:")
    print(f"  📦 확장팩: {expansion_count}개 (유지됨)")
    print(f"  🎴 카드: {card_count}개 (삭제 대상)")
    print(f"  💰 가격 기록: {price_count}개 (삭제 대상)")
    print()
    
    if card_count == 0:
        print("❌ 삭제할 카드가 없습니다.")
        return
    
    # 삭제 확인
    confirm = input("⚠️  모든 일본판 카드 데이터를 삭제하시겠습니까? (확장팩은 유지) (yes/no): ").strip().lower()
    
    if confirm != 'yes':
        print("취소되었습니다.")
        return
    
    print("\n삭제 중...")
    
    # 1. 가격 데이터 삭제
    deleted_prices = JapanCardPrice.objects.all().delete()
    print(f"✅ 가격 기록 삭제: {deleted_prices[0]}개")
    
    # 2. 카드 데이터 삭제
    deleted_cards = JapanCard.objects.all().delete()
    print(f"✅ 카드 삭제: {deleted_cards[0]}개")
    
    print("\n" + "=" * 80)
    print("✅ 일본판 카드 데이터가 삭제되었습니다. (확장팩은 유지)")
    print("=" * 80)


def delete_japan_prices_only():
    """가격 데이터만 삭제 (카드와 확장팩은 유지)"""
    print("\n" + "=" * 80)
    print("⚠️  일본판 가격 데이터만 삭제")
    print("=" * 80 + "\n")
    
    # 현재 데이터 수 확인
    price_count = JapanCardPrice.objects.count()
    
    print("현재 데이터:")
    print(f"  💰 가격 기록: {price_count}개 (삭제 대상)")
    print()
    
    if price_count == 0:
        print("❌ 삭제할 가격 데이터가 없습니다.")
        return
    
    # 삭제 확인
    confirm = input("⚠️  모든 일본판 가격 데이터를 삭제하시겠습니까? (yes/no): ").strip().lower()
    
    if confirm != 'yes':
        print("취소되었습니다.")
        return
    
    print("\n삭제 중...")
    
    # 가격 데이터 삭제
    deleted_prices = JapanCardPrice.objects.all().delete()
    print(f"✅ 가격 기록 삭제: {deleted_prices[0]}개")
    
    print("\n" + "=" * 80)
    print("✅ 일본판 가격 데이터가 삭제되었습니다.")
    print("=" * 80)


def delete_japan_expansion(expansion_code: str):
    """특정 확장팩과 해당 카드들 삭제"""
    print("\n" + "=" * 80)
    print(f"⚠️  일본판 확장팩 '{expansion_code}' 삭제")
    print("=" * 80 + "\n")
    
    try:
        expansion = JapanExpansion.objects.get(code=expansion_code)
    except JapanExpansion.DoesNotExist:
        print(f"❌ 확장팩 '{expansion_code}'를 찾을 수 없습니다.")
        return
    
    # 데이터 수 확인
    card_count = JapanCard.objects.filter(expansion=expansion).count()
    price_count = JapanCardPrice.objects.filter(card__expansion=expansion).count()
    
    print(f"확장팩: {expansion.name}")
    print(f"  🎴 카드: {card_count}개")
    print(f"  💰 가격 기록: {price_count}개")
    print()
    
    if card_count == 0:
        print("⚠️  이 확장팩에는 카드가 없습니다.")
        confirm = input("확장팩만 삭제하시겠습니까? (yes/no): ").strip().lower()
        if confirm == 'yes':
            expansion.delete()
            print("✅ 확장팩이 삭제되었습니다.")
        return
    
    # 삭제 확인
    confirm = input(f"⚠️  '{expansion.name}' 확장팩과 모든 카드를 삭제하시겠습니까? (yes/no): ").strip().lower()
    
    if confirm != 'yes':
        print("취소되었습니다.")
        return
    
    print("\n삭제 중...")
    
    # 확장팩 삭제 (관련 카드와 가격도 CASCADE로 자동 삭제)
    expansion.delete()
    
    print(f"✅ '{expansion.name}' 확장팩과 모든 관련 데이터가 삭제되었습니다.")


if __name__ == '__main__':
    print("\n🗾 일본판 카드 데이터 삭제 도구")
    print("=" * 80)
    print("\n선택하세요:")
    print("  1. 모든 데이터 삭제 (확장팩 + 카드 + 가격)")
    print("  2. 카드 데이터만 삭제 (확장팩 유지)")
    print("  3. 가격 데이터만 삭제 (카드 유지)")
    print("  4. 특정 확장팩 삭제")
    print("  5. 취소")
    
    choice = input("\n선택 (1/2/3/4/5): ").strip()
    
    if choice == '1':
        delete_all_japan_data()
    
    elif choice == '2':
        delete_japan_cards_only()
    
    elif choice == '3':
        delete_japan_prices_only()
    
    elif choice == '4':
        # 확장팩 목록 출력
        expansions = JapanExpansion.objects.all().order_by('code')
        if not expansions:
            print("❌ 등록된 확장팩이 없습니다.")
        else:
            print("\n등록된 확장팩:")
            for expansion in expansions:
                card_count = JapanCard.objects.filter(expansion=expansion).count()
                print(f"  - {expansion.code}: {expansion.name} ({card_count}장)")
            
            expansion_code = input("\n삭제할 확장팩 코드를 입력하세요: ").strip()
            delete_japan_expansion(expansion_code)
    
    elif choice == '5':
        print("취소되었습니다.")
    
    else:
        print("❌ 잘못된 선택입니다.")