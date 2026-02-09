# japan_utils.py
import requests
from bs4 import BeautifulSoup
import re
from typing import Optional, Tuple, List


def search_yuyu_tei_price(expansion_url_code: str, card_number: str) -> Tuple[Optional[float], Optional[str]]:
    """
    유유테이에서 특정 카드의 가격 검색
    
    Args:
        expansion_url_code: URL 코드 (예: 'm02a')
        card_number: 카드번호 (예: '250')
    
    Returns:
        (가격, 재고상태)
    """
    url = f"https://yuyu-tei.jp/sell/poc/s/{expansion_url_code}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            return None, None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 모든 카드 상품 찾기
        card_products = soup.select('.card-product')
        
        for card_elem in card_products:
            # 카드번호 확인
            span_number = card_elem.select_one('span.d-block.border')
            if not span_number:
                continue
            
            card_num_text = span_number.get_text(strip=True)
            # "250/193" → "250"
            if '/' in card_num_text:
                current_card_num = card_num_text.split('/')[0]
            else:
                current_card_num = card_num_text
            
            # 카드번호 매칭
            if current_card_num != card_number:
                continue
            
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
                # "在庫 : ×" → "품절", "在庫 : ○" → "재고있음"
                if '×' in stock_text:
                    stock_status = "품절"
                elif '○' in stock_text:
                    stock_status = "재고있음"
                else:
                    stock_status = stock_text
            else:
                stock_status = "알 수 없음"
            
            return price, stock_status
        
        return None, None
        
    except Exception as e:
        print(f"❌ 가격 검색 오류: {e}")
        return None, None


# japan_utils.py
def get_expansion_url_code(expansion_code: str) -> Optional[str]:
    """
    확장팩 코드를 URL 코드로 변환
    M2a → m02a
    """
    expansion_map = {
        # M 시리즈
        'M3': 'm03',
        'M2a': 'm02a',
        'M2': 'm02',
        'M1L': 'm01l',
        'M1S': 'm01s',
        
        # SV11 시리즈
        'SV11B': 'sv11b',
        'SV11W': 'sv11w',
        
        # SV10 시리즈
        'SV10': 'sv10',
        
        # SV9 시리즈
        'SV9a': 'sv09a',
        'SV9': 'sv09',
        
        # SV8 시리즈
        'SV8': 'sv08',
        
        # SV7 시리즈
        'SV7a': 'sv07a',
        'SV7': 'sv07',
        
        # SV6 시리즈
        'SV6a': 'sv06a',
        'SV6': 'sv06',
        
        # SV5 시리즈
        'SV5a': 'sv05a',
        'SV5K': 'sv05k',
        'SV5M': 'sv05m',
        
        # SV4 시리즈
        'SV4K': 'sv04k',
        'SV4M': 'sv04m',
        
        # SV3 시리즈
        'SV3a': 'sv03a',
        'SV3': 'sv03',
        
        # SV2 시리즈
        'SV2a': 'sv02a',
        'SV2P': 'sv02p',
        'SV2D': 'sv02d',
        
        # SV1 시리즈
        'SV1a': 'sv01a',
        'SV1S': 'sv01s',
        'SV1V': 'sv01v',
    }
    
    return expansion_map.get(expansion_code)


def get_japan_card_price(expansion_code: str, card_number: str) -> dict:
    """
    일본판 카드 가격 조회 (통합)
    
    Args:
        expansion_code: 확장팩 코드 (예: 'M2a')
        card_number: 카드번호 (예: '250')
    
    Returns:
        {
            'price': 가격,
            'stock_status': 재고상태,
            'source': '유유테이'
        }
    """
    url_code = get_expansion_url_code(expansion_code)
    
    if not url_code:
        print(f"⚠️  확장팩 코드 '{expansion_code}'에 대한 URL 매핑 없음")
        return {
            'price': None,
            'stock_status': None,
            'source': '유유테이'
        }
    
    print(f"🔍 [일본판] 검색: {expansion_code} - {card_number}")
    
    price, stock_status = search_yuyu_tei_price(url_code, card_number)
    
    if price:
        print(f"💰 가격: {int(price)}엔 ({stock_status})")
    else:
        print(f"⚠️  가격 정보 없음")
    
    return {
        'price': price,
        'stock_status': stock_status,
        'source': '유유테이'
    }