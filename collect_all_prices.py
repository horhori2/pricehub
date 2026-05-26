# collect_all_prices.py
import os
import django
import time
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from pricehub.models import Card, CardPrice, TargetStorePrice
from pricehub.utils import get_all_prices_for_card


def collect_all_prices_integrated():
    """모든 카드의 가격 통합 수집 (일반 최저가 + TCG999)"""
    print("\n" + "=" * 80)
    print("💰 포켓몬카드 가격 통합 수집 시작")
    print("=" * 80 + "\n")
    
    cards = Card.objects.select_related('expansion').all()
    total_cards = cards.count()
    
    print(f"📊 총 {total_cards}개 카드 처리 예정\n")
    
    general_success = 0
    tcg999_success = 0
    both_success = 0
    fail_count = 0
    api_calls = 0
    
    for idx, card in enumerate(cards, 1):
        print(f"\n[{idx}/{total_cards}] {card.name} ({card.card_number})")
        print("-" * 60)
        
        try:
            result = get_all_prices_for_card(
                card_name=card.name,
                rarity=card.rarity,
                expansion_name=card.expansion.name
            )
            
            api_calls += 1
            
            general_price, valid_count, general_mall = result['general_price']
            tcg999_price, tcg999_mall = result['tcg999_price']
            valid_items = result['valid_items']
            
            saved_general = False
            saved_tcg999 = False
            
            # 일반 최저가 저장
            if general_price is not None and general_mall:
                CardPrice.objects.create(
                    card=card,
                    price=int(general_price),
                    source=general_mall,
                    raw_data=valid_items,  # 유효 상품 전체 저장
                )
                print(f"✅ 일반 최저가 저장: {int(general_price)}원 ({general_mall})")
                general_success += 1
                saved_general = True
            else:
                print(f"❌ 일반 최저가 없음")
            
            # TCG999 가격 저장
            if tcg999_price is not None and tcg999_mall:
                TargetStorePrice.objects.create(
                    card=card,
                    price=int(tcg999_price),
                    store_name=tcg999_mall,
                )
                print(f"✅ TCG999 저장: {int(tcg999_price)}원")
                tcg999_success += 1
                saved_tcg999 = True
            else:
                print(f"⚠️ TCG999 없음")
            
            if saved_general and saved_tcg999:
                both_success += 1
            
            if not saved_general and not saved_tcg999:
                fail_count += 1
            
            time.sleep(0.3)
            
        except Exception as e:
            print(f"❌ 오류 발생: {e}")
            fail_count += 1
            continue
    
    print("\n" + "=" * 80)
    print("📊 가격 수집 완료")
    print("=" * 80)
    print(f"🔍 API 호출 횟수: {api_calls}회")
    print(f"💰 일반 최저가 저장: {general_success}개")
    print(f"🎯 TCG999 저장: {tcg999_success}개")
    print(f"✅ 둘 다 저장: {both_success}개")
    print(f"❌ 둘 다 실패: {fail_count}개")
    if total_cards > 0:
        print(f"📈 성공률: {((general_success + tcg999_success) / (total_cards * 2) * 100):.1f}%")


def collect_expansion_prices_integrated(expansion_code: str):
    """특정 확장팩의 가격 통합 수집"""
    print(f"\n🔍 확장팩 '{expansion_code}' 가격 통합 수집 시작\n")
    
    cards = Card.objects.filter(expansion__code=expansion_code).select_related('expansion')
    total_cards = cards.count()
    
    if total_cards == 0:
        print(f"❌ 확장팩 '{expansion_code}'를 찾을 수 없습니다.")
        return
    
    print(f"📊 {cards.first().expansion.name} - 총 {total_cards}개 카드\n")
    
    general_success = 0
    tcg999_success = 0
    api_calls = 0
    
    for idx, card in enumerate(cards, 1):
        print(f"[{idx}/{total_cards}] {card.name} ({card.rarity})")
        
        try:
            result = get_all_prices_for_card(
                card_name=card.name,
                rarity=card.rarity,
                expansion_name=card.expansion.name
            )
            
            api_calls += 1
            
            general_price, valid_count, general_mall = result['general_price']
            tcg999_price, tcg999_mall = result['tcg999_price']
            
            # 저장
            if general_price is not None and general_mall:
                CardPrice.objects.create(card=card, price=int(general_price), source=general_mall)
                print(f"✅ 일반: {int(general_price)}원")
                general_success += 1
            
            if tcg999_price is not None and tcg999_mall:
                TargetStorePrice.objects.create(card=card, price=int(tcg999_price), store_name=tcg999_mall)
                print(f"✅ TCG999: {int(tcg999_price)}원")
                tcg999_success += 1
            
            time.sleep(0.3)
            
        except Exception as e:
            print(f"❌ 오류: {e}")
            continue
    
    print(f"\n✅ 완료: 일반 {general_success}개, TCG999 {tcg999_success}개 (API {api_calls}회 호출)")


def test_single_card_integrated(card_id: int):
    """단일 카드 통합 테스트"""
    try:
        card = Card.objects.select_related('expansion').get(id=card_id)
        
        print(f"\n🔍 테스트 카드 정보")
        print(f"카드명: {card.name}")
        print(f"레어도: {card.rarity}")
        print(f"확장팩: {card.expansion.name}")
        print(f"카드번호: {card.card_number}\n")
        
        result = get_all_prices_for_card(
            card_name=card.name,
            rarity=card.rarity,
            expansion_name=card.expansion.name
        )
        
        general_price, valid_count, general_mall = result['general_price']
        tcg999_price, tcg999_mall = result['tcg999_price']
        valid_items = result['valid_items']  # ← 이름 통일

        print(f"\n📊 검색 결과")
        print(f"검색어: {result['search_query']}")
        
        if general_price and general_mall:
            print(f"\n💰 일반 최저가: {int(general_price)}원")
            print(f"🏪 판매처: {general_mall}")
            print(f"📊 유효 상품: {valid_count}개")
            print(f"\n📦 valid_items 미리보기 ({len(valid_items)}개):")
            print(json.dumps(valid_items, ensure_ascii=False, indent=2))
        else:
            print("\n⚠️ 일반 최저가 없음")
        
        if tcg999_price and tcg999_mall:
            print(f"\n🎯 TCG999: {int(tcg999_price)}원")
            print(f"🏪 판매처: {tcg999_mall}")
        else:
            print("\n⚠️ TCG999 없음")
        
        save = input("\n가격을 저장하시겠습니까? (y/n): ")
        if save.lower() == 'y':
            if general_price and general_mall:
                CardPrice.objects.create(
                    card=card,
                    price=int(general_price),
                    source=general_mall,
                    raw_data=valid_items,  # 유효 상품 전체 저장
                )
                print("✅ 일반 최저가 저장")
            
            if tcg999_price and tcg999_mall:
                TargetStorePrice.objects.create(
                    card=card,
                    price=int(tcg999_price),
                    store_name=tcg999_mall,
                )
                print("✅ TCG999 저장")
            
            print("저장 완료!")
        
    except Card.DoesNotExist:
        print(f"❌ ID {card_id}인 카드를 찾을 수 없습니다")


if __name__ == '__main__':
    import sys
    import os
    from datetime import datetime
    
    is_cron = os.getenv('CRON_MODE') == 'true'
    
    try:
        is_interactive = sys.stdin.isatty() and not is_cron
    except:
        is_interactive = False
    
    if is_interactive:
        # 수동 실행
        print("\n" + "=" * 80)
        print("💰 포켓몬카드 가격 통합 수집 도구")
        print("=" * 80)
        print("\n선택하세요:")
        print("  1. 모든 카드 가격 수집 (일반 + TCG999)")
        print("  2. 특정 확장팩 가격 수집")
        print("  3. 단일 카드 테스트")
        print("  4. 종료")
        
        choice = input("\n선택 (1/2/3/4): ").strip()
        
        if choice == '1':
            confirm = input("모든 카드의 가격을 수집하시겠습니까? (yes/no): ")
            if confirm.lower() == 'yes':
                collect_all_prices_integrated()
        elif choice == '2':
            expansion_code = input("확장팩 코드를 입력하세요 (예: M2): ").strip()
            collect_expansion_prices_integrated(expansion_code)
        elif choice == '3':
            card_id = int(input("카드 ID를 입력하세요: ").strip())
            test_single_card_integrated(card_id)
        elif choice == '4':
            print("종료합니다.")
        else:
            print("❌ 잘못된 선택입니다.")
    else:
        # 자동 실행
        print(f"\n{'='*80}")
        print(f"🤖 자동 실행 모드 (통합) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}\n")
        collect_all_prices_integrated()