# collect_prices.py
import os
import django
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from pricehub.models import Card, CardPrice
from pricehub.utils import get_lowest_price_for_card


def collect_all_prices():
    """모든 카드의 최저가 수집"""
    print("\n" + "=" * 80)
    print("💰 포켓몬카드 가격 수집 시작")
    print("=" * 80 + "\n")
    
    # 모든 카드 가져오기
    cards = Card.objects.select_related('expansion').all()
    total_cards = cards.count()
    
    print(f"📊 총 {total_cards}개 카드 처리 예정\n")
    
    success_count = 0
    fail_count = 0
    
    for idx, card in enumerate(cards, 1):
        print(f"\n[{idx}/{total_cards}] {card.name} ({card.card_number})")
        print("-" * 60)
        
        try:
            # 최저가 검색 (4개 반환)
            result = get_lowest_price_for_card(
                card_name=card.name,
                rarity=card.rarity,
                expansion_name=card.expansion.name
            )
            
            # 반환값 개수 확인
            if len(result) == 4:
                min_price, valid_count, search_query, mall_name = result
            elif len(result) == 3:
                min_price, valid_count, search_query = result
                mall_name = 'naver_shopping'
            else:
                print(f"❌ 예상치 못한 반환값 개수: {len(result)}")
                fail_count += 1
                continue
            
            # 가격 저장
            if min_price is not None and mall_name:
                CardPrice.objects.create(
                    card=card,
                    price=int(min_price),
                    source=mall_name
                )
                print(f"✅ 가격 저장 완료: {int(min_price)}원 ({mall_name})")
                success_count += 1
            else:
                print(f"❌ 가격을 찾을 수 없음")
                fail_count += 1
            
            # API 요청 제한 방지
            time.sleep(0.3)
            
        except Exception as e:
            print(f"❌ 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            fail_count += 1
            continue
    
    # 결과 출력
    print("\n" + "=" * 80)
    print("📊 가격 수집 완료")
    print("=" * 80)
    print(f"✅ 성공: {success_count}개")
    print(f"❌ 실패: {fail_count}개")
    if total_cards > 0:
        print(f"📈 성공률: {success_count/total_cards*100:.1f}%")


def collect_expansion_prices(expansion_code: str):
    """특정 확장팩의 가격만 수집"""
    print(f"\n🔍 확장팩 '{expansion_code}' 가격 수집 시작\n")
    
    cards = Card.objects.filter(expansion__code=expansion_code).select_related('expansion')
    total_cards = cards.count()
    
    if total_cards == 0:
        print(f"❌ 확장팩 '{expansion_code}'를 찾을 수 없습니다.")
        return
    
    print(f"📊 {cards.first().expansion.name} - 총 {total_cards}개 카드\n")
    
    success_count = 0
    
    for idx, card in enumerate(cards, 1):
        print(f"[{idx}/{total_cards}] {card.name} ({card.rarity})")
        
        try:
            result = get_lowest_price_for_card(
                card_name=card.name,
                rarity=card.rarity,
                expansion_name=card.expansion.name
            )
            
            # 반환값 개수 확인
            if len(result) == 4:
                min_price, valid_count, search_query, mall_name = result
            elif len(result) == 3:
                min_price, valid_count, search_query = result
                mall_name = 'naver_shopping'
            else:
                print(f"❌ 예상치 못한 반환값 개수: {len(result)}")
                continue
            
            if min_price is not None and mall_name:
                CardPrice.objects.create(
                    card=card,
                    price=int(min_price),
                    source=mall_name
                )
                print(f"✅ {int(min_price)}원 저장 ({mall_name})")
                success_count += 1
            else:
                print(f"❌ 가격 없음")
            
            time.sleep(0.3)
            
        except Exception as e:
            print(f"❌ 오류: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    print(f"\n✅ 완료: {success_count}/{total_cards}개 성공")


def test_single_card(card_id: int):
    """단일 카드 테스트"""
    try:
        card = Card.objects.select_related('expansion').get(id=card_id)
        
        print(f"\n🔍 테스트 카드 정보")
        print(f"카드명: {card.name}")
        print(f"레어도: {card.rarity}")
        print(f"확장팩: {card.expansion.name}")
        print(f"카드번호: {card.card_number}\n")
        
        result = get_lowest_price_for_card(
            card_name=card.name,
            rarity=card.rarity,
            expansion_name=card.expansion.name
        )
        
        # 반환값 개수 확인
        if len(result) == 4:
            min_price, valid_count, search_query, mall_name = result
        elif len(result) == 3:
            min_price, valid_count, search_query = result
            mall_name = 'naver_shopping'
        else:
            print(f"❌ 예상치 못한 반환값 개수: {len(result)}")
            return
        
        if min_price and mall_name:
            print(f"\n💰 최저가: {int(min_price)}원")
            print(f"🏪 판매처: {mall_name}")
            print(f"📊 유효 상품: {valid_count}개")
            print(f"🔍 검색어: {search_query}")
            
            save = input("\n가격을 저장하시겠습니까? (y/n): ")
            if save.lower() == 'y':
                CardPrice.objects.create(
                    card=card,
                    price=int(min_price),
                    source=mall_name
                )
                print("✅ 저장 완료")
        else:
            print("\n❌ 가격을 찾을 수 없습니다")
            
    except Card.DoesNotExist:
        print(f"❌ ID {card_id}인 카드를 찾을 수 없습니다")
    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    import sys
    from datetime import datetime
    
    # stdin이 터미널인지 확인
    is_terminal = sys.stdin.isatty()
    
    if is_terminal:
        # 수동 실행 (터미널에서 직접 실행 - 메뉴 표시)
        print("\n" + "=" * 80)
        print("💰 포켓몬카드 가격 수집 도구")
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
                collect_all_prices()
        elif choice == '2':
            expansion_code = input("확장팩 코드를 입력하세요 (예: M2): ").strip()
            collect_expansion_prices(expansion_code)
        elif choice == '3':
            card_id = int(input("카드 ID를 입력하세요: ").strip())
            test_single_card(card_id)
        elif choice == '4':
            print("종료합니다.")
        else:
            print("❌ 잘못된 선택입니다.")
    else:
        # 자동 실행 (크론잡 - 바로 수집)
        print(f"\n{'='*80}")
        print(f"🤖 자동 실행 모드 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}\n")
        collect_all_prices()