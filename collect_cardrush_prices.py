# collect_cardrush_prices.py
import os
import sys
import django
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import re

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from pricehub.models import JapanCard, JapanCardPrice, JapanExpansion
from django.utils import timezone

# 카드러쉬 확장팩 매핑
CARDRUSH_EXPANSIONS = {
    # MEGA 시리즈
    'M4': {'name': 'ニンジャスピナー', 'url': 'https://www.cardrush-pokemon.jp/product-group/556'},
    'M3': {'name': 'ムニキスゼロ', 'url': 'https://www.cardrush-pokemon.jp/product-group/533'},
    'M2a': {'name': 'MEGAドリームex', 'url': 'https://www.cardrush-pokemon.jp/product-group/509'},
    'M2': {'name': 'インフェルノX', 'url': 'https://www.cardrush-pokemon.jp/product-group/501'},
    'M1S': {'name': 'メガブレイブ', 'url': 'https://www.cardrush-pokemon.jp/product-group/488'},
    'M1L': {'name': 'メガシンフォニア', 'url': 'https://www.cardrush-pokemon.jp/product-group/488'},
    
    # SV 시리즈 (최신순)
    'SV11B': {'name': 'ブラックボルト', 'url': 'https://www.cardrush-pokemon.jp/product-group/476'},
    'SV11W': {'name': 'ホワイトフレア', 'url': 'https://www.cardrush-pokemon.jp/product-group/476'},
    'SV10': {'name': 'ロケット団の栄光', 'url': 'https://www.cardrush-pokemon.jp/product-group/457'},
    'SV9a': {'name': '熱風のアリーナ', 'url': 'https://www.cardrush-pokemon.jp/product-group/449'},
    'SV9': {'name': 'バトルパートナーズ', 'url': 'https://www.cardrush-pokemon.jp/product-group/427'},
    'SV8a': {'name': 'テラスタルフェスex', 'url': 'https://www.cardrush-pokemon.jp/product-group/416'},
    'SV8': {'name': '超電ブレイカー', 'url': 'https://www.cardrush-pokemon.jp/product-group/411'},
    'SV7a': {'name': '楽園ドラゴーナ', 'url': 'https://www.cardrush-pokemon.jp/product-group/409'},
    'SV7': {'name': 'ステラミラクル', 'url': 'https://www.cardrush-pokemon.jp/product-group/327'},
    'SV6a': {'name': 'ナイトワンダラー', 'url': 'https://www.cardrush-pokemon.jp/product-group/318'},
    'SV6': {'name': '変幻の仮面', 'url': 'https://www.cardrush-pokemon.jp/product-group/311'},
    'SV5a': {'name': 'クリムゾンヘイズ', 'url': 'https://www.cardrush-pokemon.jp/product-group/310'},
    'SV5K': {'name': 'ワイルドフォース', 'url': 'https://www.cardrush-pokemon.jp/product-group/302'},
    'SV5M': {'name': 'サイバージャッジ', 'url': 'https://www.cardrush-pokemon.jp/product-group/302'},
    'SV4a': {'name': 'シャイニートレジャーex', 'url': 'https://www.cardrush-pokemon.jp/product-group/300'},
    'SV4M': {'name': '古代の咆哮', 'url': 'https://www.cardrush-pokemon.jp/product-group/298'},
    'SV4K': {'name': '未来の一閃', 'url': 'https://www.cardrush-pokemon.jp/product-group/298'},
    'SV3a': {'name': 'レイジングサーフ', 'url': 'https://www.cardrush-pokemon.jp/product-group/294'},
    'SV3': {'name': '黒炎の支配者', 'url': 'https://www.cardrush-pokemon.jp/product-group/286'},
    'SV2a': {'name': 'ポケモンカード151', 'url': 'https://www.cardrush-pokemon.jp/product-group/284'},
    'SV2P': {'name': 'スノーハザード', 'url': 'https://www.cardrush-pokemon.jp/product-group/280'},
    'SV2D': {'name': 'クレイバースト', 'url': 'https://www.cardrush-pokemon.jp/product-group/280'},
    'SV1a': {'name': 'トリプレットビート', 'url': 'https://www.cardrush-pokemon.jp/product-group/276'},
    'SV1S': {'name': 'スカーレットex', 'url': 'https://www.cardrush-pokemon.jp/product-group/266'},
    'SV1V': {'name': 'バイオレットex', 'url': 'https://www.cardrush-pokemon.jp/product-group/266'},
}


def extract_card_info(card_name_text):
    """
    카드명에서 정보 추출
    예: ☆SALE☆ハリテヤマ【R】{025/063} → (ハリテヤマ, R, 025, S, None)
    예: 〔状態A-〕ゲンガー【RR】{M3-049/080} → (ゲンガー, RR, 049, A-, None)
    예: リザードン【SAR】{200/165}(モンスターボールミラー) → (リザードン, SAR, 200, S, モンスターボール)
    예: ピカチュウ【AR】{205/165}(マスターボールミラー) → (ピカチュウ, AR, 205, S, マスターボール)
    """
    original_text = card_name_text
    
    # SALE 제거
    card_name_text = card_name_text.replace('☆SALE☆', '').strip()
    
    # 상태 추출 〔状態A-〕, 〔状態B〕, 〔状態C〕
    condition = 'S'  # 기본값
    condition_match = re.search(r'〔状態([A-Z][-]?)〕', card_name_text)
    if condition_match:
        condition = condition_match.group(1)
    
    # 미러 타입 추출 (モンスターボールミラー, マスターボールミラー 등)
    mirror_type = None
    mirror_match = re.search(r'\((.+?ミラー)\)', card_name_text)
    if mirror_match:
        mirror_type_full = mirror_match.group(1)
        if 'モンスターボール' in mirror_type_full:
            mirror_type = 'モンスターボール'
        elif 'マスターボール' in mirror_type_full:
            mirror_type = 'マスターボール'
        else:
            # 일반 미러
            mirror_type = 'ミラー'
    
    # 레어도 추출 【R】, 【RR】, 【SR】 등
    rarity_match = re.search(r'【(.+?)】', card_name_text)
    rarity = rarity_match.group(1) if rarity_match else None
    
    # 카드번호 추출 {025/063} 또는 {M3-117/080}
    card_number_match = re.search(r'\{(.+?)\}', card_name_text)
    if card_number_match:
        card_number_full = card_number_match.group(1)
        
        # M3-117/080 → 117/080 (확장팩 코드 제거)
        card_number_full = re.sub(r'^[A-Z0-9]+-', '', card_number_full)
        
        # 117/080 → 117 (앞부분만)
        if '/' in card_number_full:
            card_number = card_number_full.split('/')[0]
        else:
            card_number = card_number_full
    else:
        card_number = None
    
    # 카드명 추출 (상태, 레어도, 카드번호, 미러 타입 제거)
    card_name = re.sub(r'〔状態.+?〕', '', card_name_text)
    card_name = re.sub(r'【.+?】', '', card_name)
    card_name = re.sub(r'\{.+?\}', '', card_name)
    card_name = re.sub(r'\(.+?ミラー\)', '', card_name).strip()
    
    return card_name, rarity, card_number, condition, mirror_type


def parse_price(price_text):
    """가격 텍스트에서 숫자만 추출 (220円 → 220)"""
    price_match = re.search(r'(\d+)', price_text.replace(',', ''))
    return int(price_match.group(1)) if price_match else None


def parse_stock(stock_text):
    """재고 텍스트에서 숫자 추출 (在庫数 37枚 → 37)"""
    stock_match = re.search(r'(\d+)', stock_text.replace(',', ''))
    return int(stock_match.group(1)) if stock_match else 0


def crawl_cardrush_page(url, expansion_code, max_pages=None):
    """카드러쉬 페이지 크롤링 (페이지네이션 지원)"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ja-JP,ja;q=0.9',
    }
    
    all_cards = []
    current_page = 1
    current_url = url
    
    while True:
        try:
            print(f"  🔍 페이지 {current_page} 크롤링 중...")
            
            response = requests.get(current_url, headers=headers, timeout=30)
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                print(f"  ❌ HTTP {response.status_code}")
                break
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 카드 아이템 찾기
            card_items = soup.find_all('li', class_='list_item_cell')
            
            if not card_items:
                print(f"  ⚠️  카드 아이템을 찾을 수 없습니다")
                break
            
            print(f"  📦 {len(card_items)}개 카드 발견")
            
            page_cards = []
            for item in card_items:
                try:
                    # 카드명 추출
                    goods_name = item.find('span', class_='goods_name')
                    if not goods_name:
                        continue
                    
                    card_name_full = goods_name.get_text(strip=True)
                    card_name, rarity, card_number, condition, mirror_type = extract_card_info(card_name_full)
                    
                    # 확장팩 코드 확인
                    model_number = item.find('span', class_='model_number_value')
                    page_expansion_code = model_number.get_text(strip=True) if model_number else expansion_code
                    
                    # 가격 추출
                    price_elem = item.find('span', class_='figure')
                    if not price_elem:
                        continue
                    
                    price = parse_price(price_elem.get_text(strip=True))
                    if not price:
                        continue
                    
                    # 재고 추출
                    stock_elem = item.find('p', class_='stock')
                    stock = parse_stock(stock_elem.get_text(strip=True)) if stock_elem else 0
                    
                    page_cards.append({
                        'expansion_code': page_expansion_code,
                        'card_name': card_name,
                        'rarity': rarity,
                        'card_number': card_number,
                        'condition': condition,
                        'mirror_type': mirror_type,
                        'price': price,
                        'stock': stock
                    })
                    
                except Exception as e:
                    continue
            
            all_cards.extend(page_cards)
            print(f"  ✅ 페이지 {current_page}: {len(page_cards)}개 수집")
            
            # 다음 페이지 확인
            if max_pages and current_page >= max_pages:
                print(f"  ⚠️  최대 페이지 수({max_pages}) 도달")
                break
            
            # 다음 페이지 링크 찾기
            next_link = None
            
            # 방법 1: '次へ' 버튼
            next_button = soup.find('a', string=lambda x: x and '次' in x)
            if next_button and next_button.get('href'):
                next_link = next_button.get('href')
            
            # 방법 2: rel="next"
            if not next_link:
                next_button = soup.find('a', rel='next')
                if next_button and next_button.get('href'):
                    next_link = next_button.get('href')
            
            # 방법 3: 페이지 번호
            if not next_link:
                page_links = soup.find_all('a', href=re.compile(r'page=\d+'))
                for link in page_links:
                    href = link.get('href')
                    page_match = re.search(r'page=(\d+)', href)
                    if page_match and int(page_match.group(1)) == current_page + 1:
                        next_link = href
                        break
            
            if not next_link:
                print(f"  ✅ 마지막 페이지 도달")
                break
            
            # 상대 경로면 절대 경로로 변환
            if next_link.startswith('/'):
                next_link = f"https://www.cardrush-pokemon.jp{next_link}"
            elif not next_link.startswith('http'):
                base_url = '/'.join(current_url.split('/')[:3])
                next_link = f"{base_url}/{next_link}"
            
            current_url = next_link
            current_page += 1
            
            # 서버 부하 방지
            time.sleep(1)
            
        except Exception as e:
            print(f"  ❌ 크롤링 오류: {e}")
            break
    
    print(f"  📊 총 {len(all_cards)}개 카드 수집 완료 ({current_page} 페이지)")
    return all_cards


def save_cardrush_prices(cards, source='카드러쉬', verbose=True):
    """카드러쉬 가격 DB 저장 (상태별, 미러 타입별)"""
    collected_time = timezone.now()
    saved_count = 0
    not_found_count = 0
    
    for card_data in cards:
        try:
            card_number = card_data['card_number']
            expansion_code = card_data['expansion_code']
            condition = card_data.get('condition', 'S')
            mirror_type = card_data.get('mirror_type')
            
            if not card_number:
                not_found_count += 1
                continue
            
            card = None
            
            # 미러 타입이 있는 경우: shop_product_code로 정확히 매칭
            if mirror_type:
                try:
                    expansion = JapanExpansion.objects.get(code=expansion_code)
                    
                    # 몬스터볼 미러 → V1
                    if mirror_type == 'モンスターボール':
                        card = JapanCard.objects.filter(
                            card_number=card_number,
                            expansion=expansion,
                            shop_product_code__contains='-V1'
                        ).first()
                        
                        if verbose and card:
                            print(f"  🎯 몬스터볼 미러 매칭: {card_number} → {card.shop_product_code}")
                    
                    # 마스터볼 미러 → V2
                    elif mirror_type == 'マスターボール':
                        card = JapanCard.objects.filter(
                            card_number=card_number,
                            expansion=expansion,
                            shop_product_code__contains='-V2'
                        ).first()
                        
                        if verbose and card:
                            print(f"  🎯 마스터볼 미러 매칭: {card_number} → {card.shop_product_code}")
                    
                    # 일반 미러 → V3 또는 is_mirror=True
                    else:
                        card = JapanCard.objects.filter(
                            card_number=card_number,
                            expansion=expansion
                        ).filter(
                            Q(shop_product_code__contains='-V3') | Q(is_mirror=True)
                        ).first()
                        
                        if verbose and card:
                            print(f"  🎯 일반 미러 매칭: {card_number} → {card.shop_product_code}")
                    
                except JapanExpansion.DoesNotExist:
                    pass
            
            # 미러가 아니거나 매칭 실패 시: 일반 카드 검색
            if not card:
                # 1차: card_number + 확장팩으로 검색
                try:
                    expansion = JapanExpansion.objects.get(code=expansion_code)
                    card = JapanCard.objects.filter(
                        card_number=card_number,
                        expansion=expansion,
                        is_mirror=False  # 일반 카드만
                    ).first()
                except JapanExpansion.DoesNotExist:
                    pass
                
                # 2차: card_number만으로 검색
                if not card:
                    card = JapanCard.objects.filter(
                        card_number=card_number,
                        is_mirror=False
                    ).first()
                
                # 3차: shop_product_code에 card_number 포함된 것 검색
                if not card:
                    card = JapanCard.objects.filter(
                        shop_product_code__contains=f"-{card_number}-"
                    ).exclude(
                        shop_product_code__contains='-V'  # V1, V2, V3 제외
                    ).first()
            
            if not card:
                if verbose:
                    mirror_info = f" [{mirror_type}]" if mirror_type else ""
                    print(f"  ❌ 카드 없음: {card_number}{mirror_info} ({card_data['card_name']})")
                not_found_count += 1
                continue
            
            # 가격 저장 (상태 포함)
            JapanCardPrice.objects.create(
                card=card,
                price=card_data['price'],
                source=source,
                condition=condition,
                collected_at=collected_time
            )
            
            saved_count += 1
            
            if verbose and saved_count % 50 == 0:
                print(f"  💾 {saved_count}개 저장 중...")
                
        except Exception as e:
            if verbose:
                print(f"  ⚠️  저장 오류 ({card_data.get('card_name', 'Unknown')}): {e}")
    
    return saved_count, not_found_count


def collect_expansion_prices(expansion_code, max_pages=None):
    """특정 확장팩의 가격 수집"""
    print("\n" + "=" * 80)
    print(f"🃏 카드러쉬 가격 수집 - {expansion_code}")
    print("=" * 80)
    print(f"📅 수집 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    if expansion_code not in CARDRUSH_EXPANSIONS:
        print(f"❌ 확장팩 '{expansion_code}'를 찾을 수 없습니다.")
        return
    
    info = CARDRUSH_EXPANSIONS[expansion_code]
    
    print(f"📦 확장팩: {info['name']}")
    print(f"🔗 URL: {info['url']}\n")
    
    # DB에서 카드 개수 확인
    try:
        expansion = JapanExpansion.objects.get(code=expansion_code)
        db_card_count = JapanCard.objects.filter(expansion=expansion).count()
        db_mirror_count = JapanCard.objects.filter(expansion=expansion, is_mirror=True).count()
        print(f"📊 DB 카드 수: {db_card_count}개 (미러: {db_mirror_count}개)\n")
    except JapanExpansion.DoesNotExist:
        print(f"⚠️  DB에 확장팩이 없습니다\n")
    
    # 크롤링
    print("🌐 페이지 크롤링 중...")
    cards = crawl_cardrush_page(info['url'], expansion_code, max_pages=max_pages)
    
    if not cards:
        print("❌ 가격 데이터를 수집하지 못했습니다.")
        return
    
    # 미러 타입 통계
    mirror_stats = {}
    for card in cards:
        mirror_type = card.get('mirror_type', '일반')
        if mirror_type not in mirror_stats:
            mirror_stats[mirror_type] = 0
        mirror_stats[mirror_type] += 1
    
    print(f"\n📊 미러 타입 통계:")
    for mirror_type, count in sorted(mirror_stats.items()):
        print(f"  - {mirror_type if mirror_type else '일반'}: {count}개")
    print()
    
    # 저장
    saved, not_found = save_cardrush_prices(cards, verbose=True)
    
    # 결과
    print("\n" + "=" * 80)
    print("📊 가격 수집 완료")
    print("=" * 80)
    print(f"✅ DB 저장: {saved}개")
    print(f"❌ 카드없음: {not_found}개")
    print(f"📝 크롤링: {len(cards)}개")
    print()


def collect_all_prices(max_pages=None):
    """모든 확장팩의 가격 수집"""
    print("\n" + "=" * 80)
    print("🃏 카드러쉬 가격 전체 수집")
    print("=" * 80)
    print(f"📅 수집 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    print(f"📦 총 확장팩: {len(CARDRUSH_EXPANSIONS)}개\n")
    
    total_saved = 0
    total_not_found = 0
    total_crawled = 0
    
    for expansion_code, info in CARDRUSH_EXPANSIONS.items():
        print("=" * 80)
        print(f"📁 {expansion_code} - {info['name']}")
        print("=" * 80)
        print(f"🔗 {info['url']}")
        
        # 크롤링
        cards = crawl_cardrush_page(info['url'], expansion_code, max_pages=max_pages)
        
        if not cards:
            print("  ❌ 크롤링 실패\n")
            time.sleep(2)
            continue
        
        total_crawled += len(cards)
        
        # 저장
        saved, not_found = save_cardrush_prices(cards, verbose=False)
        total_saved += saved
        total_not_found += not_found
        
        print(f"  ✅ 저장: {saved}개 | ❌ 없음: {not_found}개\n")
        
        # 서버 부하 방지
        time.sleep(2)
    
    # 최종 결과
    print("\n" + "=" * 80)
    print("📊 전체 가격 수집 완료")
    print("=" * 80)
    print(f"📦 처리된 확장팩: {len(CARDRUSH_EXPANSIONS)}개")
    print(f"🎴 크롤링된 카드: {total_crawled}개")
    print(f"✅ DB 저장: {total_saved}개")
    print(f"❌ 카드없음: {total_not_found}개")
    print()


def test_crawl():
    """테스트 크롤링 (SV8a 포함, 첫 페이지만)"""
    print("\n" + "=" * 80)
    print("🧪 카드러쉬 크롤링 테스트")
    print("=" * 80)
    print("⚠️  DB 저장 없이 크롤링만 테스트합니다\n")
    
    test_expansions = {
        'SV8a': CARDRUSH_EXPANSIONS['SV8a'],  # 테라스탈페스타ex (미러 사양 테스트)
        'M1L': CARDRUSH_EXPANSIONS['M1L'],
        'SV11B': CARDRUSH_EXPANSIONS['SV11B'],
    }
    
    all_cards = []
    
    for expansion_code, info in test_expansions.items():
        print("=" * 80)
        print(f"📁 {expansion_code} - {info['name']}")
        print(f"🔗 {info['url']}")
        print("=" * 80)
        
        cards = crawl_cardrush_page(info['url'], expansion_code, max_pages=1)
        
        if cards:
            all_cards.extend(cards)
            print(f"  ✅ {len(cards)}개 카드 크롤링 성공")
            
            # 미러 카드 샘플 출력
            mirror_cards = [c for c in cards if c.get('mirror_type')]
            if mirror_cards:
                print(f"\n  🎯 미러 카드 샘플:")
                for i, card in enumerate(mirror_cards[:5], 1):
                    mirror_info = f"[{card['mirror_type']}]"
                    print(f"    {i}. {card['card_name']} ({card['card_number']}) {mirror_info} - {card['price']}円")
            
            # 일반 샘플 3개 출력
            normal_cards = [c for c in cards if not c.get('mirror_type')][:3]
            if normal_cards:
                print(f"\n  📦 일반 카드 샘플:")
                for i, card in enumerate(normal_cards, 1):
                    print(f"    {i}. {card['card_name']} ({card['card_number']}) - {card['price']}円")
        else:
            print(f"  ❌ 크롤링 실패")
        
        print()
        time.sleep(2)
    
    # 최종 결과
    print("=" * 80)
    print("테스트 완료")
    print("=" * 80)
    print(f"총 수집된 카드: {len(all_cards)}개")
    mirror_count = sum(1 for c in all_cards if c.get('mirror_type'))
    print(f"미러 카드: {mirror_count}개")
    print()


if __name__ == '__main__':
    print("\n🃏 카드러쉬 가격 수집 도구")
    print("=" * 80)
    print("\n선택하세요:")
    print("  1. 모든 확장팩 가격 수집 (전체 페이지)")
    print("  2. 특정 확장팩 가격 수집")
    print("  3. 테스트 (SV8a 포함, 첫 페이지만, DB 저장 안 함)")
    print("  4. 종료")
    
    choice = input("\n선택 (1/2/3/4): ").strip()
    
    if choice == '1':
        confirm = input("⚠️  모든 확장팩의 가격을 수집하시겠습니까? (yes/no): ")
        if confirm.lower() == 'yes':
            collect_all_prices()
        else:
            print("취소되었습니다.")
    
    elif choice == '2':
        print("\n사용 가능한 확장팩:")
        print("\n[MEGA 시리즈]")
        for code in ['M4', 'M3', 'M2a', 'M2', 'M1S', 'M1L']:
            info = CARDRUSH_EXPANSIONS[code]
            print(f"  - {code}: {info['name']}")
        
        print("\n[SV 시리즈]")
        sv_codes = [k for k in CARDRUSH_EXPANSIONS.keys() if k.startswith('SV')]
        for code in sv_codes:
            info = CARDRUSH_EXPANSIONS[code]
            print(f"  - {code}: {info['name']}")
        
        expansion_code = input("\n확장팩 코드를 입력하세요: ").strip().upper()
        
        if expansion_code in CARDRUSH_EXPANSIONS:
            collect_expansion_prices(expansion_code)
        else:
            print("❌ 잘못된 확장팩 코드입니다.")
    
    elif choice == '3':
        test_crawl()
    
    elif choice == '4':
        print("종료합니다.")
    
    else:
        print("❌ 잘못된 선택입니다.")