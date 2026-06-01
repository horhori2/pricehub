"""
filter_pokemon_items 테스트 스크립트
실행: python test_filter.py
"""
import re

EXCLUDED_RARITIES = set()  # ← 기존 코드의 EXCLUDED_RARITIES로 교체

MIRROR_RARITIES = {'미러', '몬스터볼', '마스터볼', '볼 미러', '타입 미러', '로켓단 미러'}

MIRROR_KEYWORDS = {
    '미러':        None,
    '몬스터볼':    '몬스터볼',
    '마스터볼':    '마스터볼',
    '볼 미러':     '볼',
    '타입 미러':   '타입',
    '로켓단 미러': '로켓단 미러',
}


def filter_pokemon_items(items, card_name, rarity):
    min_price = None
    valid_count = 0
    min_price_mall = None
    valid_items = []

    excluded_malls = ["화성스토어-TCG-", "카드 베이스", "네이버", "쿠팡"]
    excluded_keywords = ['일본', '일본판', 'JP', 'JPN', '일판']

    is_mirror_rarity = rarity in MIRROR_RARITIES
    is_c_rarity = rarity == 'C'

    print(f"\n📋 필터링 상세 로그 (총 {len(items)}개):")

    for idx, item in enumerate(items, 1):
        title = item['title']
        price = float(item['lprice'])
        mall_name = item.get('mallName', '알 수 없음')

        print(f"\n[{idx}] 가격: {int(price)}원 / 판매처: {mall_name}")
        clean_title = re.sub(r'<[^>]+>', '', title)
        print(f"    제목: {clean_title}")

        if mall_name in excluded_malls:
            print(f"    ❌ 제외 판매처"); continue

        if any(kw in title for kw in excluded_keywords):
            print(f"    ❌ 일본판 키워드 포함"); continue

        card_name_no_space = re.sub(r'\s+', '', card_name)
        title_no_space = re.sub(r'\s+', '', clean_title)
        if card_name_no_space.lower() not in title_no_space.lower():
            print(f"    ❌ 카드명 불일치"); continue
        print(f"    ✅ 카드명 일치")

        # ── 레어도 필터링 ──
        # C 레어도: EXCLUDED_RARITIES 여부와 무관하게 미러 키워드 항상 체크
        if is_c_rarity:
            mirror_title_keywords = ['미러', '몬스터볼', '마스터볼']
            if any(kw in clean_title for kw in mirror_title_keywords):
                print(f"    ❌ C 레어도인데 미러 키워드 포함"); continue

        elif rarity and rarity not in EXCLUDED_RARITIES:
            if is_mirror_rarity:
                required_kw = MIRROR_KEYWORDS.get(rarity)
                if required_kw and required_kw not in clean_title:
                    print(f"    ❌ 미러 레어도 '{rarity}' 키워드 '{required_kw}' 불일치"); continue
                print(f"    ✅ 미러 레어도 '{rarity}' 일치")

            elif rarity == 'MUR':
                if 'MUR' not in clean_title.upper():
                    print(f"    ❌ MUR 레어도 불일치"); continue
                print(f"    ✅ MUR 레어도 일치")

            else:
                if rarity not in clean_title:
                    print(f"    ❌ 레어도 '{rarity}' 불일치"); continue

        valid_count += 1
        valid_items.append(item)
        print(f"    ✅ 유효한 상품!")

        if min_price is None or price < min_price:
            min_price = price
            min_price_mall = mall_name
            print(f"    💰 최저가 업데이트: {int(min_price)}원")

    print(f"\n📊 필터링 결과: 유효 상품 {valid_count}개")
    return min_price, valid_count, min_price_mall, valid_items


# ── 테스트 ────────────────────────────────────────────────

PASS = "✅ PASS"
FAIL = "❌ FAIL"

def run_test(name, items, card_name, rarity, expected_count, expected_valid_titles=None):
    print(f"\n{'='*60}")
    print(f"🧪 {name}")
    print(f"   카드명: {card_name} / 레어도: {rarity}")
    print(f"   기대 통과 수: {expected_count}개")
    print(f"{'='*60}")
    _, count, _, valid_items = filter_pokemon_items(items, card_name, rarity)
    ok = count == expected_count
    print(f"\n결과: {PASS if ok else FAIL} (통과 {count}개 / 기대 {expected_count}개)")
    if expected_valid_titles:
        for item in valid_items:
            clean = re.sub(r'<[^>]+>', '', item['title'])
            check = "✅" if any(t in clean for t in expected_valid_titles) else "⚠️ 예상 외"
            print(f"  {check} {clean}")
    return ok


results = []

# ── 테스트 1: C 레어도 — 미러 키워드 있는 상품 제외 ──
results.append(run_test(
    name="C 레어도 — 미러 키워드 상품 제외",
    items=[
        {'title': '포켓몬카드 꼬몽울 C 테라스탈페스타ex', 'lprice': '200', 'mallName': '카드냥'},
        {'title': '포켓몬카드 꼬몽울 미러 테라스탈페스타ex', 'lprice': '500', 'mallName': '카드냥'},
        {'title': '포켓몬카드 꼬몽울 몬스터볼 테라스탈페스타ex', 'lprice': '800', 'mallName': '카드냥'},
        {'title': '포켓몬카드 꼬몽울 테라스탈페스타ex 일반', 'lprice': '150', 'mallName': '트레이너스'},
    ],
    card_name='꼬몽울', rarity='C', expected_count=2,
))

# ── 테스트 2: 몬스터볼 레어도 — 몬스터볼 키워드만 통과 ──
results.append(run_test(
    name="몬스터볼 레어도 — 몬스터볼 키워드만 통과",
    items=[
        {'title': '포켓몬카드 꼬몽울 몬스터볼 테라스탈페스타ex', 'lprice': '800', 'mallName': '카드냥'},
        {'title': '포켓몬카드 꼬몽울 마스터볼 테라스탈페스타ex', 'lprice': '1200', 'mallName': '카드냥'},
        {'title': '포켓몬카드 꼬몽울 미러 테라스탈페스타ex', 'lprice': '500', 'mallName': '카드냥'},
        {'title': '포켓몬카드 꼬몽울 C 테라스탈페스타ex', 'lprice': '200', 'mallName': '트레이너스'},
        {'title': '포켓몬카드 꼬몽울 볼 몬스터볼 테라스탈', 'lprice': '750', 'mallName': 'TCG999'},
    ],
    card_name='꼬몽울', rarity='몬스터볼', expected_count=2,
))

# ── 테스트 3: 마스터볼 레어도 ──
results.append(run_test(
    name="마스터볼 레어도 — 마스터볼 키워드만 통과",
    items=[
        {'title': '포켓몬카드 리자몽 마스터볼 인페르노ex', 'lprice': '5000', 'mallName': '카드냥'},
        {'title': '포켓몬카드 리자몽 몬스터볼 인페르노ex', 'lprice': '1500', 'mallName': '카드냥'},
        {'title': '포켓몬카드 리자몽 미러 인페르노ex', 'lprice': '800', 'mallName': '카드냥'},
        {'title': '포켓몬카드 리자몽 C 인페르노ex', 'lprice': '300', 'mallName': '트레이너스'},
    ],
    card_name='리자몽', rarity='마스터볼', expected_count=1,
))

# ── 테스트 4: 볼 미러 레어도 ──
results.append(run_test(
    name="볼 미러 레어도 — '볼' 키워드만 통과",
    items=[
        {'title': '포켓몬카드 피카츄 볼 미러 샤이니트레저', 'lprice': '3000', 'mallName': '카드냥'},
        {'title': '포켓몬카드 피카츄 타입 미러 샤이니트레저', 'lprice': '2000', 'mallName': '카드냥'},
        {'title': '포켓몬카드 피카츄 미러 샤이니트레저', 'lprice': '1000', 'mallName': '카드냥'},
        {'title': '포켓몬카드 피카츄 몬스터볼 샤이니트레저', 'lprice': '800', 'mallName': '트레이너스'},
    ],
    card_name='피카츄', rarity='볼 미러', expected_count=2,
))

# ── 테스트 5: 타입 미러 레어도 ──
results.append(run_test(
    name="타입 미러 레어도 — '타입' 키워드만 통과",
    items=[
        {'title': '포켓몬카드 피카츄 타입 미러 샤이니트레저', 'lprice': '2000', 'mallName': '카드냥'},
        {'title': '포켓몬카드 피카츄 볼 미러 샤이니트레저', 'lprice': '3000', 'mallName': '카드냥'},
        {'title': '포켓몬카드 피카츄 C 샤이니트레저', 'lprice': '200', 'mallName': '트레이너스'},
    ],
    card_name='피카츄', rarity='타입 미러', expected_count=1,
))

# ── 테스트 6: 로켓단 미러 레어도 — 카드명에 로켓단 포함 케이스 ──
results.append(run_test(
    name="로켓단 미러 레어도 — '로켓단 미러' 키워드 통과",
    items=[
        {'title': '포켓몬카드 로켓단의렌트라 로켓단 미러 151', 'lprice': '8000', 'mallName': '카드냥'},
        {'title': '포켓몬카드 로켓단의렌트라 미러 151', 'lprice': '3000', 'mallName': '카드냥'},
        {'title': '포켓몬카드 로켓단의렌트라 C 151', 'lprice': '300', 'mallName': '트레이너스'},
    ],
    card_name='로켓단의렌트라', rarity='로켓단 미러', expected_count=1,
))

# ── 최종 결과 ──────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"📊 최종 결과: {sum(results)}/{len(results)} 통과")
print(f"{'='*60}")