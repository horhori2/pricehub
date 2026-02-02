# save_cards_to_db.py
import os
import django
import requests
from bs4 import BeautifulSoup

# Django 설정 로드
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
    '2025015': {'code': 'M2A', 'name': 'MEGA드림ex'}
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
        return f'{base_code}-V3'  # 미러는 V3
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
            'image_url': ''  # admin에서 나중에 추가
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
            
            # 카드번호 추출 (001/080 -> 001)
            p_num_span = soup.select_one('span.p_num')
            if p_num_span:
                card_num_text = p_num_span.get_text().split()[0]  # "001/080"
                card_num = card_num_text.split('/')[0]  # "001"
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
            
            # 미러 카드 체크 (이미지 URL에 _m이 포함되어 있는지 확인)
            is_mirror = '_m.' in image_url or '_m?' in image_url
            
            # 미러 카드인 경우 레어도를 "미러"로 변경
            if is_mirror:
                rarity = '미러'
                print(f'🔍 미러 카드 감지: {image_url}')
            
            # shop_product_code 생성
            shop_product_code = generate_shop_product_code(expansion.code, card_num, rarity)
            
            # DB에 카드 저장 (중복 시 업데이트)
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

if __name__ == '__main__':
    # 크롤링할 확장팩 코드 입력
    target_expansion = '2025015' 
    
    print(f'크롤링 시작: {EXPANSION_INFO[target_expansion]["name"]}')
    crawl_and_save_cards(target_expansion)
    
    # 여러 확장팩을 한번에 크롤링하려면:
    # expansion_list = ['2020002',
    # '2020003',
    # '2020004',
    # '2020005',
    # '2020010',
    # '2020011',
    # '2020012',
    # '2020014',
    # '2020016',
    # '2021001',
    # '2021002',
    # '2021003',
    # '2021004',
    # '2021005',
    # '2021007',
    # '2021011',
    # '2021012',
    # '2021015',
    # '2021018',
    # '2022001',
    # '2022002',
    # '2022004',
    # '2022007',
    # '2022008',
    # '2022010',
    # '2022011',
    # '2022014',
    # '2022016',
    # '2022017',
    # '2023001',
    # '2023006',
    # '2023007',
    # '2023010',
    # '2023011',
    # '2023012',
    # '2023014',
    # '2023015',
    # '2023020',
    # '2023021',
    # '2023022',
    # '2024001',
    # '2024004',
    # '2024005',
    # '2024007',
    # '2024008',
    # '2024011',
    # '2024012',
    # '2024016',
    # '2024017',
    # '2024019',
    # '2025001',
    # '2025005',
    # '2025006',
    # '2025007',
    # '2025008',
    # '2025009',
    # '2025010',
    # '2025014',
    # '2025015',
    # ]

    # for exp_code in expansion_list:
    #     print(f'\n크롤링 시작: {EXPANSION_INFO[exp_code]["name"]}')
    #     crawl_and_save_cards(exp_code)