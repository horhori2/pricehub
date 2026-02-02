# save_onepiece_cards_to_db.py
import os
import django
import requests
from bs4 import BeautifulSoup
import re
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from pricehub.models import OnePieceExpansion, OnePieceCard

# ==================== 원피스 시리즈 목록 ====================
SERIES_LIST = [
    {'code': 'OPK-10', 'name': '[OPK-10] 부스터 팩 왕족의 혈통'},
    {'code': 'OPK-09', 'name': '[OPK-09] 부스터 팩 새로운 황제'},
    {'code': 'OPK-08', 'name': '[OPK-08] 부스터 팩 두 전설'},
    {'code': 'OPK-07', 'name': '[OPK-07] 부스터 팩 500년 후의 미래'},
    {'code': 'EBK-01', 'name': '[EBK-01] 엑스트라 부스터 팩 메모리얼 컬렉션'},
    {'code': 'OPK-06', 'name': '[OPK-06] 부스터 팩 쌍벽의 패자'},
    {'code': 'OPK-05', 'name': '[OPK-05] 부스터 팩 신시대의 주역'},
    {'code': 'OPK-04', 'name': '[OPK-04] 부스터 팩 모략의 왕국'},
    {'code': 'OPK-03', 'name': '[OPK-03] 부스터 팩 강대한 적'},
    {'code': 'OPK-02', 'name': '[OPK-02] 부스터 팩 정상결전'},
    {'code': 'OPK-01', 'name': '[OPK-01] 부스터 팩 ROMANCE DAWN'},
    {'code': 'PROMO', 'name': '【프로모션】'},
]

# ==================== 유틸리티 함수 ====================

def extract_text_only(element):
    """첫 텍스트만 가져오기"""
    if element:
        text = element.find(text=True)
        return text.strip() if text else ""
    return ""


def modify_rarity(card_number: str, rarity: str) -> str:
    """
    카드 번호에 따라 레어도 접두어 조정
    _P1 또는 _p1 → P-{rarity}
    _P2 이상 → SP-{rarity}
    """
    # 대소문자 구분 없이 매칭
    match = re.search(r"_[Pp](\d+)", card_number)
    if match:
        p_num = int(match.group(1))
        if p_num == 1:
            return f"P-{rarity}"
        else:
            return f"SP-{rarity}"
    return rarity


def extract_card_code(card_number: str) -> str:
    """
    카드 코드 추출 (OP06-021_P1 → OP06-021, ST03-014_p1 → ST03-014)
    대소문자 구분 없이 처리
    """
    return re.sub(r"_[Pp]\d+", "", card_number, flags=re.IGNORECASE)


def generate_shop_product_code(card_number: str) -> str:
    """
    원피스 상품코드 생성
    OP10-046 → OPC-OP10-046-K
    OP10-046_P1 → OPC-OP10-046-K-V1
    OP10-046_p1 → OPC-OP10-046-K-V1 (소문자도 지원)
    ST03-014_p1 → OPC-ST03-014-K-V1
    """
    # 카드번호를 대문자로 변환 (소문자 _p1도 처리)
    card_number_upper = card_number.upper()
    
    # 기본 카드번호 추출 (_P 제거)
    base_code = re.sub(r"_P\d+", "", card_number_upper)
    
    # 상품코드 생성 (OPC- 접두어)
    product_code = f"OPC-{base_code}-K"
    
    # _P1, _P2, _p1, _p2 등이 있으면 -V1, -V2로 변환
    match = re.search(r"_P(\d+)", card_number_upper)
    if match:
        p_num = match.group(1)
        product_code += f"-V{p_num}"
    
    return product_code


def crawl_onepiece_series(series_code: str, series_name: str):
    """
    특정 시리즈의 원피스 카드 크롤링 및 DB 저장
    
    Args:
        series_code: 시리즈 코드 (예: 'OPK-10')
        series_name: 시리즈 전체명 (예: '[OPK-10] 부스터 팩 왕족의 혈통')
    """
    print("\n" + "=" * 80)
    print(f"🏴‍☠️ 원피스 카드 크롤링 시작: {series_name}")
    print("=" * 80 + "\n")
    
    # 확장팩 생성 또는 가져오기
    expansion, created = OnePieceExpansion.objects.get_or_create(
        code=series_code,
        defaults={
            'name': series_name.replace(f'[{series_code}] ', ''),  # 접두어 제거
        }
    )
    
    if created:
        print(f"✅ 새로운 확장팩 생성: {expansion.name}")
    else:
        print(f"📦 기존 확장팩 사용: {expansion.name}")
    
    base_url = "https://onepiece-cardgame.kr/cardlist.do"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    page = 0
    total_cards = 0
    new_cards = 0
    updated_cards = 0
    
    while True:
        params = {
            "page": page,
            "size": 20,
            "freewords": "",
            "categories": "",
            "illustrations": "",
            "colors": "",
            "series": series_name
        }
        
        print(f"📄 페이지 {page} 요청 중...")
        
        try:
            response = requests.get(base_url, params=params, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")
            
            card_list_section = soup.select_one(".card_sch_list")
            card_buttons = card_list_section.select("button.item") if card_list_section else []
            
            if not card_buttons:
                print("✅ 더 이상 카드가 없습니다.")
                break
            
            for card_elem in card_buttons:
                try:
                    # 카드 정보 추출
                    card_number = extract_text_only(card_elem.select_one(".cardNumber"))
                    card_name = extract_text_only(card_elem.select_one(".cardName"))
                    rarity = extract_text_only(card_elem.select_one(".rarity"))
                    card_type = extract_text_only(card_elem.select_one(".cardType"))
                    
                    if not card_number or not card_name:
                        continue
                    
                    # 레어도 조정 (P-, SP- 접두어)
                    adjusted_rarity = modify_rarity(card_number, rarity)
                    
                    # 망가(슈퍼 패러렐) 여부 판단
                    # SP- 로 시작하고 SP-SP가 아닌 경우 망가로 판단
                    is_manga = adjusted_rarity.startswith('SP-') and adjusted_rarity != 'SP-SP'
                    
                    # 상품코드 생성
                    shop_product_code = generate_shop_product_code(card_number)
                    
                    # DB 저장
                    card_obj, card_created = OnePieceCard.objects.update_or_create(
                        shop_product_code=shop_product_code,
                        defaults={
                            'expansion': expansion,
                            'card_number': card_number,
                            'name': card_name,
                            'rarity': adjusted_rarity if adjusted_rarity in dict(OnePieceCard.RARITY_CHOICES) else 'C',
                            'is_manga': is_manga,  # 망가 여부 저장
                            'image_url': '',
                        }
                    )
                    
                    total_cards += 1
                    manga_indicator = " [망가]" if is_manga else ""
                    if card_created:
                        new_cards += 1
                        print(f"  ✅ 신규: {card_number} ({shop_product_code}) - {card_name} ({adjusted_rarity}){manga_indicator}")
                    else:
                        updated_cards += 1
                        print(f"  🔄 업데이트: {card_number} ({shop_product_code}) - {card_name} ({adjusted_rarity}){manga_indicator}")
                    
                except Exception as e:
                    print(f"  ❌ 카드 처리 오류: {e}")
                    continue
            
            page += 1
            time.sleep(0.5)  # API 부하 방지
            
        except Exception as e:
            print(f"❌ 페이지 요청 오류: {e}")
            break
    
    # 결과 출력
    print("\n" + "=" * 80)
    print(f"📊 크롤링 완료: {series_name}")
    print("=" * 80)
    print(f"✅ 신규 카드: {new_cards}개")
    print(f"🔄 업데이트: {updated_cards}개")
    print(f"📝 총 처리: {total_cards}개")
    print()


def crawl_all_series():
    """모든 시리즈 크롤링"""
    print("\n" + "=" * 80)
    print("🏴‍☠️ 원피스 카드 전체 크롤링 시작")
    print("=" * 80)
    
    total_new = 0
    total_updated = 0
    
    for series in SERIES_LIST:
        try:
            before_count = OnePieceCard.objects.filter(expansion__code=series['code']).count()
            
            crawl_onepiece_series(series['code'], series['name'])
            
            after_count = OnePieceCard.objects.filter(expansion__code=series['code']).count()
            series_new = after_count - before_count
            
            total_new += series_new if series_new > 0 else 0
            
            time.sleep(1)  # 시리즈 간 대기
            
        except Exception as e:
            print(f"❌ 시리즈 '{series['code']}' 크롤링 실패: {e}")
            continue
    
    # 최종 결과
    print("\n" + "=" * 80)
    print("📊 전체 크롤링 완료")
    print("=" * 80)
    print(f"✅ 총 신규 카드: {total_new}개")
    print(f"📦 총 확장팩: {len(SERIES_LIST)}개")
    print(f"🗂️  총 카드 수: {OnePieceCard.objects.count()}개")


if __name__ == '__main__':
    import sys
    
    print("\n🏴‍☠️ 원피스 카드 크롤링 도구")
    print("=" * 80)
    print("\n선택하세요:")
    print("  1. 모든 시리즈 크롤링")
    print("  2. 특정 시리즈만 크롤링")
    print("  3. 종료")
    
    choice = input("\n선택 (1/2/3): ").strip()
    
    if choice == '1':
        confirm = input("모든 시리즈를 크롤링하시겠습니까? (yes/no): ")
        if confirm.lower() == 'yes':
            crawl_all_series()
    elif choice == '2':
        print("\n사용 가능한 시리즈:")
        for idx, series in enumerate(SERIES_LIST, 1):
            print(f"  {idx}. {series['name']}")
        
        series_num = int(input("\n시리즈 번호 선택: ").strip()) - 1
        
        if 0 <= series_num < len(SERIES_LIST):
            series = SERIES_LIST[series_num]
            crawl_onepiece_series(series['code'], series['name'])
        else:
            print("❌ 잘못된 번호입니다.")
    elif choice == '3':
        print("종료합니다.")
    else:
        print("❌ 잘못된 선택입니다.")