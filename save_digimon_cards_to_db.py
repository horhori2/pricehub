# save_digimon_cards_to_db.py
import os
import django
import requests
from bs4 import BeautifulSoup
import time
import re
from collections import defaultdict

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from pricehub.models import DigimonExpansion, DigimonCard

EXPANSION_INFO = {
    1078: {'code': 'BTK-1.0', 'name': '스페셜 부스터 버전 1.0'},
    2300: {'code': 'BTK-1.5', 'name': '스페셜 부스터 버전 1.5'},
    4108: {'code': 'BTK-04', 'name': '그레이트 레전드'},
    5192: {'code': 'BTK-05', 'name': '배틀 오브 오메가'},
    6128: {'code': 'BTK-06', 'name': '더블 다이아몬드'},
    7467: {'code': 'EXK-01', 'name': '클래식 컬렉션'},
    8585: {'code': 'BTK-07', 'name': '넥스트 어드벤처'},
    10406: {'code': 'BTK-08', 'name': '뉴 히어로'},
    11549: {'code': 'EXK-02', 'name': '디지털 해저드'},
    12160: {'code': 'BTK-09', 'name': 'X레코드'},
    13687: {'code': 'BTK-10', 'name': '크로스 인카운터'},
    35770: {'code': 'EXK-03', 'name': '드래곤즈 로어'},
    36807: {'code': 'BTK-11', 'name': '디멘셔널 페이즈'},
    37672: {'code': 'BTK-12', 'name': '어크로스 타임'},
    38620: {'code': 'EXK-04', 'name': '얼터너티브 비잉'},
    39056: {'code': 'BTK-13', 'name': 'vs 로얄 나이츠'},
    39800: {'code': 'RBK-01', 'name': '라이징 윈드'},
    40497: {'code': 'BTK-14', 'name': 'BLAST ACE'},
    40815: {'code': 'EXK-05', 'name': '애니멀 콜로세움'},
    41534: {'code': 'BTK-15', 'name': '익시드 아포칼립스'},
    42178: {'code': 'BTK-16', 'name': 'BEGINNING OBSERVER'},
    42671: {'code': 'EXK-06', 'name': '인퍼널 어센션'},
    43359: {'code': 'BTK-17', 'name': '시크릿 크라이시스'},
    44257: {'code': 'EXK-07', 'name': '디지몬 리버레이터'},
    45019: {'code': 'BTK-18', 'name': '엘리멘트 석세서'},
    45777: {'code': 'BTK-19', 'name': '크로스 에볼루션'},
    46212: {'code': 'EXK-08', 'name': 'CHAIN OF LIBERATION'},
    46837: {'code': 'BTK-20', 'name': 'OVER THE X'},
    47744: {'code': 'BTK-21', 'name': 'WORLD CONVERGENCE'},
    48269: {'code': 'EXK-09', 'name': 'VERSUS MONSTERS'},
    488: {'code': 'PROMO', 'name': '프로모션 카드'},
}

BASE_URL = "https://digimoncard.co.kr"
CARD_LIST_URL = "https://digimoncard.co.kr/index.php?mid=cardlist&category={}&page={}"


def generate_shop_product_code(card_number, count, region='K'):
    """
    상품코드 생성: DGM-{카드번호}-{region}[-V{n}]
    한글판: region='K', 일본판: region='J'
    동일 카드번호 2번째부터 -V1, -V2, -V3 ... 순으로 부여
    """
    base = f'DGM-{card_number}-{region}'
    if count == 1:
        return base
    return f'{base}-V{count - 1}'


def get_or_create_expansion(category_id):
    info = EXPANSION_INFO.get(category_id)
    if not info:
        print(f'경고: 확장팩 정보 없음 - category_id={category_id}')
        return None

    expansion, created = DigimonExpansion.objects.get_or_create(
        code=info['code'],
        defaults={
            'name': info['name'],
            'category_id': category_id,
            'image_url': '',
        }
    )
    if created:
        print(f'확장팩 생성: {expansion.name} ({expansion.code})')
    return expansion


def crawl_and_save_cards(category_id):
    expansion = get_or_create_expansion(category_id)
    if not expansion:
        return

    info = EXPANSION_INFO[category_id]
    print(f'\n{"="*80}')
    print(f'크롤링 시작: {info["name"]} ({info["code"]})')
    print(f'{"="*80}')

    card_counter = defaultdict(int)
    saved_count = 0

    for page_num in range(1, 1000):
        url = CARD_LIST_URL.format(category_id, page_num)

        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                print(f'HTTP 오류 {response.status_code} - 중지')
                break

            soup = BeautifulSoup(response.text, 'html.parser')
            card_items = soup.select('li.image_lists_item')

            if not card_items:
                print(f'페이지 {page_num}: 카드 없음, 완료')
                break

            print(f'페이지 {page_num}: {len(card_items)}장 처리 중...')

            for item in card_items:
                card_name_tag = item.select_one('.card_name')
                if not card_name_tag:
                    continue

                card_name_tag_text = card_name_tag.get_text(strip=True)

                match = re.search(
                    r'((BT|EX|ST|RB|TM|DR|AC)\d{1,2}-\d{2,3}|P-\d{2,3}|PR-\d{2,3}|LM-\d{2,3}|token\w*)',
                    card_name_tag_text
                )
                if not match:
                    print(f'  카드번호 패턴 불일치: {card_name_tag_text}')
                    continue

                card_number = match.group(1)

                # 카드명 추출 (카드번호·레어도 제거)
                name_part = card_name_tag_text.replace(card_number, '', 1).strip()
                card_name = re.sub(r'^(SR|SEC|R|U|C|P|PR|L|DR|AC)\s*', '', name_part)

                # 카드 정보 추출
                card_info_tag = item.select_one('.cardinfo_head')
                contents = card_info_tag.contents if card_info_tag else []

                rarity_tag = contents[3] if len(contents) > 3 else None
                type_tag   = contents[5] if len(contents) > 5 else None
                level_tag  = contents[7] if len(contents) > 7 else None

                rarity    = rarity_tag.get_text(strip=True) if rarity_tag else ''
                card_type = type_tag.get_text(strip=True)   if type_tag   else ''

                # 패러렐/스페셜 텍스트 여부
                has_parallel_text = any(
                    ('페러렐' in c.get_text(strip=True) or '패러렐' in c.get_text(strip=True))
                    for c in contents if hasattr(c, 'get_text')
                )
                has_special_text = any(
                    '스페셜' in c.get_text(strip=True)
                    for c in contents if hasattr(c, 'get_text')
                )

                # 카드레벨 (테이머/옵션은 레벨 없음)
                if card_type in ['테이머', '옵션']:
                    card_level = ''
                else:
                    card_level = level_tag.get_text(strip=True) if level_tag else ''

                # 이미지 URL
                img_tag = item.select_one('div.card_img img')
                if not img_tag or not img_tag.get('src'):
                    continue
                img_src   = img_tag['src']
                image_url = BASE_URL + img_src if img_src.startswith('/') else img_src

                # 카운트 증가 (동일 카드번호 등장 횟수로 패러렐/희소/스페셜 구분)
                card_counter[card_number] += 1
                count       = card_counter[card_number]
                is_parallel = has_parallel_text or (count == 2)
                is_scarce   = (count == 3)
                is_special  = has_special_text or (count == 4)

                valid_rarities = {r[0] for r in DigimonCard.RARITY_CHOICES}

                # 기존 DB 코드와 충돌 시 다음 버전으로 이동 (기존 데이터 건드리지 않음)
                shop_product_code = generate_shop_product_code(card_number, count)
                suffix = count
                while DigimonCard.objects.filter(shop_product_code=shop_product_code).exists():
                    suffix += 1
                    shop_product_code = generate_shop_product_code(card_number, suffix)

                DigimonCard.objects.create(
                    shop_product_code=shop_product_code,
                    expansion=expansion,
                    card_number=card_number,
                    name=card_name,
                    rarity=rarity if rarity in valid_rarities else 'C',
                    card_type=card_type,
                    card_level=card_level,
                    is_parallel=is_parallel,
                    is_scarce=is_scarce,
                    is_special=is_special,
                    image_url=image_url,
                )

                tags    = (
                    (['패러렐'] if is_parallel else []) +
                    (['희소']   if is_scarce   else []) +
                    (['스페셜'] if is_special  else [])
                )
                tag_str = f' [{", ".join(tags)}]' if tags else ''
                print(f'  [생성] {shop_product_code}: {card_name} ({card_number}, {rarity}){tag_str}')
                saved_count += 1

            time.sleep(0.3)

        except Exception as e:
            print(f'오류 ({url}): {e}')
            continue

    print(f'\n=== 완료: {info["name"]} - 총 {saved_count}장 저장 ===\n')


def display_expansions():
    print('\n' + '='*80)
    print('디지몬 카드 확장팩 목록')
    print('='*80)
    for idx, (cat_id, info) in enumerate(EXPANSION_INFO.items(), 1):
        print(f'{idx:2d}. [{info["code"]:10s}] {info["name"]:30s} (category: {cat_id})')
    print('='*80)


def main():
    while True:
        print('\n[수집 모드 선택]')
        print('1. 전체 확장팩 수집')
        print('2. 특정 확장팩 선택 (번호)')
        print('3. 최신 확장팩만 수집 (최근 3개)')
        print('4. 종료')

        choice = input('\n선택 (1-4): ').strip()

        if choice == '1':
            print('\n전체 확장팩 수집을 시작합니다...')
            for cat_id in EXPANSION_INFO:
                crawl_and_save_cards(cat_id)
            break

        elif choice == '2':
            display_expansions()
            exp_list = list(EXPANSION_INFO.keys())
            print('\n번호 입력 (예: 1 / 1,3 / 1-5):')
            sel = input('입력: ').strip()

            selected = []
            if '-' in sel:
                try:
                    s, e = map(int, sel.split('-'))
                    selected = [exp_list[i-1] for i in range(s, e+1) if 0 < i <= len(exp_list)]
                except Exception:
                    print('올바른 범위를 입력하세요.')
                    continue
            elif ',' in sel:
                try:
                    nums = [int(n.strip()) for n in sel.split(',')]
                    selected = [exp_list[i-1] for i in nums if 0 < i <= len(exp_list)]
                except Exception:
                    print('올바른 번호를 입력하세요.')
                    continue
            else:
                try:
                    num = int(sel)
                    if 0 < num <= len(exp_list):
                        selected = [exp_list[num-1]]
                    else:
                        print(f'1-{len(exp_list)} 사이의 번호를 입력하세요.')
                        continue
                except Exception:
                    print('올바른 번호를 입력하세요.')
                    continue

            if not selected:
                print('선택된 확장팩이 없습니다.')
                continue

            print('\n선택된 확장팩:')
            for cat_id in selected:
                print(f'  - {EXPANSION_INFO[cat_id]["name"]} ({EXPANSION_INFO[cat_id]["code"]})')

            if input('\n수집을 시작하시겠습니까? (y/n): ').strip().lower() == 'y':
                for cat_id in selected:
                    crawl_and_save_cards(cat_id)
            break

        elif choice == '3':
            recent = list(EXPANSION_INFO.keys())[:3]
            print('\n최신 확장팩 3개:')
            for cat_id in recent:
                print(f'  - {EXPANSION_INFO[cat_id]["name"]} ({EXPANSION_INFO[cat_id]["code"]})')
            if input('\n수집을 시작하시겠습니까? (y/n): ').strip().lower() == 'y':
                for cat_id in recent:
                    crawl_and_save_cards(cat_id)
            break

        elif choice == '4':
            print('종료합니다.')
            break
        else:
            print('올바른 번호를 선택하세요.')


if __name__ == '__main__':
    main()
