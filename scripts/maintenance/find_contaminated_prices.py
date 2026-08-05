# find_contaminated_prices.py
"""
가격 이력(raw_data)에 지금 필터 기준으로는 유효하지 않은 상품이 섞여
들어간 행을 찾아 CSV로 보고한다 (읽기 전용 — 아무것도 수정/삭제하지 않음).

과거에 필터 로직이 지금과 달랐거나 버그가 있었을 때 저장된 오염 데이터를
찾기 위함. 포켓몬/원피스/디지몬만 대상 — 일본판은 고정 페이지를 직접
크롤링하는 방식이라 이름/레어도 검색+필터 개념 자체가 없어서 제외.

메모리 주의사항: MySQL(mysqlclient)은 Django의 .iterator()를 쓰더라도
드라이버 커서가 결과셋 전체를 한 번에 버퍼링한다 — 파이썬 쪽에서 모델
객체로 안 쌓을 뿐, 그 앞 단계인 DB 드라이버 버퍼링 자체를 막지는 못한다.
가격 이력 테이블이 수백만 행(수 GB)이라 그대로 쓰면 메모리를 통째로
먹여버린다(실제로 이 문제로 서버가 한 번 다운됨). 그래서 반드시
`WHERE id > 마지막id ORDER BY id LIMIT N` 수동 페이지네이션으로 매
청크를 별도 쿼리로 날려서, MySQL 서버가 그때그때 청크 크기만큼만
계산해서 보내주도록 한다.

사용법:
    python -u scripts/maintenance/find_contaminated_prices.py [pokemon] [onepiece] [digimon]
    (인자 없으면 3개 다 검사. -u로 실행해야 진행 로그가 즉시 보임)
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

# 청크 크기: 작을수록 메모리는 덜 쓰지만 쿼리 왕복이 늘어남.
# raw_data가 카드당 최대 수십 KB일 수 있어 보수적으로 작게 잡음
# (5000행 기준 최악의 경우도 수십 MB 선 — 서버 RAM 1.9GB에 안전한 수준).
CHUNK_SIZE = 1000
# 청크 사이에 짧게 쉬어서 CPU를 몰아 쓰지 않도록 함 — 이전에 CPU
# 크레딧을 다 태워서 서버가 응답 불능이 된 적이 있어 반드시 필요.
SLEEP_BETWEEN_CHUNKS = 0.05
REPORT_DIR = BASE_DIR / 'scripts' / 'maintenance' / 'reports'


def _log(msg):
    print(msg, flush=True)


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


def _iter_price_rows_paginated(price_model, total):
    """
    id 기준 keyset 페이지네이션으로 가격 이력을 청크 단위로 스트리밍.
    매 청크를 별도 쿼리로 날리기 때문에 MySQL 드라이버가 결과셋 전체를
    버퍼링하는 일이 없다 — .iterator()만 쓰는 것과 달리 진짜로 메모리를
    적게 쓴다.
    """
    last_id = 0
    scanned = 0
    t0 = time.time()

    while True:
        chunk = list(
            price_model.objects
            .filter(id__gt=last_id)
            .order_by('id')
            .values('id', 'card_id', 'raw_data', 'collected_at')[:CHUNK_SIZE]
        )
        if not chunk:
            break

        for row in chunk:
            yield row
        last_id = chunk[-1]['id']
        scanned += len(chunk)

        if scanned % 50000 < CHUNK_SIZE:
            elapsed = time.time() - t0
            rate = scanned / elapsed if elapsed > 0 else 0
            eta = (total - scanned) / rate if rate > 0 else 0
            _log(f"  ...{scanned}/{total} ({elapsed:.0f}초 경과, {rate:.0f}행/초, 예상 잔여 {eta:.0f}초)")

        del chunk
        time.sleep(SLEEP_BETWEEN_CHUNKS)


def scan_pokemon(writer):
    _log("\n" + "=" * 70)
    _log("[포켓몬] 카드 메타데이터 로딩")
    import re
    cards = {}
    for c in Card.objects.only('id', 'name', 'rarity', 'is_teukil', 'shop_product_code'):
        cards[c.id] = {
            'name': c.name,
            'rarity': c.rarity,
            'is_teukil': c.is_teukil,
            'shop_product_code': c.shop_product_code,
            'name_no_space': re.sub(r'\s+', '', c.name).lower(),
            'is_mirror_rarity': c.rarity in MIRROR_RARITIES,
            'is_general_rarity': c.rarity in GENERAL_RARITIES,
            'is_irochi': c.rarity == '이로치',
        }

    total = CardPrice.objects.count()
    _log(f"[포켓몬] 가격 이력 {total}건 스캔 시작 (청크 {CHUNK_SIZE}행)")

    contaminated_rows = 0
    scanned = 0
    for row in _iter_price_rows_paginated(CardPrice, total):
        scanned += 1
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

    _log(f"[포켓몬] 완료: {scanned}건 스캔, 오염 행 {contaminated_rows}건")


def scan_onepiece(writer):
    _log("\n" + "=" * 70)
    _log("[원피스] 카드 메타데이터 로딩")
    cards = {}
    for c in OnePieceCard.objects.only('id', 'name', 'card_number', 'rarity', 'shop_product_code'):
        is_manga, is_special, is_parallel, is_redmanga = _onepiece_rarity_flags(c.rarity)
        cards[c.id] = {
            'name': c.name,
            'card_number': c.card_number,
            'rarity': c.rarity,
            'shop_product_code': c.shop_product_code,
            'base_number': _BASE_CARD_NUMBER_RE.sub('', c.card_number),
            'is_manga': is_manga,
            'is_special': is_special,
            'is_parallel': is_parallel,
            'is_redmanga': is_redmanga,
        }

    total = OnePieceCardPrice.objects.count()
    _log(f"[원피스] 가격 이력 {total}건 스캔 시작 (청크 {CHUNK_SIZE}행)")

    contaminated_rows = 0
    scanned = 0
    for row in _iter_price_rows_paginated(OnePieceCardPrice, total):
        scanned += 1
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
                meta['is_parallel'], price, meta['rarity'], meta['name'], meta['is_redmanga'],
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

    _log(f"[원피스] 완료: {scanned}건 스캔, 오염 행 {contaminated_rows}건")


def scan_digimon(writer):
    _log("\n" + "=" * 70)
    _log("[디지몬] 카드 메타데이터 로딩")

    # RBK-01(라이징 윈드) 재록 확장팩과 카드번호가 겹치는 카드 판별용.
    rbk01_card_numbers = set(
        DigimonCard.objects.filter(expansion__code='RBK-01').values_list('card_number', flat=True)
    )

    cards = {}
    for c in DigimonCard.objects.only(
        'id', 'card_number', 'shop_product_code', 'is_parallel', 'is_scarce', 'is_special', 'expansion',
    ).select_related('expansion'):
        if c.expansion.code == 'RBK-01':
            rbk01_marker_required = True
        elif c.card_number in rbk01_card_numbers:
            rbk01_marker_required = False
        else:
            rbk01_marker_required = None
        cards[c.id] = {
            'card_number': c.card_number,
            'shop_product_code': c.shop_product_code,
            'is_parallel': c.is_parallel,
            'is_scarce': c.is_scarce,
            'is_special': c.is_special,
            'rbk01_marker_required': rbk01_marker_required,
        }

    total = DigimonCardPrice.objects.count()
    _log(f"[디지몬] 가격 이력 {total}건 스캔 시작 (청크 {CHUNK_SIZE}행)")

    contaminated_rows = 0
    scanned = 0
    for row in _iter_price_rows_paginated(DigimonCardPrice, total):
        scanned += 1
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
                meta['rbk01_marker_required'],
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

    _log(f"[디지몬] 완료: {scanned}건 스캔, 오염 행 {contaminated_rows}건")


def main():
    games = [a.lower() for a in sys.argv[1:]] or ['pokemon', 'onepiece', 'digimon']

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORT_DIR / f'contaminated_prices_{time.strftime("%Y%m%d_%H%M%S")}.csv'

    _log("=" * 70)
    _log("오염 가격 데이터 검사 (읽기 전용)")
    _log(f"대상: {games}")
    _log(f"청크 크기: {CHUNK_SIZE}행 (keyset 페이지네이션 — DB 드라이버 전체 버퍼링 방지)")
    _log(f"출력: {out_path}")
    _log("=" * 70)

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

    _log("\n" + "=" * 70)
    _log(f"전체 완료: {time.time()-t0:.0f}초")
    _log(f"보고서: {out_path}")
    _log("=" * 70)


if __name__ == '__main__':
    main()
