# clean_contaminated_prices.py
"""
가격 이력(raw_data)에서 지금 필터 기준으로 유효하지 않은 상품만 제거하고,
남은 정상 상품으로 최저가를 다시 계산해 저장한다.

find_contaminated_prices.py(읽기 전용 진단)의 후속 조치 — 오염 상품만
빼고 정상 데이터는 그대로 보존하는 방식. 정상 상품이 하나도 안 남으면
그 가격 행 자체를 삭제한다(남길 정보가 없으므로).

기본은 dry_run=True(미리보기, DB 변경 없음). 실제 적용은 --apply 필요.

메모리 주의: find_contaminated_prices.py와 동일하게 WHERE id > 마지막id
LIMIT N 수동 keyset 페이지네이션으로 스트리밍 — MySQL 드라이버가 결과셋
전체를 버퍼링해 서버 메모리를 다 먹는 사고가 있었기 때문에 반드시 이
방식을 유지해야 함.

사용법:
    python -u scripts/maintenance/clean_contaminated_prices.py [pokemon] [onepiece] [digimon]              # 미리보기만
    python -u scripts/maintenance/clean_contaminated_prices.py --apply [pokemon] [onepiece] [digimon]      # 실제 적용
"""
import os
import sys
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
    _is_excluded, _clean_title, _build_price_result,
    _pokemon_item_is_valid, MIRROR_RARITIES, GENERAL_RARITIES,
    _digimon_item_is_valid,
    _onepiece_title_matches, _onepiece_rarity_flags, _BASE_CARD_NUMBER_RE,
)

CHUNK_SIZE = 1000
SLEEP_BETWEEN_CHUNKS = 0.05


def _log(msg):
    print(msg, flush=True)


def _normalize_raw(raw):
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
    last_id = 0
    scanned = 0
    t0 = time.time()

    while True:
        chunk = list(
            price_model.objects
            .filter(id__gt=last_id)
            .order_by('id')
            .values('id', 'card_id', 'raw_data', 'price', 'collected_at')[:CHUNK_SIZE]
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


def _clean_generic(price_model, card_model, total, item_validator, meta_of, dry_run):
    """
    공용 정리 루프.
    item_validator(item_title, meta) -> bool
    meta_of: {card_id: meta dict}
    """
    stats = {
        'scanned': 0, 'rows_touched': 0, 'rows_deleted': 0, 'rows_updated': 0,
        'items_removed': 0, 'cards_needing_cache_refresh': set(),
    }
    to_delete_ids = []
    to_update = []  # [(id, new_raw_data, new_price)]

    def flush():
        if not dry_run:
            if to_delete_ids:
                price_model.objects.filter(id__in=to_delete_ids).delete()
            for row_id, new_raw, new_price in to_update:
                price_model.objects.filter(id=row_id).update(raw_data=new_raw, price=new_price)
        to_delete_ids.clear()
        to_update.clear()

    for row in _iter_price_rows_paginated(price_model, total):
        stats['scanned'] += 1
        meta = meta_of.get(row['card_id'])
        if not meta:
            continue
        items = _normalize_raw(row['raw_data'])
        if not items:
            continue

        cleaned = [item for item in items if item_validator(item, meta)]
        if len(cleaned) == len(items):
            continue  # 오염 없음

        stats['rows_touched'] += 1
        stats['items_removed'] += (len(items) - len(cleaned))
        stats['cards_needing_cache_refresh'].add(row['card_id'])

        if not cleaned:
            stats['rows_deleted'] += 1
            to_delete_ids.append(row['id'])
        else:
            min_price, _valid_count, _mall, valid_items = _build_price_result(cleaned)
            stats['rows_updated'] += 1
            to_update.append((row['id'], valid_items, min_price))

        if len(to_delete_ids) + len(to_update) >= CHUNK_SIZE:
            flush()

    flush()
    return stats


def _refresh_card_caches(card_model, price_model, card_ids, dry_run):
    """
    정리 후 해당 카드의 최신 가격 행을 다시 조회해 latest_market_price/
    latest_raw_data 캐시를 갱신 (정리된 행이 그 카드의 '최신'이었을 수 있어
    캐시가 정리 전 값을 그대로 들고 있을 수 있음).
    """
    refreshed = 0
    for card_id in card_ids:
        latest = (
            price_model.objects.filter(card_id=card_id)
            .order_by('-collected_at')
            .values('raw_data', 'price')
            .first()
        )
        if not dry_run:
            card = card_model.objects.filter(id=card_id).first()
            if not card:
                continue
            if latest:
                card.latest_raw_data = _normalize_raw(latest['raw_data'])
                card.latest_market_price = int(latest['price'])
            else:
                card.latest_raw_data = None
                card.latest_market_price = None
            card.save(update_fields=['latest_raw_data', 'latest_market_price'])
        refreshed += 1
    return refreshed


def clean_pokemon(dry_run):
    _log("\n" + "=" * 70)
    _log(f"[포켓몬] 정리 시작 (dry_run={dry_run})")
    import re
    meta_of = {}
    for c in Card.objects.only('id', 'name', 'rarity', 'is_teukil'):
        meta_of[c.id] = {
            'name_no_space': re.sub(r'\s+', '', c.name).lower(),
            'rarity': c.rarity,
            'is_teukil': c.is_teukil,
            'is_mirror_rarity': c.rarity in MIRROR_RARITIES,
            'is_general_rarity': c.rarity in GENERAL_RARITIES,
            'is_irochi': c.rarity == '이로치',
        }

    def validator(item, meta):
        title = _clean_title(item.get('title', ''))
        return (not _is_excluded(item)) and _pokemon_item_is_valid(
            title, meta['name_no_space'], meta['rarity'], meta['is_teukil'],
            meta['is_mirror_rarity'], meta['is_general_rarity'], meta['is_irochi'],
        )

    total = CardPrice.objects.count()
    stats = _clean_generic(CardPrice, Card, total, validator, meta_of, dry_run)
    _log(f"[포켓몬] 스캔 {stats['scanned']}건 / 오염행 {stats['rows_touched']}건 "
         f"(수정 {stats['rows_updated']} / 삭제 {stats['rows_deleted']}) / 제거된 상품 {stats['items_removed']}건")

    refreshed = _refresh_card_caches(Card, CardPrice, stats['cards_needing_cache_refresh'], dry_run)
    _log(f"[포켓몬] 캐시 갱신 대상 카드 {refreshed}장")


def clean_onepiece(dry_run):
    _log("\n" + "=" * 70)
    _log(f"[원피스] 정리 시작 (dry_run={dry_run})")
    meta_of = {}
    for c in OnePieceCard.objects.only('id', 'name', 'card_number', 'rarity'):
        is_manga, is_special, is_parallel = _onepiece_rarity_flags(c.rarity)
        meta_of[c.id] = {
            'name': c.name,
            'base_number': _BASE_CARD_NUMBER_RE.sub('', c.card_number),
            'rarity': c.rarity,
            'is_manga': is_manga,
            'is_special': is_special,
            'is_parallel': is_parallel,
        }

    def validator(item, meta):
        title = _clean_title(item.get('title', ''))
        price = _price_to_float(item)
        return (not _is_excluded(item)) and _onepiece_title_matches(
            title, meta['base_number'], meta['is_manga'], meta['is_special'],
            meta['is_parallel'], price, meta['rarity'], meta['name'],
        )

    total = OnePieceCardPrice.objects.count()
    stats = _clean_generic(OnePieceCardPrice, OnePieceCard, total, validator, meta_of, dry_run)
    _log(f"[원피스] 스캔 {stats['scanned']}건 / 오염행 {stats['rows_touched']}건 "
         f"(수정 {stats['rows_updated']} / 삭제 {stats['rows_deleted']}) / 제거된 상품 {stats['items_removed']}건")

    refreshed = _refresh_card_caches(OnePieceCard, OnePieceCardPrice, stats['cards_needing_cache_refresh'], dry_run)
    _log(f"[원피스] 캐시 갱신 대상 카드 {refreshed}장")


def clean_digimon(dry_run):
    _log("\n" + "=" * 70)
    _log(f"[디지몬] 정리 시작 (dry_run={dry_run})")
    meta_of = {
        c.id: {
            'card_number': c.card_number,
            'is_parallel': c.is_parallel,
            'is_scarce': c.is_scarce,
            'is_special': c.is_special,
        }
        for c in DigimonCard.objects.only('id', 'card_number', 'is_parallel', 'is_scarce', 'is_special')
    }

    def validator(item, meta):
        title = _clean_title(item.get('title', ''))
        return (not _is_excluded(item)) and _digimon_item_is_valid(
            title, meta['card_number'], meta['is_parallel'], meta['is_scarce'], meta['is_special'],
        )

    total = DigimonCardPrice.objects.count()
    stats = _clean_generic(DigimonCardPrice, DigimonCard, total, validator, meta_of, dry_run)
    _log(f"[디지몬] 스캔 {stats['scanned']}건 / 오염행 {stats['rows_touched']}건 "
         f"(수정 {stats['rows_updated']} / 삭제 {stats['rows_deleted']}) / 제거된 상품 {stats['items_removed']}건")

    refreshed = _refresh_card_caches(DigimonCard, DigimonCardPrice, stats['cards_needing_cache_refresh'], dry_run)
    _log(f"[디지몬] 캐시 갱신 대상 카드 {refreshed}장")


def main():
    args = sys.argv[1:]
    dry_run = '--apply' not in args
    games = [a.lower() for a in args if not a.startswith('--')] or ['pokemon', 'onepiece', 'digimon']

    _log("=" * 70)
    _log("오염 가격 데이터 정리")
    _log(f"모드: {'미리보기(DRY RUN, DB 변경 없음)' if dry_run else '⚠️  실제 적용'}")
    _log(f"대상: {games}")
    _log("=" * 70)

    t0 = time.time()
    if 'pokemon' in games:
        clean_pokemon(dry_run)
    if 'onepiece' in games:
        clean_onepiece(dry_run)
    if 'digimon' in games:
        clean_digimon(dry_run)

    _log("\n" + "=" * 70)
    _log(f"전체 완료: {time.time()-t0:.0f}초")
    if dry_run:
        _log("(미리보기 모드였습니다 — 실제 적용하려면 --apply 옵션을 붙여서 다시 실행하세요)")
    _log("=" * 70)


if __name__ == '__main__':
    main()
