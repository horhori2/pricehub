# find_contaminated_prices.py
"""
가격 이력(raw_data)에 지금 필터 기준으로는 유효하지 않은 상품이 섞여
들어간 행을 찾아 CSV로 보고한다 (읽기 전용 — 아무것도 수정/삭제하지 않음).

과거에 필터 로직이 지금과 달랐거나 버그가 있었을 때 저장된 오염 데이터를
찾기 위함. 포켓몬/원피스/디지몬만 대상 — 일본판은 고정 페이지를 직접
크롤링하는 방식이라 이름/레어도 검색+필터 개념 자체가 없어서 제외.

사용법:
    python scripts/maintenance/find_contaminated_prices.py [pokemon] [onepiece] [digimon]
    (인자 없으면 3개 다 검사)
"""
import os
import sys
import csv
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from pricehub.models import (
    Card, CardPrice,
    OnePieceCard, OnePieceCardPrice,
    DigimonCard, DigimonCardPrice,
)
from pricehub.utils import (
    _is_excluded, _clean_title,
    _pokemon_item_is_valid, MIRROR_RARITIES, GENERAL_RARITIES,
    _digimon_item_is_valid,
    _onepiece_title_matches, _onepiece_rarity_flags, _BASE_CARD_NUMBER_RE,
)

CHUNK_SIZE = 5000
REPORT_DIR = BASE_DIR / 'scripts' / 'maintenance' / 'reports'


def _normalize_raw(raw):
    """raw_data가 dict(단일 상품) 또는 list(여러 상품)일 수 있어 항상 list로 통일."""
    if isinstance(raw, dict):
        return [raw] if raw else []
    if isinstance(raw, list):
        return raw
    return []


def _price_to_float(item):
    try:
        return float(item.get('lprice', 0))
    except (TypeError, ValueError):
        return 0.0


def scan_pokemon(writer):
    print("\n" + "=" * 70)
    print("[포켓몬] 카드 메타데이터 로딩")
    cards = {
        c.id: {
            'name': c.name,
            'rarity': c.rarity,
            'is_teukil': c.is_teukil,
            'shop_product_code': c.shop_product_code,
            'name_no_space': None,  # lazy
            'is_mirror_rarity': c.rarity in MIRROR_RARITIES,
            'is_general_rarity': c.rarity in GENERAL_RARITIES,
            'is_irochi': c.rarity == '이로치',
        }
        for c in Card.objects.all()
    }
    import re
    for meta in cards.values():
        meta['name_no_space'] = re.sub(r'\s+', '', meta['name']).lower()

    total = CardPrice.objects.count()
    print(f"[포켓몬] 가격 이력 {total}건 스캔 시작")

    scanned = 0
    contaminated_rows = 0
    t0 = time.time()

    qs = CardPrice.objects.values('id', 'card_id', 'raw_data', 'collected_at').iterator(chunk_size=CHUNK_SIZE)
    for row in qs:
        scanned += 1
        if scanned % 200000 == 0:
            elapsed = time.time() - t0
            print(f"  ...{scanned}/{total} ({elapsed:.0f}초 경과)")

        meta = cards.get(row['card_id'])
        if not meta:
            continue
        items = _normalize_raw(row['raw_data'])
        if not items:
            continue

        row_bad = False
        for item in items:
            title = _clean_title(item.get('title', ''))
            valid = (not _is_excluded(item)) and _pokemon_item_is_valid(
                title, meta['name_no_space'], meta['rarity'], meta['is_teukil'],
                meta['is_mirror_rarity'], meta['is_general_rarity'], meta['is_irochi'],
            )
            if not valid:
                row_bad = True
                writer.writerow([
                    'pokemon', row['id'], row['card_id'], meta['shop_product_code'],
                    meta['name'], meta['rarity'], item.get('mallName', ''),
                    item.get('lprice', ''), title, row['collected_at'],
                ])
        if row_bad:
            contaminated_rows += 1

    print(f"[포켓몬] 완료: {scanned}건 스캔, 오염 행 {contaminated_rows}건 ({time.time()-t0:.0f}초)")


def scan_onepiece(writer):
    print("\n" + "=" * 70)
    print("[원피스] 카드 메타데이터 로딩")
    cards = {}
    for c in OnePieceCard.objects.all():
        is_manga, is_special, is_parallel = _onepiece_rarity_flags(c.rarity)
        cards[c.id] = {
            'card_number': c.card_number,
            'rarity': c.rarity,
            'shop_product_code': c.shop_product_code,
            'base_number': _BASE_CARD_NUMBER_RE.sub('', c.card_number),
            'is_manga': is_manga,
            'is_special': is_special,
            'is_parallel': is_parallel,
        }

    total = OnePieceCardPrice.objects.count()
    print(f"[원피스] 가격 이력 {total}건 스캔 시작")

    scanned = 0
    contaminated_rows = 0
    t0 = time.time()

    qs = OnePieceCardPrice.objects.values('id', 'card_id', 'raw_data', 'collected_at').iterator(chunk_size=CHUNK_SIZE)
    for row in qs:
        scanned += 1
        if scanned % 200000 == 0:
            elapsed = time.time() - t0
            print(f"  ...{scanned}/{total} ({elapsed:.0f}초 경과)")

        meta = cards.get(row['card_id'])
        if not meta:
            continue
        items = _normalize_raw(row['raw_data'])
        if not items:
            continue

        row_bad = False
        for item in items:
            title = _clean_title(item.get('title', ''))
            price = _price_to_float(item)
            valid = (not _is_excluded(item)) and _onepiece_title_matches(
                title, meta['base_number'], meta['is_manga'], meta['is_special'],
                meta['is_parallel'], price, meta['rarity'],
            )
            if not valid:
                row_bad = True
                writer.writerow([
                    'onepiece', row['id'], row['card_id'], meta['shop_product_code'],
                    meta['card_number'], meta['rarity'], item.get('mallName', ''),
                    item.get('lprice', ''), title, row['collected_at'],
                ])
        if row_bad:
            contaminated_rows += 1

    print(f"[원피스] 완료: {scanned}건 스캔, 오염 행 {contaminated_rows}건 ({time.time()-t0:.0f}초)")


def scan_digimon(writer):
    print("\n" + "=" * 70)
    print("[디지몬] 카드 메타데이터 로딩")
    cards = {
        c.id: {
            'card_number': c.card_number,
            'shop_product_code': c.shop_product_code,
            'is_parallel': c.is_parallel,
            'is_scarce': c.is_scarce,
            'is_special': c.is_special,
        }
        for c in DigimonCard.objects.all()
    }

    total = DigimonCardPrice.objects.count()
    print(f"[디지몬] 가격 이력 {total}건 스캔 시작")

    scanned = 0
    contaminated_rows = 0
    t0 = time.time()

    qs = DigimonCardPrice.objects.values('id', 'card_id', 'raw_data', 'collected_at').iterator(chunk_size=CHUNK_SIZE)
    for row in qs:
        scanned += 1
        if scanned % 200000 == 0:
            elapsed = time.time() - t0
            print(f"  ...{scanned}/{total} ({elapsed:.0f}초 경과)")

        meta = cards.get(row['card_id'])
        if not meta:
            continue
        items = _normalize_raw(row['raw_data'])
        if not items:
            continue

        row_bad = False
        for item in items:
            title = _clean_title(item.get('title', ''))
            valid = (not _is_excluded(item)) and _digimon_item_is_valid(
                title, meta['card_number'], meta['is_parallel'], meta['is_scarce'], meta['is_special'],
            )
            if not valid:
                row_bad = True
                writer.writerow([
                    'digimon', row['id'], row['card_id'], meta['shop_product_code'],
                    meta['card_number'], '', item.get('mallName', ''),
                    item.get('lprice', ''), title, row['collected_at'],
                ])
        if row_bad:
            contaminated_rows += 1

    print(f"[디지몬] 완료: {scanned}건 스캔, 오염 행 {contaminated_rows}건 ({time.time()-t0:.0f}초)")


def main():
    games = [a.lower() for a in sys.argv[1:]] or ['pokemon', 'onepiece', 'digimon']

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORT_DIR / f'contaminated_prices_{time.strftime("%Y%m%d_%H%M%S")}.csv'

    print("=" * 70)
    print("오염 가격 데이터 검사 (읽기 전용)")
    print(f"대상: {games}")
    print(f"출력: {out_path}")
    print("=" * 70)

    with open(out_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow([
            'game', 'price_row_id', 'card_id', 'shop_product_code',
            'card_name_or_number', 'rarity', 'mall_name', 'price',
            'bad_title', 'collected_at',
        ])

        t0 = time.time()
        if 'pokemon' in games:
            scan_pokemon(writer)
        if 'onepiece' in games:
            scan_onepiece(writer)
        if 'digimon' in games:
            scan_digimon(writer)

    print("\n" + "=" * 70)
    print(f"전체 완료: {time.time()-t0:.0f}초")
    print(f"보고서: {out_path}")
    print("=" * 70)


if __name__ == '__main__':
    main()
