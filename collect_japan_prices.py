# collect_japan_prices.py
import os
import sys
import django
from datetime import datetime
from django.utils import timezone
import time
import requests
from bs4 import BeautifulSoup
import re

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from pricehub.models import JapanCard, JapanCardPrice, JapanExpansion


def get_expansion_url_code(expansion_code: str) -> str:
    """확장팩 코드를 URL 코드로 변환"""
    expansion_map = {
        'M4': 'm04',
        'M3': 'm03',
        'M2a': 'm02a',
        'M2': 'm02',
        'M1L': 'm01l',
        'M1S': 'm01s',
        'SV11B': 'sv11b',
        'SV11W': 'sv11w',
        'SV10': 'sv10',
        'SV9a': 'sv09a',
        'SV9': 'sv09',
        'SV8a': 'sv08a',
        'SV8': 'sv08',
        'SV7a': 'sv07a',
        'SV7': 'sv07',
        'SV6a': 'sv06a',
        'SV6': 'sv06',
        'SV5a': 'sv05a',
        'SV5K': 'sv05k',
        'SV5M': 'sv05m',
        'SV4a': 'sv04a',
        'SV4K': 'sv04k',
        'SV4M': 'sv04m',
        'SV3a': 'sv03a',
        'SV3': 'sv03',
        'SV2a': 'sv02a',
        'SV2P': 'sv02p',
        'SV2D': 'sv02d',
        'SV1a': 'sv01a',
        'SV1S': 'sv01s',
        'SV1V': 'sv01v',

        'S12a': 's12a',
        'S12': 's12',
        'S11a': 's11a',
        'S10b': 's10b',
        'S10a': 's10a',
        'S10D': 's10d',
        'S10P': 's10p',
    }
    return expansion_map.get(expansion_code)


def extract_mirror_type_from_name(card_name: str) -> str:
    """
    카드명에서 미러 타입 추출
    - ホップのウールー(エネルギーマーク柄/ミラー仕様) → エネルギーマーク柄
    - ホップのウールー(ボール柄/ミラー仕様) → ボール柄
    """
    # (타입/ミラー仕様) 또는 (타입/ミ) 패턴에서 타입 추출
    match = re.search(r'\((.+?)(?:/ミラー仕様|/ミ)\)', card_name)
    if match:
        return match.group(1).strip()
    
    # (ミラー仕様) 만 있는 경우
    if 'ミラー仕様' in card_name or 'ミラー' in card_name:
        return "基本ミラー"
    
    return ""


def is_mirror_card_from_name(card_name: str) -> bool:
    """카드명으로 미러 여부 확인"""
    mirror_keywords = ['ミラー', 'mirror', 'MIRROR']
    mirror_patterns = ['/ミラー仕様', '/ミ']
    
    if any(keyword in card_name for keyword in mirror_keywords):
        return True
    
    if any(pattern in card_name for pattern in mirror_patterns):
        return True
    
    return False


def collect_expansion_prices_bulk(expansion_code: str) -> dict:
    """
    확장팩 페이지 한 번 크롤링으로 모든 카드 가격 수집
    
    Returns:
        {
            'card_key': {  # card_key = f"{card_number}_{mirror_type}"
                'card_number': 카드번호,
                'mirror_type': 미러타입,
                'price': 가격,
                'stock_status': 재고상태
            }
        }
    """
    url_code = get_expansion_url_code(expansion_code)
    
    if not url_code:
        print(f"⚠️  확장팩 코드 '{expansion_code}'에 대한 URL 매핑 없음")
        return {}
    
    url = f"https://yuyu-tei.jp/sell/poc/s/{url_code}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    print(f"🔍 [일본판 일괄 수집] URL: {url}")
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            print(f"❌ HTTP 오류: {response.status_code}")
            return {}
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 모든 카드 상품 찾기
        card_products = soup.select('.card-product')
        
        if not card_products:
            print(f"❌ 카드를 찾을 수 없습니다.")
            return {}
        
        print(f"✅ 발견된 카드: {len(card_products)}개")
        
        prices_data = {}
        
        for card_elem in card_products:
            try:
                # 카드번호 추출
                span_number = card_elem.select_one('span.d-block.border')
                if not span_number:
                    continue
                
                card_num_text = span_number.get_text(strip=True)
                # "250/193" → "250"
                if '/' in card_num_text:
                    card_number = card_num_text.split('/')[0]
                else:
                    card_number = card_num_text
                
                # 카드명 추출 (미러 타입 확인용)
                card_name_elem = card_elem.select_one('h4.text-primary')
                if not card_name_elem:
                    continue
                
                card_name = card_name_elem.get_text(strip=True)
                
                # 미러 여부 및 타입
                is_mirror = is_mirror_card_from_name(card_name)
                mirror_type = extract_mirror_type_from_name(card_name) if is_mirror else ""
                
                # 가격 추출
                price_elem = card_elem.select_one('strong.d-block.text-end')
                if not price_elem:
                    continue
                
                price_text = price_elem.get_text(strip=True)
                # "39,800 円" → 39800
                price_text = price_text.replace('円', '').replace(',', '').strip()
                
                try:
                    price = float(price_text)
                except ValueError:
                    continue
                
                # 재고 상태 확인
                stock_elem = card_elem.select_one('.cart_sell_zaiko')
                if stock_elem:
                    stock_text = stock_elem.get_text(strip=True)
                    if '×' in stock_text:
                        stock_status = "품절"
                    elif '○' in stock_text:
                        stock_status = "재고있음"
                    else:
                        stock_status = stock_text
                else:
                    stock_status = "알 수 없음"
                
                # 카드 키 생성 (카드번호 + 미러타입)
                card_key = f"{card_number}_{mirror_type}" if mirror_type else card_number
                
                # 저장
                prices_data[card_key] = {
                    'card_number': card_number,
                    'mirror_type': mirror_type,
                    'price': price,
                    'stock_status': stock_status,
                    'card_name': card_name
                }
                
            except Exception as e:
                continue
        
        print(f"💰 가격 수집 완료: {len(prices_data)}개")
        return prices_data
        
    except Exception as e:
        print(f"❌ 크롤링 오류: {e}")
        return {}


def collect_prices_for_expansion_bulk(expansion_code: str):
    """특정 확장팩의 모든 카드 가격을 일괄 수집"""
    print("\n" + "=" * 80)
    print(f"🗾 일본판 카드 가격 일괄 수집 - {expansion_code}")
    print("=" * 80)
    print(f"📅 수집 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 확장팩 확인
    try:
        expansion = JapanExpansion.objects.get(code=expansion_code)
    except JapanExpansion.DoesNotExist:
        print(f"❌ 확장팩 '{expansion_code}'를 찾을 수 없습니다.")
        return
    
    print(f"📦 확장팩: {expansion.name}")
    
    # DB에서 카드 목록 가져오기
    cards = JapanCard.objects.filter(expansion=expansion).select_related('expansion')
    total_cards = cards.count()
    
    if total_cards == 0:
        print("❌ 해당 확장팩에 등록된 카드가 없습니다.")
        return
    
    print(f"📊 DB 카드 수: {total_cards}개\n")
    
    # 한 번에 모든 가격 수집
    print("🌐 확장팩 페이지 크롤링 중...")
    prices_data = collect_expansion_prices_bulk(expansion_code)
    
    if not prices_data:
        print("❌ 가격 데이터를 수집하지 못했습니다.")
        return
    
    print()
    
    # DB 카드와 매칭하여 저장
    price_found = 0
    price_not_found = 0
    saved_count = 0
    
    for idx, card in enumerate(cards, 1):
        card_number = card.card_number
        mirror_type = card.mirror_type if card.mirror_type else ""
        
        # 카드 키 생성
        card_key = f"{card_number}_{mirror_type}" if mirror_type else card_number
        
        print(f"[{idx}/{total_cards}] {card.name} ({card_number})", end=" ")
        
        if card_key in prices_data:
            price_info = prices_data[card_key]
            
            # 가격 저장
            JapanCardPrice.objects.create(
                card=card,
                price=price_info['price'],
                source='유유테이',
                collected_at=timezone.now()
            )
            
            price_found += 1
            saved_count += 1
            mirror_tag = f"[{mirror_type}]" if mirror_type else ""
            print(f"✅ {int(price_info['price'])}엔 ({price_info['stock_status']}) {mirror_tag}")
        else:
            price_not_found += 1
            print(f"⚠️  가격 없음 (키: {card_key})")
    
    # 결과 출력
    print("\n" + "=" * 80)
    print("📊 가격 수집 완료")
    print("=" * 80)
    print(f"✅ 가격 발견: {price_found}개")
    print(f"💾 DB 저장: {saved_count}개")
    print(f"⚠️  가격 없음: {price_not_found}개")
    print(f"📝 총 카드: {total_cards}개")
    print()


def collect_all_prices_bulk():
    """모든 확장팩의 가격을 일괄 수집"""
    print("\n" + "=" * 80)
    print("🗾 일본판 카드 가격 전체 일괄 수집")
    print("=" * 80)
    print(f"📅 수집 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 모든 확장팩 가져오기
    expansions = JapanExpansion.objects.all().order_by('code')
    
    if not expansions:
        print("❌ 등록된 확장팩이 없습니다.")
        return
    
    print(f"📦 총 확장팩: {expansions.count()}개\n")
    
    total_price_found = 0
    total_price_not_found = 0
    total_cards = 0
    
    for expansion in expansions:
        print("=" * 80)
        print(f"처리 중: {expansion.name} ({expansion.code})")
        print("=" * 80)
        
        # DB 카드 수
        card_count = JapanCard.objects.filter(expansion=expansion).count()
        total_cards += card_count
        
        if card_count == 0:
            print("⚠️  등록된 카드 없음\n")
            continue
        
        print(f"DB 카드 수: {card_count}개")
        
        # 가격 수집
        prices_data = collect_expansion_prices_bulk(expansion.code)
        
        if not prices_data:
            print("❌ 가격 수집 실패\n")
            time.sleep(2)
            continue
        
        # DB 카드와 매칭
        cards = JapanCard.objects.filter(expansion=expansion)
        found = 0
        not_found = 0
        
        for card in cards:
            card_number = card.card_number
            mirror_type = card.mirror_type if card.mirror_type else ""
            
            # 카드 키 생성
            card_key = f"{card_number}_{mirror_type}" if mirror_type else card_number
            
            if card_key in prices_data:
                price_info = prices_data[card_key]
                
                JapanCardPrice.objects.create(
                    card=card,
                    price=price_info['price'],
                    source='유유테이'
                )
                found += 1
            else:
                not_found += 1
        
        total_price_found += found
        total_price_not_found += not_found
        
        print(f"✅ 저장: {found}개 | ⚠️  없음: {not_found}개\n")
        
        # 서버 부하 방지
        time.sleep(2)
    
    # 최종 결과
    print("\n" + "=" * 80)
    print("📊 전체 가격 수집 완료")
    print("=" * 80)
    print(f"📦 처리된 확장팩: {expansions.count()}개")
    print(f"🎴 총 카드: {total_cards}개")
    print(f"✅ 가격 발견: {total_price_found}개")
    print(f"⚠️  가격 없음: {total_price_not_found}개")
    print()


def test_single_card(card_id: int):
    """단일 카드 테스트"""
    print("\n" + "=" * 80)
    print("🧪 단일 카드 가격 수집 테스트")
    print("=" * 80 + "\n")
    
    try:
        card = JapanCard.objects.select_related('expansion').get(id=card_id)
    except JapanCard.DoesNotExist:
        print(f"❌ ID {card_id}인 카드를 찾을 수 없습니다.")
        return
    
    print(f"카드 정보:")
    print(f"  ID: {card.id}")
    print(f"  카드명: {card.name}")
    print(f"  카드번호: {card.card_number}")
    print(f"  미러타입: {card.mirror_type if card.mirror_type else '없음'}")
    print(f"  확장팩: {card.expansion.name} ({card.expansion.code})")
    print(f"  레어도: {card.rarity}")
    print(f"  상품코드: {card.shop_product_code}")
    print()
    
    # 해당 확장팩의 모든 가격 수집
    print("🌐 확장팩 페이지 크롤링 중...")
    prices_data = collect_expansion_prices_bulk(card.expansion.code)
    
    print()
    print("=" * 80)
    print("📊 검색 결과")
    print("=" * 80)
    
    # 카드 키 생성
    mirror_type = card.mirror_type if card.mirror_type else ""
    card_key = f"{card.card_number}_{mirror_type}" if mirror_type else card.card_number
    
    print(f"검색 키: {card_key}")
    
    if card_key in prices_data:
        price_info = prices_data[card_key]
        print(f"💰 가격: {int(price_info['price'])}엔")
        print(f"📦 재고: {price_info['stock_status']}")
        print(f"🏪 출처: 유유테이")
        print(f"🎴 카드명: {price_info['card_name']}")
        print()
        
        save = input("DB에 저장하시겠습니까? (yes/no): ").strip().lower()
        
        if save == 'yes':
            JapanCardPrice.objects.create(
                card=card,
                price=price_info['price'],
                source='유유테이'
            )
            print("✅ 가격 저장 완료")
        else:
            print("저장을 취소했습니다.")
    else:
        print(f"⚠️  가격 정보 없음")
        print(f"\n수집된 키 목록 샘플:")
        for i, key in enumerate(list(prices_data.keys())[:10]):
            print(f"  - {key}")
        if len(prices_data) > 10:
            print(f"  ... 외 {len(prices_data) - 10}개")


if __name__ == '__main__':
    print("\n🗾 일본판 카드 가격 수집 도구 (미러 지원)")
    print("=" * 80)
    print("\n선택하세요:")
    print("  1. 모든 확장팩 가격 일괄 수집 (빠름)")
    print("  2. 특정 확장팩 가격 일괄 수집")
    print("  3. 단일 카드 테스트")
    print("  4. 종료")
    
    choice = input("\n선택 (1/2/3/4): ").strip()
    
    if choice == '1':
        confirm = input("⚠️  모든 확장팩의 가격을 일괄 수집하시겠습니까? (yes/no): ")
        if confirm.lower() == 'yes':
            collect_all_prices_bulk()
    
    elif choice == '2':
        # 확장팩 목록 출력
        expansions = JapanExpansion.objects.all().order_by('-created_at')
        if not expansions:
            print("❌ 등록된 확장팩이 없습니다.")
        else:
            print("\n사용 가능한 확장팩:")
            for expansion in expansions:
                card_count = JapanCard.objects.filter(expansion=expansion).count()
                print(f"  - {expansion.code}: {expansion.name} ({card_count}장)")
            
            expansion_code = input("\n확장팩 코드를 입력하세요: ").strip()
            collect_prices_for_expansion_bulk(expansion_code)
    
    elif choice == '3':
        # 최근 등록된 카드
        recent_cards = JapanCard.objects.select_related('expansion').order_by('-created_at')[:10]
        if not recent_cards:
            print("❌ 등록된 카드가 없습니다.")
        else:
            print("\n최근 등록된 카드:")
            for card in recent_cards:
                mirror_tag = f" [미러:{card.mirror_type}]" if card.mirror_type else ""
                print(f"  ID {card.id}: {card.name} ({card.card_number}){mirror_tag} - {card.expansion.name}")
            
            card_id = int(input("\n카드 ID를 입력하세요: ").strip())
            test_single_card(card_id)
    
    elif choice == '4':
        print("종료합니다.")
    
    else:
        print("❌ 잘못된 선택입니다.")