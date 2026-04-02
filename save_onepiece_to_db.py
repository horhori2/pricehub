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
    {'code': 'OPK-11', 'name': '[OPK-11] 부스터 팩 신속의 권'},
    {'code': 'EBK-02', 'name': '[EBK-02] 엑스트라 부스터 팩 Anime 25th collection'},
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

# ==================== 업데이트 정책 Enum ====================
class UpdatePolicy:
    ASK    = 'ask'     # 매번 물어보기
    ALL    = 'all'     # 모두 업데이트
    SKIP   = 'skip'    # 모두 건너뛰기
    RECODE = 'recode'  # 다른 코드로 새로 저장

# ==================== 유틸리티 함수 ====================

def extract_text_only(element):
    """첫 텍스트만 가져오기"""
    if element:
        text = element.find(text=True)
        return text.strip() if text else ""
    return ""


def modify_rarity(card_number: str, rarity: str) -> str:
    match = re.search(r"_[Pp](\d+)", card_number)
    if match:
        p_num = int(match.group(1))
        if p_num == 1:
            return f"P-{rarity}"
        else:
            return f"SP-{rarity}"
    return rarity


def extract_card_code(card_number: str) -> str:
    return re.sub(r"_[Pp]\d+", "", card_number, flags=re.IGNORECASE)


def generate_shop_product_code(card_number: str) -> str:
    card_number_upper = card_number.upper()
    base_code = re.sub(r"_P\d+", "", card_number_upper)
    product_code = f"OPC-{base_code}-K"
    match = re.search(r"_P(\d+)", card_number_upper)
    if match:
        p_num = match.group(1)
        product_code += f"-V{p_num}"
    return product_code


# ==================== 업데이트 정책 결정 ====================

def ask_update_policy() -> str:
    """
    크롤링 시작 전, 기존 데이터 충돌 시 전체 정책을 묻는다.
    반환값: UpdatePolicy 상수 중 하나
    """
    print("\n" + "─" * 60)
    print("📋 기존 DB 데이터 충돌 시 처리 방식을 선택하세요:")
    print("  1. 매번 물어보기  (카드별로 직접 결정)")
    print("  2. 모두 업데이트  (덮어쓰기)")
    print("  3. 모두 건너뛰기  (기존 데이터 유지)")
    print("  4. 다른 코드로 저장  (일괄 접미어 지정)")
    print("─" * 60)

    while True:
        choice = input("선택 (1/2/3/4): ").strip()
        if choice == '1':
            return UpdatePolicy.ASK
        elif choice == '2':
            return UpdatePolicy.ALL
        elif choice == '3':
            return UpdatePolicy.SKIP
        elif choice == '4':
            return UpdatePolicy.RECODE
        else:
            print("❌ 1~4 중에서 선택해주세요.")


def ask_recode_suffix() -> str:
    """'다른 코드로 저장' 선택 시 접미어를 입력받는다."""
    print("\n기존 상품코드에 붙일 접미어를 입력하세요.")
    print("예) _NEW  →  OPC-OP10-046-K_NEW")
    while True:
        suffix = input("접미어: ").strip()
        if suffix:
            return suffix
        print("❌ 접미어를 입력해주세요.")


def resolve_conflict(existing_card, new_data: dict, policy: str, suffix: str) -> tuple[str, str | None]:
    """
    기존 카드와 새 데이터 충돌 해결.

    반환: (action, new_code)
      action:
        'update'  - 기존 레코드를 덮어씀
        'skip'    - 아무 것도 하지 않음
        'recode'  - new_code 로 새 레코드 삽입
      new_code: recode 시 사용할 상품코드, 그 외 None
    """
    if policy == UpdatePolicy.ALL:
        return 'update', None

    if policy == UpdatePolicy.SKIP:
        return 'skip', None

    if policy == UpdatePolicy.RECODE:
        new_code = existing_card.shop_product_code + suffix
        return 'recode', new_code

    # UpdatePolicy.ASK — 카드별로 직접 결정
    print("\n" + "─" * 60)
    print(f"⚠️  이미 존재하는 카드:")
    print(f"   상품코드  : {existing_card.shop_product_code}")
    print(f"   카드번호  : {existing_card.card_number}")
    print(f"   카드명    : {existing_card.name}")
    print(f"   레어도    : {existing_card.rarity}")
    print(f"\n   새 데이터  : {new_data['card_number']} / {new_data['name']} / {new_data['rarity']}")
    print("─" * 60)
    print("  u) 업데이트   s) 건너뛰기   r) 다른 코드로 저장")

    while True:
        action_input = input("선택 (u/s/r): ").strip().lower()
        if action_input == 'u':
            return 'update', None
        elif action_input == 's':
            return 'skip', None
        elif action_input == 'r':
            default_code = existing_card.shop_product_code + "_NEW"
            entered = input(f"새 상품코드 입력 (기본값: {default_code}): ").strip()
            new_code = entered if entered else default_code
            return 'recode', new_code
        else:
            print("❌ u / s / r 중 하나를 입력하세요.")


# ==================== 크롤링 함수 ====================

def crawl_onepiece_series(series_code: str, series_name: str, policy: str, suffix: str = ""):
    print("\n" + "=" * 80)
    print(f"🏴‍☠️ 원피스 카드 크롤링 시작: {series_name}")
    print("=" * 80 + "\n")

    expansion, created = OnePieceExpansion.objects.get_or_create(
        code=series_code,
        defaults={'name': series_name.replace(f'[{series_code}] ', '')}
    )
    print(f"{'✅ 새로운' if created else '📦 기존'} 확장팩: {expansion.name}")

    base_url = "https://onepiece-cardgame.kr/cardlist.do"
    headers = {"User-Agent": "Mozilla/5.0"}

    page = 0
    total_cards = new_cards = updated_cards = skipped_cards = recoded_cards = 0

    while True:
        params = {
            "page": page, "size": 20,
            "freewords": "", "categories": "", "illustrations": "", "colors": "",
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
                    card_number  = extract_text_only(card_elem.select_one(".cardNumber"))
                    card_name    = extract_text_only(card_elem.select_one(".cardName"))
                    rarity       = extract_text_only(card_elem.select_one(".rarity"))
                    card_type    = extract_text_only(card_elem.select_one(".cardType"))

                    if not card_number or not card_name:
                        continue

                    adjusted_rarity   = modify_rarity(card_number, rarity)
                    is_manga          = adjusted_rarity.startswith('SP-') and adjusted_rarity != 'SP-SP'
                    shop_product_code = generate_shop_product_code(card_number)

                    new_data = {
                        'card_number': card_number,
                        'name':        card_name,
                        'rarity':      adjusted_rarity if adjusted_rarity in dict(OnePieceCard.RARITY_CHOICES) else 'C',
                        'is_manga':    is_manga,
                        'image_url':   '',
                        'expansion':   expansion,
                    }

                    total_cards += 1
                    manga_tag = " [망가]" if is_manga else ""

                    # ── 기존 레코드 조회 ──────────────────────────────────
                    existing = OnePieceCard.objects.filter(
                        shop_product_code=shop_product_code
                    ).first()

                    if existing is None:
                        # 신규 등록
                        OnePieceCard.objects.create(
                            shop_product_code=shop_product_code,
                            **new_data
                        )
                        new_cards += 1
                        print(f"  ✅ 신규: {card_number} ({shop_product_code}) - {card_name} ({adjusted_rarity}){manga_tag}")

                    else:
                        # 충돌 → 정책에 따라 처리
                        action, new_code = resolve_conflict(existing, new_data, policy, suffix)

                        if action == 'update':
                            for field, value in new_data.items():
                                setattr(existing, field, value)
                            existing.save()
                            updated_cards += 1
                            print(f"  🔄 업데이트: {card_number} ({shop_product_code}) - {card_name} ({adjusted_rarity}){manga_tag}")

                        elif action == 'skip':
                            skipped_cards += 1
                            print(f"  ⏭️  건너뜀: {card_number} ({shop_product_code})")

                        elif action == 'recode':
                            OnePieceCard.objects.create(
                                shop_product_code=new_code,
                                **new_data
                            )
                            recoded_cards += 1
                            print(f"  🆕 재코드 저장: {card_number} ({new_code}) - {card_name} ({adjusted_rarity}){manga_tag}")

                except Exception as e:
                    print(f"  ❌ 카드 처리 오류: {e}")
                    continue

            page += 1
            time.sleep(0.5)

        except Exception as e:
            print(f"❌ 페이지 요청 오류: {e}")
            break

    print("\n" + "=" * 80)
    print(f"📊 크롤링 완료: {series_name}")
    print("=" * 80)
    print(f"  ✅ 신규      : {new_cards}개")
    print(f"  🔄 업데이트  : {updated_cards}개")
    print(f"  ⏭️  건너뜀    : {skipped_cards}개")
    print(f"  🆕 재코드    : {recoded_cards}개")
    print(f"  📝 총 처리   : {total_cards}개\n")


def crawl_all_series(policy: str, suffix: str = ""):
    print("\n" + "=" * 80)
    print("🏴‍☠️ 원피스 카드 전체 크롤링 시작")
    print("=" * 80)

    for series in SERIES_LIST:
        try:
            crawl_onepiece_series(series['code'], series['name'], policy, suffix)
            time.sleep(1)
        except Exception as e:
            print(f"❌ 시리즈 '{series['code']}' 크롤링 실패: {e}")
            continue

    print("\n" + "=" * 80)
    print("📊 전체 크롤링 완료")
    print("=" * 80)
    print(f"  📦 총 확장팩 : {len(SERIES_LIST)}개")
    print(f"  🗂️  총 카드 수: {OnePieceCard.objects.count()}개")


# ==================== 진입점 ====================

if __name__ == '__main__':
    print("\n🏴‍☠️ 원피스 카드 크롤링 도구")
    print("=" * 80)
    print("\n선택하세요:")
    print("  1. 모든 시리즈 크롤링")
    print("  2. 특정 시리즈만 크롤링")
    print("  3. 종료")

    choice = input("\n선택 (1/2/3): ").strip()

    if choice == '3':
        print("종료합니다.")
    elif choice in ('1', '2'):
        # ── 공통: 업데이트 정책 먼저 결정 ──────────────────────────
        policy = ask_update_policy()
        suffix = ""
        if policy == UpdatePolicy.RECODE:
            suffix = ask_recode_suffix()

        if choice == '1':
            confirm = input("\n모든 시리즈를 크롤링하시겠습니까? (yes/no): ")
            if confirm.lower() == 'yes':
                crawl_all_series(policy, suffix)
        else:
            print("\n사용 가능한 시리즈:")
            for idx, series in enumerate(SERIES_LIST, 1):
                print(f"  {idx}. {series['name']}")

            series_num = int(input("\n시리즈 번호 선택: ").strip()) - 1
            if 0 <= series_num < len(SERIES_LIST):
                series = SERIES_LIST[series_num]
                crawl_onepiece_series(series['code'], series['name'], policy, suffix)
            else:
                print("❌ 잘못된 번호입니다.")
    else:
        print("❌ 잘못된 선택입니다.")