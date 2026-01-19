# import_cards_from_excel.py
import os
import django
import openpyxl
import glob
import re

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from pricehub.models import Expansion, Card

# 확장팩 정보 매핑
EXPANSION_INFO = {
    'S7D': '마천퍼펙트',
    'S8B': 'Vmax클라이맥스',
    'SV1S': '스칼렛',
    'SV1V': '바이올렛',
    'SV1A': '트리플렛비트',
    'SV2P': '스노해저드',
    'SV2D': '클레이버스트',
    'SV2A': '포켓몬카드151',
    'SV3': '흑염의지배자',
    'SV3A': '레이징서프',
    'SV4K': '고대의포효',
    'SV4M': '미래의일섬',
    'SV4A': '샤이니트레저ex',
    'SV5K': '와일드포스',
    'SV5M': '사이버저지',
    'SV5A': '크림슨헤이즈',
    'SV6': '변환의가면',
    'SV6A': '나이트원더러',
    'SV7': '스텔라미라클',
    'SV7A': '낙원드래고나',
    'SV8': '초전브레이커',
    'SV8A': '테라스탈페스타ex',
    'SV9A': '배틀파트너즈',
    'SV9': '열풍의아레나',
    'SV10': '로켓단의영광',
    'SV11B': '블랙볼트',
    'SV11W': '화이트플레어',
    'M1L': '메가브레이브',
    'M1S': '메가심포니아',
    'M2': '인페르노X',
    'S10A': '다크판타즈마',
    'M2A': 'MEGA드림ex',
}

# 검색에서 제외할 레어도
EXCLUDED_RARITIES = ['RR', 'RRR', 'R', 'U', 'C']

# 모든 레어도 목록
ALL_RARITIES = ['UR', 'SSR', 'SR', 'RR', 'RRR', 'CHR', 'CSR', 'BWR', 'AR', 'SAR', 'HR', 'R', 'U', 'C', '몬스터볼', '마스터볼', '이로치', '미러']


def normalize_shop_code(code: str) -> str:
    """상품코드를 정규화 (대소문자 통일)"""
    return code.upper().strip() if code else ''


def is_japanese_card(shop_code: str) -> bool:
    """일본판 카드인지 확인 (-J 포함 여부)"""
    return '-J-' in shop_code.upper() or shop_code.upper().endswith('-J')


def card_exists(shop_code: str) -> bool:
    """카드가 이미 DB에 존재하는지 확인 (대소문자 구분 없이)"""
    normalized_code = normalize_shop_code(shop_code)
    
    # 효율적인 쿼리로 변경
    return Card.objects.filter(shop_product_code__iexact=shop_code).exists()


def parse_shop_code(shop_code: str) -> dict:
    """
    상품코드 파싱
    예: PKM-SV8A-075-K → {expansion_code: 'SV8A', card_number: '075'}
    예: PKM-SV8A-075-K-V2 → {expansion_code: 'SV8A', card_number: '075'}
    """
    parts = shop_code.upper().split('-')
    
    if len(parts) < 4:
        return None
    
    return {
        'expansion_code': parts[1],
        'card_number': parts[2]
    }


def parse_product_name(product_name: str) -> dict:
    """
    상품명에서 카드 정보 파싱
    
    예1: "포켓몬카드 이야후 테라스탈페스타ex 덱소스"
         → {name: '이야후', rarity: None, expansion_name: '테라스탈페스타ex'}
    
    예2: "포켓몬카드 다투곰 붉은 달 마스터볼 미러 테라스탈페스타ex"
         → {name: '다투곰 붉은 달', rarity: '마스터볼', expansion_name: '테라스탈페스타ex'}
    
    예3: "포켓몬카드 자마젠타V VMAX클라이맥스"
         → {name: '자마젠타V', rarity: None, expansion_name: 'VMAX클라이맥스'}
    """
    if not product_name.startswith("포켓몬카드"):
        return None
    
    # "포켓몬카드" 제거
    text = product_name.replace("포켓몬카드", "").strip()
    original_text = text  # 원본 저장
    
    # 확장팩명 리스트 (긴 이름부터 정렬)
    expansion_names = sorted(list(EXPANSION_INFO.values()), key=len, reverse=True)
    
    # 확장팩명 찾기 (뒤에서부터 매칭 - 가장 마지막 출현 위치)
    expansion_name = None
    text_without_expansion = text
    
    for exp_name in expansion_names:
        # 확장팩명의 마지막 출현 위치 찾기
        last_index = text.rfind(exp_name)
        if last_index != -1:
            expansion_name = exp_name
            # 확장팩명 이전까지만 추출
            text_without_expansion = text[:last_index].strip()
            break
    
    text = text_without_expansion
    
    # 레어도 찾기 (뒤에서부터 검색)
    rarity = None
    card_name = text
    
    # 특수 레어도 패턴 (복합 레어도 우선 처리)
    special_rarities = ['마스터볼 미러', '몬스터볼 미러', '마스터볼', '몬스터볼', '이로치']
    
    for special_rarity in special_rarities:
        # 특수 레어도의 마지막 출현 위치 찾기
        last_index = text.rfind(special_rarity)
        if last_index != -1:
            # "마스터볼 미러" → "마스터볼"로 저장
            if special_rarity == '마스터볼 미러':
                rarity = '마스터볼'
            elif special_rarity == '몬스터볼 미러':
                rarity = '몬스터볼'
            else:
                rarity = special_rarity
            
            # 레어도 이전까지가 카드명
            card_name = text[:last_index].strip()
            break
    
    # 일반 레어도 체크 (특수 레어도가 없을 때만)
    if not rarity:
        for rare in ['UR', 'SSR', 'SR', 'CHR', 'CSR', 'BWR', 'AR', 'SAR', 'HR', '미러']:
            # 단어 경계를 확인하여 정확히 매칭
            pattern = rf'\b{rare}\b'
            match = re.search(pattern, text)
            if match:
                rarity = rare
                # 레어도 이전까지가 카드명
                card_name = text[:match.start()].strip()
                break
    
    return {
        'name': card_name,
        'rarity': rarity,
        'expansion_name': expansion_name
    }

def get_or_create_expansion(expansion_code: str, skip_if_not_exists: bool = False) -> Expansion:
    """
    확장팩 가져오기 또는 생성
    
    Args:
        expansion_code: 확장팩 코드
        skip_if_not_exists: True면 DB에 없을 때 None 반환 (생성 안 함)
    """
    try:
        # DB에서 확장팩 찾기
        expansion = Expansion.objects.get(code=expansion_code)
        return expansion
    except Expansion.DoesNotExist:
        if skip_if_not_exists:
            # DB에 없으면 None 반환 (건너뛰기)
            return None
        
        # DB에 없으면 새로 생성
        expansion_name = EXPANSION_INFO.get(expansion_code)
        
        if not expansion_name:
            print(f"  ⚠️ 알 수 없는 확장팩 코드: {expansion_code}")
            return None
        
        expansion, created = Expansion.objects.get_or_create(
            code=expansion_code,
            defaults={
                'name': expansion_name,
                'image_url': ''
            }
        )
        
        if created:
            print(f"  📦 확장팩 생성: {expansion_name}")
        
        return expansion


def save_card_to_db(shop_code: str, parsed_shop: dict, parsed_name: dict, image_url: str = '') -> bool:
    """카드를 DB에 저장"""
    try:
        # 확장팩 가져오기 (DB에 없으면 None 반환)
        expansion = get_or_create_expansion(parsed_shop['expansion_code'], skip_if_not_exists=True)
        
        if not expansion:
            print(f"  ⚠️ DB에 없는 확장팩: {parsed_shop['expansion_code']}")
            return False
        
        # 레어도 결정 (없으면 'C'로 기본값)
        rarity = parsed_name['rarity'] if parsed_name['rarity'] else 'C'
        
        # 레어도가 유효한지 확인
        if rarity not in [choice[0] for choice in Card.RARITY_CHOICES]:
            print(f"  ⚠️ 알 수 없는 레어도: {rarity}, 'C'로 저장")
            rarity = 'C'
        
        # 상품코드를 대문자로 변환
        shop_code_upper = shop_code.upper()
        
        # 카드 저장
        card, created = Card.objects.update_or_create(
            shop_product_code=shop_code_upper,  # 대문자로 저장
            defaults={
                'expansion': expansion,
                'card_number': parsed_shop['card_number'],
                'name': parsed_name['name'],
                'rarity': rarity,
                'image_url': image_url  # 엑셀에서 가져온 이미지 URL
            }
        )
        
        return True
        
    except Exception as e:
        print(f"  ❌ DB 저장 오류: {e}")
        return False


def process_excel_file(file_path: str, dry_run: bool = True) -> tuple:
    """
    엑셀 파일 처리
    
    Args:
        file_path: 엑셀 파일 경로
        dry_run: True면 실제 저장 안 함 (테스트용)
    
    Returns:
        (추가된 수, 건너뛴 수, 오류 수)
    """
    print(f"\n📂 파일 처리 중: {os.path.basename(file_path)}")
    print("-" * 60)
    
    added_count = 0
    skipped_count = 0
    error_count = 0
    
    try:
        wb = openpyxl.load_workbook(file_path, data_only=True)
        ws = wb.active
        
        # 6행부터 데이터 시작
        for row_idx, row in enumerate(ws.iter_rows(min_row=6), start=6):
            # B열 (인덱스 1) - 네이버 상품코드
            shop_code = row[1].value
            # D열 (인덱스 3) - 상품명
            product_name = row[3].value
            # U열 (인덱스 20) - 이미지 URL
            image_url = row[20].value if len(row) > 20 else ''
            
            if not shop_code or not product_name:
                continue
            
            shop_code = str(shop_code).strip()
            product_name = str(product_name).strip()
            image_url = str(image_url).strip() if image_url else ''
            
            # 일본판 체크
            if is_japanese_card(shop_code):
                print(f"[건너뜀] {shop_code} - 일본판")
                skipped_count += 1
                continue
            
            # 이미 존재하는 카드 체크 (대소문자 구분 없이)
            if card_exists(shop_code):
                print(f"[건너뜀] {shop_code} - 이미 존재")
                skipped_count += 1
                continue
            
            # 상품코드 파싱
            parsed_shop = parse_shop_code(shop_code)
            if not parsed_shop:
                print(f"[오류] {shop_code} - 상품코드 형식 오류")
                error_count += 1
                continue
            
            # DB에 확장팩이 있는지 확인
            expansion = get_or_create_expansion(parsed_shop['expansion_code'], skip_if_not_exists=True)
            if not expansion:
                print(f"[건너뜀] {shop_code} - DB에 없는 확장팩: {parsed_shop['expansion_code']}")
                skipped_count += 1
                continue
            
            # 상품명 파싱
            parsed_name = parse_product_name(product_name)
            if not parsed_name:
                print(f"[오류] {shop_code} - 상품명 파싱 실패: {product_name}")
                error_count += 1
                continue
            
            # 정보 출력
            print(f"[발견] {shop_code.upper()}")  # 대문자로 표시
            print(f"  카드명: {parsed_name['name']}")
            print(f"  레어도: {parsed_name['rarity'] or 'C (기본값)'}")
            print(f"  확장팩: {parsed_shop['expansion_code']} - {expansion.name}")
            if image_url:
                print(f"  이미지: {image_url[:50]}...")  # 일부만 표시
            
            # 실제 저장
            if not dry_run:
                if save_card_to_db(shop_code, parsed_shop, parsed_name, image_url):
                    print(f"  ✅ DB 저장 완료")
                    added_count += 1
                else:
                    error_count += 1
            else:
                added_count += 1
        
        wb.close()
        
    except Exception as e:
        print(f"❌ 파일 처리 오류: {e}")
        import traceback
        traceback.print_exc()
        return 0, 0, 1
    
    return added_count, skipped_count, error_count


def import_all_excel_files(folder_path: str = '.', dry_run: bool = True):
    """폴더 내 모든 엑셀 파일 처리"""
    mode_text = "테스트 모드 (실제 저장 안 함)" if dry_run else "실제 저장 모드"
    
    print("\n" + "=" * 80)
    print(f"📊 엑셀 파일에서 카드 정보 가져오기 - {mode_text}")
    print("=" * 80)
    
    # 엑셀 파일 찾기
    excel_files = glob.glob(os.path.join(folder_path, '*.xlsx'))
    excel_files = [f for f in excel_files if not os.path.basename(f).startswith('~$')]
    
    if not excel_files:
        print("❌ 엑셀 파일을 찾을 수 없습니다.")
        return
    
    print(f"\n📁 {len(excel_files)}개의 엑셀 파일 발견\n")
    
    total_added = 0
    total_skipped = 0
    total_errors = 0
    
    for excel_file in excel_files:
        added, skipped, errors = process_excel_file(excel_file, dry_run)
        total_added += added
        total_skipped += skipped
        total_errors += errors
    
    # 결과 출력
    print("\n" + "=" * 80)
    print("📊 처리 완료")
    print("=" * 80)
    print(f"✅ 추가됨: {total_added}개")
    print(f"⏭️  건너뜀: {total_skipped}개")
    print(f"❌ 오류: {total_errors}개")


if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("📊 엑셀 파일 카드 가져오기 도구")
    print("=" * 80)
    
    print("\n엑셀 파일이 있는 폴더 경로를 입력하세요.")
    print("(엔터를 누르면 현재 폴더에서 찾습니다)")
    
    folder_path = input("\n폴더 경로: ").strip()
    
    if not folder_path:
        folder_path = '.'
    
    if not os.path.exists(folder_path):
        print(f"❌ 폴더를 찾을 수 없습니다: {folder_path}")
    else:
        print("\n모드 선택:")
        print("  1. 테스트 모드 (실제 저장 안 함)")
        print("  2. 실제 저장 모드")
        
        mode = input("\n선택 (1/2): ").strip()
        
        dry_run = (mode != '2')
        
        if dry_run:
            print("\n⚠️ 테스트 모드로 실행합니다. 실제로 DB에 저장되지 않습니다.\n")
        else:
            confirm = input("\n⚠️ 실제로 DB에 저장하시겠습니까? (yes/no): ")
            if confirm.lower() != 'yes':
                print("취소되었습니다.")
                exit()
        
        import_all_excel_files(folder_path, dry_run)