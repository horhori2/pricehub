# collect_tcg999_prices.py
import os
import django
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from pricehub.models import Card, TargetStorePrice
from pricehub.utils import get_tcg999_price_for_card


def collect_all_tcg999_prices():
    """모든 카드의 TCG999 가격 수집"""
    print("\n" + "=" * 80)
    print("🎯 TCG999 가격 수집 시작")
    print("=" * 80 + "\n")
    
    # 모든 카드 가져오기
    cards = Card.objects.select_related('expansion').all()
    total_cards = cards.count()
    
    print(f"📊 총 {total_cards}개 카드 처리 예정\n")
    
    success_count = 0
    not_found_count = 0
    fail_count = 0
    
    for idx, card in enumerate(cards, 1):
        print(f"\n[{idx}/{total_cards}] {card.name} ({card.card_number})")
        print("-" * 60)
        
        try:
            # TCG999 가격 검색
            tcg999_price, search_query, mall_name = get_tcg999_price_for_card(
                card_name=card.name,
                rarity=card.rarity,
                expansion_name=card.expansion.name
            )
            
            # 가격 저장
            if tcg999_price is not None and mall_name:
                TargetStorePrice.objects.create(
                    card=card,
                    price=int(tcg999_price),
                    store_name=mall_name
                )
                print(f"✅ TCG999 가격 저장: {int(tcg999_price)}원")
                success_count += 1
            else:
                print(f"⚠️ TCG999에서 판매하지 않음")
                not_found_count += 1
            
            # API 요청 제한 방지
            time.sleep(0.3)
            
        except Exception as e:
            print(f"❌ 오류 발생: {e}")
            fail_count += 1
            continue
    
    # 결과 출력
    print("\n" + "=" * 80)
    print("📊 TCG999 가격 수집 완료")
    print("=" * 80)
    print(f"✅ 성공: {success_count}개")
    print(f"⚠️ TCG999 없음: {not_found_count}개")
    print(f"❌ 실패: {fail_count}개")
    print(f"📈 성공률: {success_count/total_cards*100:.1f}%")


def collect_expansion_tcg999_prices(expansion_code: str):
    """특정 확장팩의 TCG999 가격만 수집"""
    print(f"\n🔍 확장팩 '{expansion_code}' TCG999 가격 수집 시작\n")
    
    cards = Card.objects.filter(expansion__code=expansion_code).select_related('expansion')
    total_cards = cards.count()
    
    if total_cards == 0:
        print(f"❌ 확장팩 '{expansion_code}'를 찾을 수 없습니다.")
        return
    
    print(f"📊 {cards.first().expansion.name} - 총 {total_cards}개 카드\n")
    
    success_count = 0
    not_found_count = 0
    
    for idx, card in enumerate(cards, 1):
        print(f"[{idx}/{total_cards}] {card.name} ({card.rarity})")
        
        try:
            tcg999_price, search_query, mall_name = get_tcg999_price_for_card(
                card_name=card.name,
                rarity=card.rarity,
                expansion_name=card.expansion.name
            )
            
            if tcg999_price is not None and mall_name:
                TargetStorePrice.objects.create(
                    card=card,
                    price=int(tcg999_price),
                    store_name=mall_name
                )
                print(f"✅ {int(tcg999_price)}원 저장")
                success_count += 1
            else:
                print(f"⚠️ TCG999 없음")
                not_found_count += 1
            
            time.sleep(0.3)
            
        except Exception as e:
            print(f"❌ 오류: {e}")
            continue
    
    print(f"\n✅ 완료: {success_count}/{total_cards}개 성공 ({not_found_count}개 TCG999 없음)")


def test_single_card_tcg999(card_id: int):
    """단일 카드 TCG999 테스트"""
    try:
        card = Card.objects.select_related('expansion').get(id=card_id)
        
        print(f"\n🔍 테스트 카드 정보")
        print(f"카드명: {card.name}")
        print(f"레어도: {card.rarity}")
        print(f"확장팩: {card.expansion.name}")
        print(f"카드번호: {card.card_number}\n")
        
        tcg999_price, search_query, mall_name = get_tcg999_price_for_card(
            card_name=card.name,
            rarity=card.rarity,
            expansion_name=card.expansion.name
        )
        
        if tcg999_price and mall_name:
            print(f"\n💰 TCG999 가격: {int(tcg999_price)}원")
            print(f"🏪 판매처: {mall_name}")
            print(f"🔍 검색어: {search_query}")
            
            save = input("\n가격을 저장하시겠습니까? (y/n): ")
            if save.lower() == 'y':
                TargetStorePrice.objects.create(
                    card=card,
                    price=int(tcg999_price),
                    store_name=mall_name
                )
                print("✅ 저장 완료")
        else:
            print("\n⚠️ TCG999에서 판매하지 않습니다")
            
    except Card.DoesNotExist:
        print(f"❌ ID {card_id}인 카드를 찾을 수 없습니다")


if __name__ == '__main__':
    import sys
    from datetime import datetime
    
    is_terminal = sys.stdin.isatty()
    
    if is_terminal:
        # 수동 실행
        print("\n" + "=" * 80)
        print("🎯 TCG999 가격 수집 도구")
        print("=" * 80)
        print("\n선택하세요:")
        print("  1. 모든 카드 TCG999 가격 수집")
        print("  2. 특정 확장팩 TCG999 가격 수집")
        print("  3. 단일 카드 TCG999 테스트")
        print("  4. 종료")
        
        choice = input("\n선택 (1/2/3/4): ").strip()
        
        if choice == '1':
            confirm = input("모든 카드의 TCG999 가격을 수집하시겠습니까? (yes/no): ")
            if confirm.lower() == 'yes':
                collect_all_tcg999_prices()
        elif choice == '2':
            expansion_code = input("확장팩 코드를 입력하세요 (예: M2): ").strip()
            collect_expansion_tcg999_prices(expansion_code)
        elif choice == '3':
            card_id = int(input("카드 ID를 입력하세요: ").strip())
            test_single_card_tcg999(card_id)
        elif choice == '4':
            print("종료합니다.")
        else:
            print("❌ 잘못된 선택입니다.")
    else:
        # 자동 실행
        print(f"\n{'='*80}")
        print(f"🎯 TCG999 자동 실행 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}\n")
        collect_all_tcg999_prices()