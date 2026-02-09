# save_japan_cards_to_db.py
import os
import django
import requests
from bs4 import BeautifulSoup
import re
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from pricehub.models import JapanExpansion, JapanCard

# ==================== 일본판 확장팩 목록 ====================
JAPAN_EXPANSIONS = [
    # M 시리즈
    {'code': 'M3', 'url_code': 'm03'},
    {'code': 'M2a', 'url_code': 'm02a'},
    {'code': 'M2', 'url_code': 'm02'},
    {'code': 'M1L', 'url_code': 'm01l'},
    {'code': 'M1S', 'url_code': 'm01s'},
    
    # SV11 시리즈
    {'code': 'SV11B', 'url_code': 'sv11b'},
    {'code': 'SV11W', 'url_code': 'sv11w'},
    
    # SV10 시리즈
    {'code': 'SV10', 'url_code': 'sv10'},
    
    # SV9 시리즈
    {'code': 'SV9a', 'url_code': 'sv09a'},
    {'code': 'SV9', 'url_code': 'sv09'},
    
    # SV8 시리즈
    {'code': 'SV8', 'url_code': 'sv08'},
    
    # SV7 시리즈
    {'code': 'SV7a', 'url_code': 'sv07a'},
    {'code': 'SV7', 'url_code': 'sv07'},
    
    # SV6 시리즈
    {'code': 'SV6a', 'url_code': 'sv06a'},
    {'code': 'SV6', 'url_code': 'sv06'},
    
    # SV5 시리즈
    {'code': 'SV5a', 'url_code': 'sv05a'},
    {'code': 'SV5K', 'url_code': 'sv05k'},
    {'code': 'SV5M', 'url_code': 'sv05m'},
    
    # SV4 시리즈
    {'code': 'SV4K', 'url_code': 'sv04k'},
    {'code': 'SV4M', 'url_code': 'sv04m'},
    
    # SV3 시리즈
    {'code': 'SV3a', 'url_code': 'sv03a'},
    {'code': 'SV3', 'url_code': 'sv03'},
    
    # SV2 시리즈
    {'code': 'SV2a', 'url_code': 'sv02a'},
    {'code': 'SV2P', 'url_code': 'sv02p'},
    {'code': 'SV2D', 'url_code': 'sv02d'},
    
    # SV1 시리즈
    {'code': 'SV1a', 'url_code': 'sv01a'},
    {'code': 'SV1S', 'url_code': 'sv01s'},
    {'code': 'SV1V', 'url_code': 'sv01v'},
]

# ==================== 유틸리티 함수 ====================

def extract_expansion_name(soup) -> str:
    """
    확장팩명 추출 (h1 태그에서)
    예: [M3] 拡張パック ムニキスゼロ | シングルカード販売 | ポケモンカードゲーム
    → 拡張パック ムニキスゼロ
    """
    # h1 태그 찾기
    h1_elem = soup.find('h1')
    
    if not h1_elem:
        return ""
    
    full_text = h1_elem.get_text(strip=True)
    
    # 1. | 로 분리해서 첫 번째 부분만 가져오기
    if '|' in full_text:
        full_text = full_text.split('|')[0].strip()
    
    # 2. [코드] 부분 제거
    # [M3] 拡張パック ムニキスゼロ → 拡張パック ムニキスゼロ
    match = re.search(r'\[.+?\]\s*(.+)', full_text)
    if match:
        return match.group(1).strip()
    
    return full_text


def extract_card_number_from_alt(alt_text: str) -> tuple:
    """
    alt 텍스트에서 카드번호와 레어도 추출
    예: "250/193 MUR メガカイリューex" → ("250", "MUR", "メガカイリューex")
    """
    # 패턴: "숫자/숫자 레어도 카드명"
    match = re.match(r'(\d{3})/\d+\s+([A-Z]+)\s+(.+)', alt_text)
    if match:
        card_number = match.group(1)  # 250
        rarity = match.group(2)        # MUR
        card_name = match.group(3)     # メガカイリューex
        return card_number, rarity, card_name
    
    # 레어도 없는 경우: "250/193 メガカイリューex"
    match = re.match(r'(\d{3})/\d+\s+(.+)', alt_text)
    if match:
        card_number = match.group(1)
        card_name = match.group(2)
        return card_number, "", card_name
    
    return "", "", ""


def map_rarity_to_korean(jp_rarity: str) -> str:
    """일본 레어도를 한국 레어도로 매핑"""
    rarity_map = {
        'MUR': 'MUR',
        'UR': 'UR',
        'SSR': 'SSR',
        'SAR': 'SAR',
        'SR': 'SR',
        'HR': 'HR',
        'CSR': 'CSR',
        'CHR': 'CHR',
        'AR': 'AR',
        'BWR': 'BWR',
        'RRR': 'RRR',
        'RR': 'RR',
        'R': 'R',
        'U': 'U',
        'C': 'C',
    }
    return rarity_map.get(jp_rarity.upper(), 'C')


def extract_mirror_type(card_name: str) -> str:
    """
    미러 타입 추출
    - ホップのウールー(エネルギーマーク柄/ミラー仕様) → エネルギーマーク柄
    - ホップのウールー(ボール柄/ミラー仕様) → ボール柄
    - キリキザン(モンスターボール柄/ミラー仕様) → モンスターボール柄
    - キリキザン(マスターボール柄/ミラー仕様) → マスターボール柄
    """
    # (타입/ミラー仕様) 패턴에서 타입 추출
    match = re.search(r'\((.+?)(?:/ミラー仕様|/ミ)\)', card_name)
    if match:
        return match.group(1)
    
    # (ミラー仕様) 만 있는 경우
    if 'ミラー仕様' in card_name or 'ミラー' in card_name:
        return "基本ミラー"
    
    return ""


def generate_japan_product_code(expansion_code: str, card_number: str, is_mirror: bool = False, mirror_type: str = "") -> str:
    """
    일본판 상품코드 생성
    M2a + 250 → PKM-M2a-250-J
    미러 (기본): PKM-M2a-250-J-M
    미러 (에너지마크): PKM-M2a-250-J-M-ENERGY
    미러 (볼): PKM-M2a-250-J-M-BALL
    미러 (몬스터볼): PKM-M2a-250-J-M-MONSTERBALL
    미러 (마스터볼): PKM-M2a-250-J-M-MASTERBALL
    """
    # PKM-J- 대신 PKM-로 시작
    product_code = f"PKM-{expansion_code}-{card_number}-J"
    
    if is_mirror:
        product_code += "-M"
        
        # 미러 타입별 추가 코드
        if mirror_type:
            # 에너지마크
            if 'エネルギー' in mirror_type or 'エネルギーマーク' in mirror_type:
                product_code += "-ENERGY"
            # 볼
            elif 'ボール柄' in mirror_type and 'モンスター' not in mirror_type and 'マスター' not in mirror_type:
                product_code += "-BALL"
            # 몬스터볼
            elif 'モンスターボール' in mirror_type:
                product_code += "-MONSTERBALL"
            # 마스터볼
            elif 'マスターボール' in mirror_type:
                product_code += "-MASTERBALL"
            # 기본 미러
            elif '基本' in mirror_type or mirror_type == "基本ミラー":
                product_code += "-BASIC"
            else:
                # 기타 미러 타입은 해시로 구분
                import hashlib
                type_hash = hashlib.md5(mirror_type.encode()).hexdigest()[:4].upper()
                product_code += f"-{type_hash}"
    
    return product_code


def is_mirror_card(alt_text: str, card_name: str) -> bool:
    """
    미러 카드 여부 확인
    - ミラー 키워드
    - 柄/ミラー仕様 패턴
    - 柄/ミ 패턴 (짧은 표기)
    """
    mirror_keywords = ['ミラー', 'mirror', 'MIRROR']
    mirror_patterns = ['/ミラー仕様', '/ミ']
    
    # 키워드 확인
    if any(keyword in alt_text or keyword in card_name for keyword in mirror_keywords):
        return True
    
    # 패턴 확인
    if any(pattern in card_name for pattern in mirror_patterns):
        return True
    
    return False


def crawl_yuyu_tei_expansion(expansion_code: str, url_code: str):
    """
    유유테이에서 특정 확장팩의 카드 크롤링
    
    Args:
        expansion_code: 확장팩 코드 (예: 'M2a')
        url_code: URL 코드 (예: 'm02a')
    """
    print("\n" + "=" * 80)
    print(f"🗾 일본판 카드 크롤링 시작: {expansion_code}")
    print("=" * 80 + "\n")
    
    # URL 생성
    base_url = f"https://yuyu-tei.jp/sell/poc/s/{url_code}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        print(f"🔍 크롤링 URL: {base_url}")
        response = requests.get(base_url, headers=headers, timeout=30)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            print(f"❌ HTTP 오류: {response.status_code}")
            return
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. 확장팩명 추출
        expansion_name = extract_expansion_name(soup)
        
        if not expansion_name:
            print("❌ 확장팩명을 찾을 수 없습니다.")
            return
        
        print(f"📦 확장팩명: {expansion_name}")
        
        # 확장팩 생성 또는 가져오기
        expansion, created = JapanExpansion.objects.get_or_create(
            code=expansion_code,
            defaults={'name': expansion_name}
        )
        
        if created:
            print(f"✅ 새로운 확장팩 생성: {expansion.name}\n")
        else:
            # 기존 확장팩명 업데이트
            if expansion.name != expansion_name:
                expansion.name = expansion_name
                expansion.save()
                print(f"🔄 확장팩명 업데이트: {expansion.name}\n")
            else:
                print(f"📦 기존 확장팩 사용: {expansion.name}\n")
        
        # 2. 카드 정보 추출
        card_products = soup.select('.card-product')
        
        if not card_products:
            print("❌ 카드를 찾을 수 없습니다.")
            return
        
        print(f"📊 발견된 카드: {len(card_products)}개\n")
        
        total_cards = 0
        new_cards = 0
        updated_cards = 0
        
        for idx, card_elem in enumerate(card_products, 1):
            try:
                # 이미지 태그 찾기
                img_elem = card_elem.select_one('img.card')
                
                if not img_elem:
                    print(f"  ⚠️  [{idx}] 이미지 없음")
                    continue
                
                # 이미지 URL
                image_url = img_elem.get('src', '')
                
                # alt 텍스트에서 정보 추출
                alt_text = img_elem.get('alt', '')
                card_number, jp_rarity, jp_card_name = extract_card_number_from_alt(alt_text)
                
                if not card_number or not jp_card_name:
                    print(f"  ⚠️  [{idx}] 카드 정보 추출 실패: {alt_text}")
                    continue
                
                # 레어도 매핑
                rarity = map_rarity_to_korean(jp_rarity) if jp_rarity else 'C'
                
                # ★★★ 미러 여부 및 타입 추출 (추가!) ★★★
                is_mirror = is_mirror_card(alt_text, jp_card_name)
                mirror_type = extract_mirror_type(jp_card_name) if is_mirror else ""
                
                # ★★★ 상품코드 생성 (mirror_type 파라미터 추가!) ★★★
                shop_product_code = generate_japan_product_code(expansion_code, card_number, is_mirror, mirror_type)
                
                # ★★★ DB 저장 (mirror_type 필드 추가!) ★★★
                card_obj, card_created = JapanCard.objects.update_or_create(
                    shop_product_code=shop_product_code,
                    defaults={
                        'expansion': expansion,
                        'card_number': card_number,
                        'name': jp_card_name,
                        'rarity': rarity,
                        'is_mirror': is_mirror,
                        'mirror_type': mirror_type,  # 추가!
                        'image_url': image_url,
                    }
                )
                
                total_cards += 1
                mirror_tag = f" [미러:{mirror_type}]" if is_mirror and mirror_type else (" [미러]" if is_mirror else "")
                
                if card_created:
                    new_cards += 1
                    print(f"  ✅ 신규 [{idx}]: {jp_card_name} ({card_number}) - {rarity}{mirror_tag}")
                else:
                    updated_cards += 1
                    print(f"  🔄 업데이트 [{idx}]: {jp_card_name} ({card_number}) - {rarity}{mirror_tag}")
                
            except Exception as e:
                print(f"  ❌ 카드 처리 오류 [{idx}]: {e}")
                continue
        
        # 결과 출력
        print("\n" + "=" * 80)
        print(f"📊 크롤링 완료: {expansion_name} ({expansion_code})")
        print("=" * 80)
        print(f"✅ 신규 카드: {new_cards}개")
        print(f"🔄 업데이트: {updated_cards}개")
        print(f"📝 총 처리: {total_cards}개")
        print()
        
    except requests.exceptions.RequestException as e:
        print(f"❌ 네트워크 오류: {e}")
    except Exception as e:
        print(f"❌ 예외 발생: {e}")
        import traceback
        traceback.print_exc()


def crawl_all_japan_expansions():
    """모든 일본판 확장팩 크롤링"""
    print("\n" + "=" * 80)
    print("🗾 일본판 카드 전체 크롤링 시작")
    print("=" * 80)
    
    total_new = 0
    total_updated = 0
    
    for expansion in JAPAN_EXPANSIONS:
        try:
            before_count = JapanCard.objects.filter(expansion__code=expansion['code']).count()
            
            crawl_yuyu_tei_expansion(
                expansion['code'],
                expansion['url_code']
            )
            
            after_count = JapanCard.objects.filter(expansion__code=expansion['code']).count()
            expansion_new = after_count - before_count
            
            total_new += expansion_new if expansion_new > 0 else 0
            
            time.sleep(2)  # 서버 부하 방지
            
        except Exception as e:
            print(f"❌ 확장팩 '{expansion['code']}' 크롤링 실패: {e}")
            continue
    
    # 최종 결과
    print("\n" + "=" * 80)
    print("📊 전체 크롤링 완료")
    print("=" * 80)
    print(f"✅ 총 신규 카드: {total_new}개")
    print(f"📦 총 확장팩: {len(JAPAN_EXPANSIONS)}개")
    print(f"🗂️  총 카드 수: {JapanCard.objects.count()}개")


if __name__ == '__main__':
    import sys
    
    print("\n🗾 포켓몬 일본판 카드 크롤링 도구")
    print("=" * 80)
    print("\n선택하세요:")
    print("  1. 모든 확장팩 크롤링 (총 28개)")
    print("  2. 특정 확장팩만 크롤링")
    print("  3. 종료")
    
    choice = input("\n선택 (1/2/3): ").strip()
    
    if choice == '1':
        confirm = input(f"⚠️  모든 확장팩 {len(JAPAN_EXPANSIONS)}개를 크롤링하시겠습니까? (yes/no): ")
        if confirm.lower() == 'yes':
            crawl_all_japan_expansions()
    
    elif choice == '2':
        print("\n사용 가능한 확장팩:")
        for idx, exp in enumerate(JAPAN_EXPANSIONS, 1):
            print(f"  {idx:2d}. {exp['code']:6s} - URL: {exp['url_code']}")
        
        exp_num = int(input("\n확장팩 번호 선택 (1-28): ").strip()) - 1
        
        if 0 <= exp_num < len(JAPAN_EXPANSIONS):
            exp = JAPAN_EXPANSIONS[exp_num]
            crawl_yuyu_tei_expansion(exp['code'], exp['url_code'])
        else:
            print("❌ 잘못된 번호입니다.")
    
    elif choice == '3':
        print("종료합니다.")
    
    else:
        print("❌ 잘못된 선택입니다.")