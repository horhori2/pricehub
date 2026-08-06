"""
pricehub/store_price_check.py

card-controltower(네이버 스마트스토어 매장 관리 백엔드)가 알려주는 "지금 스토어에 실제로
반영된 가격"과 PriceHub 자체 판매가(selling_price)를 매장별로 비교하는 로직. "오늘의 작업"
흐름(수정가격조회→하락확인→스토어반영)이 끝난 뒤, 그 결과를 PriceHub 쪽에서 검수용으로
보기 위해 만들어졌다(2026-08-06, 실 서버 반영 결과 기준 요청).

세 갈래로 나눈다:
- drops/rises: card-controltower가 계산한 priceChangeStatus(스토어 현재가 vs 마지막으로
  가져간 PriceHub 판매가)를 그대로 따른다.
- unregistered: shop_product_code 기준으로 PriceHub 카탈로그에서 매칭되는 카드를 못 찾은
  것. PriceHub가 아예 취급하지 않는 카드 종류(홀로라이브/니케/쿠키런 등)는 매칭 모델 자체가
  없어 전부 여기로 떨어진다 — "카탈로그 미보유"가 자연스럽게 포함되는 정의라 별도 분기가
  필요 없다.
"""
from .models import Card, OnePieceCard, DigimonCard, CardPrice, OnePieceCardPrice, DigimonCardPrice

_DROP_STATUSES = {'SLIGHT_DROP', 'MODERATE_DROP', 'SEVERE_DROP'}


# card-controltower의 CardType enum 실제 값 기준(2026-08-06 확인, CardType.java) — "ONEPIECE"가
# 아니라 "ONE_PIECE"다. 여기서 한 번 틀렸다가 실제 데이터로 검증하는 과정에서 원피스 카드
# 2275건이 전부 매칭 실패로 "미등록" 처리되는 걸 보고 발견함 — 키 하나 오타로 카테고리
# 전체가 조용히 잘못 분류되는 사례라 남겨둠.
_GAME_MODEL_BY_CARD_TYPE = {
    'POKEMON': Card,
    'ONE_PIECE': OnePieceCard,
    'DIGIMON': DigimonCard,
}
_GAME_LABEL_BY_CARD_TYPE = {
    'POKEMON': '포켓몬',
    'ONE_PIECE': '원피스',
    'DIGIMON': '디지몬',
    'HOLOLIVE': '홀로라이브',
    'NIKKE': '니케',
    'COOKIERUN': '쿠키런',
    'OTHER': '기타',
}
_BASE_URL_BY_CARD_TYPE = {
    'POKEMON': '/pokemon/kr',
    'ONE_PIECE': '/onepiece/kr',
    'DIGIMON': '/digimon/kr',
}

# 카드 종류별로 추가 표시할 태그 배지 계산에 필요한 필드 — views.py의 _pokemon_kr_tags/
# _digimon_tags와 같은 규칙이지만, 여기선 모델 인스턴스가 아니라 .values() dict라 직접 계산한다.
_EXTRA_TAG_FIELDS_BY_CARD_TYPE = {
    'POKEMON': ('is_teukil',),
    'DIGIMON': ('is_parallel', 'is_scarce', 'is_special'),
}

_PRICE_MODEL_BY_CARD_TYPE = {
    'POKEMON': CardPrice,
    'ONE_PIECE': OnePieceCardPrice,
    'DIGIMON': DigimonCardPrice,
}


def fetch_market_raw_data(rows):
    """
    현재 화면에 보이는 행(페이지 분량)들의 pricehub_key별 최신 판매처 목록(raw_data) —
    카드 목록 페이지(_card_list_view)의 사이드 패널과 동일한 패턴. 전체가 아니라
    "지금 보이는 페이지"만 조회해서 무거워지지 않게 한다.

    키를 pricehub_id(순수 정수)가 아니라 pricehub_key(cardType 접두사 포함)로 쓰는 이유는
    categorize()의 pricehub_key 주석 참고 — 여기서도 안 맞추면 결국 같은 충돌이 재현된다.
    """
    ids_by_type = {}
    for r in rows:
        if r.get('pricehub_id') and r.get('cardType') in _PRICE_MODEL_BY_CARD_TYPE:
            ids_by_type.setdefault(r['cardType'], set()).add(r['pricehub_id'])

    raw_by_key = {}
    for card_type, ids in ids_by_type.items():
        price_model = _PRICE_MODEL_BY_CARD_TYPE[card_type]
        for cp in (
            price_model.objects.filter(card_id__in=ids)
            .exclude(raw_data={}).exclude(raw_data=[])
            .order_by('-collected_at')
            .values('card_id', 'raw_data')
        ):
            key = f"{card_type}:{cp['card_id']}"
            if key not in raw_by_key:
                raw_by_key[key] = cp['raw_data']
    return raw_by_key


def _tag_badges(card_type, row):
    if card_type == 'POKEMON':
        return [('특일', 'tag-teukil')] if row.get('is_teukil') else []
    if card_type == 'DIGIMON':
        tags = []
        if row.get('is_parallel'):
            tags.append(('패러렐', 'tag-parallel'))
        if row.get('is_scarce'):
            tags.append(('희소', 'tag-scarce'))
        if row.get('is_special'):
            tags.append(('스페셜', 'tag-special'))
        return tags
    return []


def _bulk_pricehub_lookup(cards):
    """cardType별로 shop_product_code→PriceHub 카드를 한 번씩만 조회(카드 수만큼 N+1 방지)."""
    codes_by_type = {}
    for c in cards:
        card_type = c.get('cardType')
        code = c.get('sellerProductCode')
        if card_type in _GAME_MODEL_BY_CARD_TYPE and code:
            codes_by_type.setdefault(card_type, set()).add(code)

    lookup = {}
    for card_type, codes in codes_by_type.items():
        model = _GAME_MODEL_BY_CARD_TYPE[card_type]
        fields = ('id', 'shop_product_code', 'selling_price', 'name', 'image_url') \
            + _EXTRA_TAG_FIELDS_BY_CARD_TYPE.get(card_type, ())
        rows = model.objects.filter(shop_product_code__in=codes).values(*fields)
        for row in rows:
            lookup[(card_type, row['shop_product_code'])] = row
    return lookup


def _store_image_index(all_store_cards):
    """{store: {sellerProductCode: imageUrl}} — 스토어별 카드 이미지 인덱스(부산/광주 이미지 나란히 표시용)."""
    index = {}
    for store, cards in all_store_cards.items():
        idx = {}
        for c in cards:
            code = c.get('sellerProductCode')
            if code:
                idx[code] = c.get('imageUrl')
        index[store] = idx
    return index


def categorize(all_store_cards, primary_store):
    """
    all_store_cards: {store: GET /api/cards 결과} — 설정된 전 매장(현재 busan/gwangju) 데이터.
    primary_store: 하락/상승/미등록 분류 기준이 되는 매장(지금 보고 있는 탭).

    각 행에 PriceHub 쪽 매칭 정보(pricehub_price/pricehub_name/set_price_url, 매칭 없으면
    전부 None)와 스토어별 이미지(store_images: {store: url})를 덧붙인 dict로 돌려준다 —
    템플릿에서 바로 렌더링할 수 있게. 분류(하락/상승/미등록) 자체는 primary_store 기준
    priceChangeStatus를 그대로 따른다 — 다른 매장 이미지는 "같은 카드가 그쪽엔 어떻게
    등록돼 있나" 참고용일 뿐, 분류에는 관여하지 않는다.
    """
    cards = all_store_cards[primary_store]
    image_index = _store_image_index(all_store_cards)
    lookup = _bulk_pricehub_lookup(cards)
    drops, rises, unregistered = [], [], []

    for c in cards:
        card_type = c.get('cardType')
        code = c.get('sellerProductCode')
        match = lookup.get((card_type, code))

        row = dict(c)
        row['game_label'] = _GAME_LABEL_BY_CARD_TYPE.get(card_type, card_type)
        row['store_images'] = {
            store: idx.get(code) for store, idx in image_index.items()
        }

        if match:
            base_url = _BASE_URL_BY_CARD_TYPE[card_type]
            row['pricehub_id'] = match['id']
            # POKEMON/ONE_PIECE/DIGIMON은 서로 다른 Django 모델(각자 독립된 auto-increment
            # PK)이라, 같은 정수 id가 게임이 다른 카드를 가리키는 경우가 실제로 있다(2026-08-06,
            # 8페이지에서 포켓몬 id=7142와 디지몬 id=7142가 동시에 나타나 클릭 시 엉뚱한 카드의
            # 판매처 목록이 뜨는 버그로 발견). DOM id/JS 키로는 반드시 이 pricehub_key(카드
            # 종류 접두사 포함)를 쓰고, pricehub_id는 실제 PriceHub URL(/set-price/ 등)에만 쓴다.
            row['pricehub_key'] = f"{card_type}:{match['id']}"
            row['pricehub_price'] = match['selling_price']
            row['pricehub_name'] = match['name']
            row['pricehub_image_url'] = match.get('image_url')
            row['set_price_url'] = f"{base_url}/cards/{match['id']}/set-price/"
            row['tag_badges'] = _tag_badges(card_type, match)
        else:
            row['pricehub_id'] = None
            row['pricehub_key'] = None
            row['pricehub_price'] = None
            row['pricehub_name'] = None
            row['pricehub_image_url'] = None
            row['set_price_url'] = None
            row['tag_badges'] = []

        status = c.get('priceChangeStatus')
        if match is None:
            unregistered.append(row)
        elif status in _DROP_STATUSES:
            drops.append(row)
        elif status == 'INCREASED':
            rises.append(row)

    # 하락은 더 많이 떨어진 게, 상승은 더 많이 오른 게 먼저 보이게.
    drops.sort(key=lambda r: r.get('priceChangeRate') if r.get('priceChangeRate') is not None else 0)
    rises.sort(key=lambda r: r.get('priceChangeRate') if r.get('priceChangeRate') is not None else 0, reverse=True)
    unregistered.sort(key=lambda r: r.get('productName') or '')

    return drops, rises, unregistered
