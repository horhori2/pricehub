# save_cards_to_db.py
import os
import django
import requests
from bs4 import BeautifulSoup

# Django 설정 로드
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from pricehub.models import Expansion, Card

# 확장팩 정보 딕셔너리
EXPANSION_INFO = {
    '2020002': {'code': 'S1W', 'name': '소드'},
    '2020003': {'code': 'S1H', 'name': '실드'},
    '2020004': {'code': 'S1A', 'name': 'VMAX라이징'},
    '2020005': {'code': 'S2', 'name': '반역크래시'},
    '2020010': {'code': 'S2A', 'name': '폭염워커'},
    '2020011': {'code': 'S3', 'name': '무한존'},
    '2020012': {'code': 'S3A', 'name': '전설의고동'},
    '2020014': {'code': 'S4', 'name': '앙천의볼트태클'},
    '2020016': {'code': 'S4A', 'name': '샤이니스타V'},
    '2021001': {'code': 'S5I', 'name': '일격마스터'},
    '2021002': {'code': 'S5R', 'name': '연격마스터'},
    '2021003': {'code': 'S5A', 'name': '쌍벽의파이터'},
    '2021004': {'code': 'S6H', 'name': '백은의랜스'},
    '2021005': {'code': 'S6K', 'name': '칠흑의가이스트'},
    '2021007': {'code': 'S6A', 'name': '이브이히어로즈'},
    '2021011': {'code': 'S7D', 'name': '마천퍼펙트'},
    '2021012': {'code': 'S7R', 'name': '창공스트림'},
    '2021015': {'code': 'S8A', 'name': '25주년애니버서리'},
    '2021018': {'code': 'S8', 'name': '퓨전아츠'},
    '2022001': {'code': 'S8B', 'name': 'VMAX클라이맥스'},
    '2022002': {'code': 'S9', 'name': '스타버스'},
    '2022004': {'code': 'S9A', 'name': '배틀리전'},
    '2022007': {'code': 'S10D', 'name': '타임게이저'},
    '2022008': {'code': 'S10P', 'name': '스페이스저글러'},
    '2022010': {'code': 'S10B', 'name': '포켓몬고'},
    '2022011': {'code': 'S10A', 'name': '다크판타즈마'},
    '2022014': {'code': 'S11', 'name': '로스트어비스'},
    '2022016': {'code': 'S11A', 'name': '백열의아르카나'},
    '2022017': {'code': 'S12', 'name': '패러다임트리거'},
    '2023001': {'code': 'S12A', 'name': 'VSTAR유니버스'},
    '2023006': {'code': 'SV1S', 'name': '스칼렛'},
    '2023007': {'code': 'SV1V', 'name': '바이올렛'},
    '2023010': {'code': 'SV1A', 'name': '트리플렛비트'},
    '2023011': {'code': 'SV2P', 'name': '스노해저드'},
    '2023012': {'code': 'SV2D', 'name': '클레이버스트'},
    '2023014': {'code': 'SV2A', 'name': '포켓몬카드151'},
    '2023015': {'code': 'SV3', 'name': '흑염의지배자'},
    '2023020': {'code': 'SV3A', 'name': '레이징서프'},
    '2023021': {'code': 'SV4K', 'name': '고대의포효'},
    '2023022': {'code': 'SV4M', 'name': '미래의일섬'},
    '2024001': {'code': 'SV4A', 'name': '샤이니트레저ex'},
    '2024004': {'code': 'SV5K', 'name': '와일드포스'},
    '2024005': {'code': 'SV5M', 'name': '사이버저지'},
    '2024007': {'code': 'SV5A', 'name': '크림슨헤이즈'},
    '2024008': {'code': 'SV6', 'name': '변환의가면'},
    '2024011': {'code': 'SV6A', 'name': '나이트원더러'},
    '2024012': {'code': 'SV7', 'name': '스텔라미라클'},
    '2024016': {'code': 'SV7A', 'name': '낙원드래고나'},
    '2024017': {'code': 'SV8', 'name': '초전브레이커'},
    '2024019': {'code': 'SV8A', 'name': '테라스탈페스타ex'},
    '2025001': {'code': 'SV9', 'name': '배틀파트너즈'},
    '2025005': {'code': 'SV9A', 'name': '열풍의아레나'},
    '2025006': {'code': 'SV10', 'name': '로켓단의영광'},
    '2025007': {'code': 'SV11B', 'name': '블랙볼트'},
    '2025008': {'code': 'SV11W', 'name': '화이트플레어'},
    '2025009': {'code': 'M1L', 'name': '메가브레이브'},
    '2025010': {'code': 'M1S', 'name': '메가심포니아'},
    '2025014': {'code': 'M2', 'name': '인페르노X'},
    '2025015': {'code': 'M2A', 'name': 'MEGA드림ex'},
    '2026002': {'code': 'M3', 'name': '니힐제로'},
    '2026003': {'code': 'M4', 'name': '닌자스피너'},
    '2026004': {'code': 'M5', 'name': '어비스아이'},

    # 스타터
    '2025004': {'code': 'SVOM', 'name': '마리의모르페코&오롱털'},
    '2026001': {'code': 'MC', 'name': 'MEGA스타트덱100'},
}

def generate_shop_product_code(expansion_code, card_number, rarity):
    """
    네이버상품코드 생성
    형식: PKM-{확장팩코드}-{카드번호}-K[-V1/V2/V3]
    
    V1: 몬스터볼 레어도
    V2: 마스터볼 레어도
    V3: 미러 레어도
    """
    base_code = f'PKM-{expansion_code}-{card_number}-K'
    
    if rarity == '몬스터볼':
        return f'{base_code}-V1'
    elif rarity == '마스터볼':
        return f'{base_code}-V2'
    elif rarity == '미러':
        return f'{base_code}-V3'
    else:
        return base_code

def get_or_create_expansion(expansion_code):
    """확장팩 가져오기 또는 생성"""
    exp_info = EXPANSION_INFO.get(expansion_code)
    if not exp_info:
        print(f'경고: 확장팩 정보 없음 - {expansion_code}')
        return None
    
    expansion, created = Expansion.objects.get_or_create(
        code=exp_info['code'],
        defaults={
            'name': exp_info['name'],
            'image_url': ''
        }
    )
    
    if created:
        print(f'확장팩 생성: {expansion.name}')
    
    return expansion

def crawl_and_save_cards(expansion_code):
    """카드 크롤링 및 DB 저장"""
    base_url = f'https://pokemoncard.co.kr/cards/detail/BS{expansion_code}'
    expansion = get_or_create_expansion(expansion_code)
    
    if not expansion:
        return
    
    saved_count = 0
    
    for i in range(1, 1000):
        code = f'{i:03}'
        url = f'{base_url}{code}'
        
        try:
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # "없는 카드정보입니다." 확인
            if not soup.select_one('span.p_num'):
                print(f'종료: {url} → 없는 카드입니다.')
                break
            
            # 카드번호 추출
            p_num_span = soup.select_one('span.p_num')
            if p_num_span:
                card_num_text = p_num_span.get_text().split()[0]
                card_num = card_num_text.split('/')[0]
            else:
                card_num = ''
            
            # 카드명 추출
            card_name_tag = soup.select_one('span.card-hp.title')
            card_name = card_name_tag.get_text(strip=True) if card_name_tag else ''
            
            # 레어도 추출
            rarity_tag = soup.select_one('#no_wrap_by_admin')
            rarity = rarity_tag.get_text(strip=True) if rarity_tag else 'C'
            
            # 이미지 URL 추출
            image_tag = soup.select_one('img.feature_image')
            image_url = image_tag['src'] if image_tag and image_tag.has_attr('src') else ''
            
            # 미러 카드 체크
            is_mirror = '_m.' in image_url or '_m?' in image_url
            
            if is_mirror:
                rarity = '미러'
                print(f'🔍 미러 카드 감지: {image_url}')
            
            # shop_product_code 생성
            shop_product_code = generate_shop_product_code(expansion.code, card_num, rarity)
            
            # DB에 카드 저장
            card, created = Card.objects.update_or_create(
                shop_product_code=shop_product_code,
                defaults={
                    'expansion': expansion,
                    'card_number': card_num,
                    'name': card_name,
                    'rarity': rarity if rarity in dict(Card.RARITY_CHOICES) else 'C',
                    'image_url': image_url
                }
            )
            
            status = '생성' if created else '업데이트'
            mirror_indicator = ' [미러]' if is_mirror else ''
            print(f'[{status}] {shop_product_code}: {card_name} ({card_num}, {rarity}){mirror_indicator}')
            saved_count += 1
            
        except Exception as e:
            print(f'오류 발생 ({url}): {e}')
            continue
    
    print(f'\n=== 완료: {expansion.name} - 총 {saved_count}장 저장 ===\n')

def display_expansions():
    """확장팩 목록 출력"""
    print('\n' + '='*80)
    print('포켓몬 카드 확장팩 목록')
    print('='*80)
    
    # 확장팩을 코드별로 정렬
    sorted_expansions = sorted(EXPANSION_INFO.items())
    
    for idx, (code, info) in enumerate(sorted_expansions, 1):
        print(f'{idx:2d}. [{info["code"]:6s}] {info["name"]:20s} (내부코드: {code})')
    
    print('='*80)

def select_expansion_mode():
    """수집 모드 선택"""
    print('\n[수집 모드 선택]')
    print('1. 전체 확장팩 수집')
    print('2. 특정 확장팩 선택 (번호)')
    print('3. 특정 확장팩 선택 (코드)')
    print('4. 최신 확장팩만 수집 (최근 5개)')
    print('5. 종료')
    
    choice = input('\n선택 (1-5): ').strip()
    return choice

def collect_all_expansions():
    """전체 확장팩 수집"""
    print('\n전체 확장팩 수집을 시작합니다...\n')
    
    for exp_code in EXPANSION_INFO.keys():
        print(f'\n{"="*80}')
        print(f'크롤링 시작: {EXPANSION_INFO[exp_code]["name"]} ({EXPANSION_INFO[exp_code]["code"]})')
        print(f'{"="*80}')
        crawl_and_save_cards(exp_code)

def collect_by_numbers():
    """번호로 확장팩 선택"""
    display_expansions()
    
    print('\n수집할 확장팩 번호를 입력하세요.')
    print('예) 단일: 1  /  여러개: 1,5,10  /  범위: 1-5')
    selection = input('입력: ').strip()
    
    # 확장팩 리스트
    expansion_list = list(EXPANSION_INFO.keys())
    selected_codes = []
    
    # 범위 처리 (1-5)
    if '-' in selection:
        try:
            start, end = map(int, selection.split('-'))
            selected_codes = [expansion_list[i-1] for i in range(start, end+1) if 0 < i <= len(expansion_list)]
        except:
            print('올바른 범위를 입력하세요.')
            return
    
    # 쉼표로 구분된 번호들
    elif ',' in selection:
        try:
            numbers = [int(n.strip()) for n in selection.split(',')]
            selected_codes = [expansion_list[i-1] for i in numbers if 0 < i <= len(expansion_list)]
        except:
            print('올바른 번호를 입력하세요.')
            return
    
    # 단일 번호
    else:
        try:
            num = int(selection)
            if 0 < num <= len(expansion_list):
                selected_codes = [expansion_list[num-1]]
            else:
                print(f'1-{len(expansion_list)} 사이의 번호를 입력하세요.')
                return
        except:
            print('올바른 번호를 입력하세요.')
            return
    
    if not selected_codes:
        print('선택된 확장팩이 없습니다.')
        return
    
    # 선택 확인
    print('\n선택된 확장팩:')
    for code in selected_codes:
        print(f'  - {EXPANSION_INFO[code]["name"]} ({EXPANSION_INFO[code]["code"]})')
    
    confirm = input('\n수집을 시작하시겠습니까? (y/n): ').strip().lower()
    if confirm == 'y':
        for exp_code in selected_codes:
            print(f'\n{"="*80}')
            print(f'크롤링 시작: {EXPANSION_INFO[exp_code]["name"]} ({EXPANSION_INFO[exp_code]["code"]})')
            print(f'{"="*80}')
            crawl_and_save_cards(exp_code)

def collect_by_code():
    """코드로 확장팩 선택"""
    display_expansions()
    
    print('\n수집할 확장팩의 코드(S1W, SV1S 등) 또는 내부코드(2020002 등)를 입력하세요.')
    print('예) 단일: S1W  /  여러개: S1W,SV1S,M4')
    selection = input('입력: ').strip()
    
    codes = [c.strip().upper() for c in selection.split(',')]
    selected_codes = []
    
    for code in codes:
        # 확장팩 코드로 찾기 (S1W, SV1S 등)
        found = False
        for internal_code, info in EXPANSION_INFO.items():
            if info['code'].upper() == code or internal_code == code:
                selected_codes.append(internal_code)
                found = True
                break
        
        if not found:
            print(f'경고: "{code}" 확장팩을 찾을 수 없습니다.')
    
    if not selected_codes:
        print('선택된 확장팩이 없습니다.')
        return
    
    # 선택 확인
    print('\n선택된 확장팩:')
    for code in selected_codes:
        print(f'  - {EXPANSION_INFO[code]["name"]} ({EXPANSION_INFO[code]["code"]})')
    
    confirm = input('\n수집을 시작하시겠습니까? (y/n): ').strip().lower()
    if confirm == 'y':
        for exp_code in selected_codes:
            print(f'\n{"="*80}')
            print(f'크롤링 시작: {EXPANSION_INFO[exp_code]["name"]} ({EXPANSION_INFO[exp_code]["code"]})')
            print(f'{"="*80}')
            crawl_and_save_cards(exp_code)

def collect_recent_expansions():
    """최신 5개 확장팩 수집"""
    recent_codes = list(EXPANSION_INFO.keys())[-5:]
    
    print('\n최신 확장팩 5개:')
    for code in recent_codes:
        print(f'  - {EXPANSION_INFO[code]["name"]} ({EXPANSION_INFO[code]["code"]})')
    
    confirm = input('\n수집을 시작하시겠습니까? (y/n): ').strip().lower()
    if confirm == 'y':
        for exp_code in recent_codes:
            print(f'\n{"="*80}')
            print(f'크롤링 시작: {EXPANSION_INFO[exp_code]["name"]} ({EXPANSION_INFO[exp_code]["code"]})')
            print(f'{"="*80}')
            crawl_and_save_cards(exp_code)

def main():
    """메인 실행 함수"""
    while True:
        mode = select_expansion_mode()
        
        if mode == '1':
            collect_all_expansions()
            break
        elif mode == '2':
            collect_by_numbers()
            break
        elif mode == '3':
            collect_by_code()
            break
        elif mode == '4':
            collect_recent_expansions()
            break
        elif mode == '5':
            print('종료합니다.')
            break
        else:
            print('올바른 번호를 선택하세요.')

if __name__ == '__main__':
    main()