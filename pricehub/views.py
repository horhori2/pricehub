"""
pricehub/views.py

판매가 관리 대시보드.
- 홈: 게임(포켓몬/원피스/디지몬) × 언어(한글판/일본판) 선택
- 각 카테고리별: 확장팩 목록 → 카드 목록 → 카드 상세 + 판매가 설정
"""
import json
import re

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.db.models import OuterRef, Subquery

from django.utils import timezone
from datetime import timedelta

from .models import (
    Expansion, Card, CardPrice,
    OnePieceExpansion, OnePieceCard, OnePieceCardPrice,
    JapanExpansion, JapanCard, JapanCardPrice,
)


OUR_SHOPS = ['화성스토어-TCG-', '카드 베이스']


# ════════════════════════════════════════════════════════════════
# 카테고리 설정 레지스트리
# ════════════════════════════════════════════════════════════════

CATEGORY_CONFIGS = {
    'pokemon_kr': {
        'label': '포켓몬 한글판',
        'expansion_model': Expansion,
        'card_model': Card,
        'price_model': CardPrice,
        'base_url': '/pokemon/kr',
        'high_rarity_list': "['SAR','CSR','UR','MUR','BWR']",
        'bulk_issues_high_rarity_list': "['SAR','CSR','HR','UR','MUR','BWR']",
        'card_detail_template': 'dashboard/card_detail.html',
        'card_type_key': 'pokemon_kr',
        'favorites_url': '/pokemon/kr/favorites/',
        'toggle_favorite_url_base': '/pokemon/kr/cards/',
    },
    'pokemon_jp': {
        'label': '포켓몬 일본판',
        'expansion_model': JapanExpansion,
        'card_model': JapanCard,
        'price_model': JapanCardPrice,
        'base_url': '/pokemon/jp',
        'card_detail_template': 'dashboard/card_detail_jp.html',
        'card_type_key': 'pokemon_jp',
    },
    'onepiece_kr': {
        'label': '원피스 한글판',
        'expansion_model': OnePieceExpansion,
        'card_model': OnePieceCard,
        'price_model': OnePieceCardPrice,
        'base_url': '/onepiece/kr',
        'high_rarity_list': "['SP-SEC','SP-SR','SEC','SL']",
        'bulk_issues_high_rarity_list': "['SP-SEC','SP-SR','SEC','SL']",
        'card_detail_template': 'dashboard/card_detail.html',
        'card_type_key': 'onepiece_kr',
        'favorites_url': '/onepiece/kr/favorites/',
        'toggle_favorite_url_base': '/onepiece/kr/cards/',
    },
}

def _cfg(key):
    return CATEGORY_CONFIGS[key]

def _url(key, path=''):
    return _cfg(key)['base_url'] + path


# ════════════════════════════════════════════════════════════════
# 권한
# ════════════════════════════════════════════════════════════════

def is_staff(user):
    return user.is_active and user.is_staff

staff_required = user_passes_test(is_staff, login_url='/login/')


# ════════════════════════════════════════════════════════════════
# 로그인/로그아웃
# ════════════════════════════════════════════════════════════════

def dashboard_login(request):
    error = None
    if request.method == 'POST':
        user = authenticate(request,
                            username=request.POST.get('username'),
                            password=request.POST.get('password'))
        if user and user.is_staff:
            login(request, user)
            return redirect('/')
        error = '아이디 또는 비밀번호가 올바르지 않습니다.'
    return render(request, 'dashboard/login.html', {'error': error})


def dashboard_logout(request):
    logout(request)
    return redirect('/login/')


# ════════════════════════════════════════════════════════════════
# 홈 (카테고리 선택)
# ════════════════════════════════════════════════════════════════

@staff_required
def home(request):
    categories = [
        {
            'game': '포켓몬',
            'game_key': 'pokemon',
            'icon': '🎴',
            'regions': [
                {
                    'label': '한글판',
                    'key': 'kr',
                    'url': _url('pokemon_kr', '/expansions/'),
                    'total': Card.objects.count(),
                    'unpriced': Card.objects.filter(selling_price=0).count(),
                },
                {
                    'label': '일본판',
                    'key': 'jp',
                    'url': _url('pokemon_jp', '/expansions/'),
                    'total': JapanCard.objects.count(),
                    'unpriced': JapanCard.objects.filter(selling_price=0).count(),
                },
            ],
        },
        {
            'game': '원피스',
            'game_key': 'onepiece',
            'icon': '⚓',
            'regions': [
                {
                    'label': '한글판',
                    'key': 'kr',
                    'url': _url('onepiece_kr', '/expansions/'),
                    'total': OnePieceCard.objects.count(),
                    'unpriced': OnePieceCard.objects.filter(selling_price=0).count(),
                },
            ],
        },
        {
            'game': '디지몬',
            'game_key': 'digimon',
            'icon': '🦕',
            'regions': [],
            'coming_soon': True,
        },
    ]
    return render(request, 'dashboard/home.html', {'categories': categories})


# ════════════════════════════════════════════════════════════════
# 공통 헬퍼 — 가격 데이터
# ════════════════════════════════════════════════════════════════

def _load_raw_data(price_model, expansion_code=None, rarities=None):
    """카드별 최신 raw_data 1건씩 반환 (메모리 최적화)"""
    qs = price_model.objects.exclude(raw_data={}).exclude(raw_data=[])
    if expansion_code:
        qs = qs.filter(card__expansion__code=expansion_code)
    if rarities:
        qs = qs.filter(card__rarity__in=rarities)

    seen_cards = {}
    for cp in qs.order_by('-collected_at').values('card_id', 'id'):
        if cp['card_id'] not in seen_cards:
            seen_cards[cp['card_id']] = cp['id']

    return list(
        price_model.objects.filter(id__in=seen_cards.values())
                            .values_list('raw_data', flat=True)
    )


def _collect_mall_names(price_model, expansion_code=None, limit=500):
    """raw_data에서 mallName 빈도 집계"""
    qs = price_model.objects.exclude(raw_data={}).exclude(raw_data=[])
    if expansion_code:
        qs = qs.filter(card__expansion__code=expansion_code)

    seen_cards = {}
    for cp in qs.order_by('-collected_at').values('card_id', 'id'):
        if cp['card_id'] not in seen_cards:
            seen_cards[cp['card_id']] = cp['id']
        if len(seen_cards) >= limit:
            break

    name_count = {}
    for raw in price_model.objects.filter(id__in=seen_cards.values()).values_list('raw_data', flat=True):
        if isinstance(raw, list):
            for item in raw:
                name = item.get('mallName', '').strip()
                if name:
                    name_count[name] = name_count.get(name, 0) + 1

    return sorted(name_count.items(), key=lambda x: -x[1])


def _calc_shop_stats(raw_data_list):
    """raw_data 리스트에서 샵별 통계 집계"""
    shops = {}
    total_prices = []

    for raw in raw_data_list:
        if isinstance(raw, dict):
            raw = [raw] if raw else []
        if not isinstance(raw, list):
            continue
        for item in raw:
            mall = item.get('mallName', '').strip()
            try:
                price = int(float(item.get('lprice', 0)))
            except (ValueError, TypeError):
                continue
            if not mall or price <= 0:
                continue
            if mall not in shops:
                shops[mall] = {'count': 0, 'prices': []}
            shops[mall]['count'] += 1
            shops[mall]['prices'].append(price)
            total_prices.append(price)

    overall_avg = round(sum(total_prices) / len(total_prices)) if total_prices else 0

    result = []
    for mall, data in shops.items():
        prices = data['prices']
        avg = round(sum(prices) / len(prices))
        diff = avg - overall_avg
        diff_pct = round((diff / overall_avg) * 100, 1) if overall_avg else 0
        result.append({
            'name': mall,
            'count': data['count'],
            'avg': avg,
            'min': min(prices),
            'max': max(prices),
            'diff': diff,
            'diff_pct': diff_pct,
            'cheaper': diff < 0,
        })

    result.sort(key=lambda x: -x['count'])
    return result, overall_avg


def _parse_market_items(latest_price_obj):
    """CardPrice.raw_data에서 market_items + stats 반환"""
    market_items = []
    if latest_price_obj and latest_price_obj.raw_data:
        raw = latest_price_obj.raw_data
        if isinstance(raw, list):
            market_items = raw
        elif isinstance(raw, dict) and raw:
            market_items = [raw]

    for item in market_items:
        item['clean_title'] = re.sub(r'<[^>]+>', '', item.get('title', ''))
        item['price_int'] = int(float(item.get('lprice', 0)))

    our_items = []
    for shop in OUR_SHOPS:
        for item in market_items:
            if item.get('mallName') == shop:
                our_items.append(item)
                break

    other_items = sorted(
        [i for i in market_items if i.get('mallName') not in OUR_SHOPS],
        key=lambda x: x['price_int'],
    )

    market_items = our_items + other_items
    prices = [item['price_int'] for item in market_items if item['price_int'] > 0]
    return market_items, _calc_stats(prices)


def _calc_stats(prices):
    if not prices:
        return {}
    sorted_p = sorted(prices)
    return {
        'min': sorted_p[0],
        'max': sorted_p[-1],
        'avg': round(sum(sorted_p) / len(sorted_p)),
        'median': sorted_p[len(sorted_p) // 2],
        'count': len(sorted_p),
    }


def _set_price(model_class, pk, request):
    """공통 판매가 저장 (AJAX POST)"""
    obj = get_object_or_404(model_class, pk=pk)
    try:
        data = json.loads(request.body)
        price = int(data.get('selling_price', 0))
        if price < 0:
            return JsonResponse({'success': False, 'error': '올바른 가격을 입력하세요.'})
        obj.selling_price = price if price > 0 else None
        obj.save(update_fields=['selling_price'])
        return JsonResponse({'success': True, 'selling_price': obj.selling_price})
    except (ValueError, TypeError) as e:
        return JsonResponse({'success': False, 'error': str(e)})


def _price_history_json(card, price_model_relation):
    """최근 1주일 가격 이력 JSON"""
    one_week_ago = timezone.now() - timedelta(days=7)
    history = list(
        price_model_relation
        .filter(collected_at__gte=one_week_ago)
        .order_by('collected_at')
        .values('collected_at', 'raw_data')
    )
    return json.dumps(
        [
            {
                'date': p['collected_at'].strftime('%m/%d %H:%M'),
                'raw_data': p['raw_data'] if isinstance(p['raw_data'], list) else [],
            }
            for p in history
        ],
        ensure_ascii=False,
    )


def _get_rarities(card_model, expansion_code=None):
    qs = card_model.objects.values_list('rarity', flat=True).distinct().order_by('rarity')
    if expansion_code:
        qs = qs.filter(expansion__code=expansion_code)
    return list(qs)


# ════════════════════════════════════════════════════════════════
# 공통 뷰 로직 — expansion_list / card_list / card_search
# ════════════════════════════════════════════════════════════════

def _expansion_list_view(request, cfg_key, extra_ctx=None):
    cfg = _cfg(cfg_key)
    expansion_model = cfg['expansion_model']
    card_model = cfg['card_model']
    base_url = cfg['base_url']
 
    expansions = list(expansion_model.objects.order_by('-release_date', '-created_at'))
    for e in expansions:
        e.card_count = e.cards.count()
        e.unpriced_count = e.cards.filter(selling_price=0).count()
 
    # 하락 대기 카드 수
    drop_qs = card_model.objects.filter(modified_price__gt=0, selling_price__gt=0)
    drop_count = sum(1 for c in drop_qs if c.modified_price < c.selling_price)
 
    ctx = {
        'expansions': expansions,
        'total_cards': sum(e.card_count for e in expansions),
        'total_unpriced': sum(e.unpriced_count for e in expansions),
        'total_drop': drop_count,                              # ← 신규
        'base_url': base_url,
        'title': cfg['label'],
        'breadcrumb': [('홈', '/'), (cfg['label'], None)],
        'card_detail_base_url': f'{base_url}/cards/',
    }
    if extra_ctx:
        ctx.update(extra_ctx)
    return render(request, 'dashboard/expansion_list.html', ctx)


def _card_list_view(request, cfg_key, code, extra_ctx=None):
    cfg = _cfg(cfg_key)
    expansion_model = cfg['expansion_model']
    card_model = cfg['card_model']
    price_model = cfg['price_model']
    base_url = cfg['base_url']

    expansion = get_object_or_404(expansion_model, code=code)
    latest_price_qs = price_model.objects.filter(card=OuterRef('pk')).order_by('-collected_at')
    cards = (
        card_model.objects.filter(expansion=expansion)
        .annotate(
            latest_market_price=Subquery(latest_price_qs.values('price')[:1]),
            latest_collected_at=Subquery(latest_price_qs.values('collected_at')[:1]),
        )
        .order_by('card_number')
    )

    filter_type = request.GET.get('filter', 'all')
    if filter_type == 'unpriced':
        cards = cards.filter(selling_price=0)
    elif filter_type == 'priced':
        cards = cards.filter(selling_price__gt=0)

    # ── 즐겨찾기 context (favorites_url이 있는 카테고리만)
    fav_ctx = {}
    if 'favorites_url' in cfg:
        fav_ctx = {
            'favorites_url': cfg['favorites_url'],
            'toggle_favorite_url_base': cfg['toggle_favorite_url_base'],
            'favorite_count': card_model.objects.filter(is_favorite=True).count(),
        }

    ctx = {
        'expansion': expansion,
        'cards': cards,
        'filter_type': filter_type,
        'breadcrumb': [
            ('홈', '/'),
            (cfg['label'], f'{base_url}/expansions/'),
            (expansion.name, None),
        ],
        'detail_base_url': f'{base_url}/cards',
        'back_url': f'{base_url}/expansions/',
        **fav_ctx,
    }
    if extra_ctx:
        ctx.update(extra_ctx)
    return render(request, 'dashboard/card_list.html', ctx)


def _card_search_view(request, card_model):
    q = request.GET.get('name', '').strip()
    page_size = min(int(request.GET.get('page_size', 30)), 50)

    if not q:
        return JsonResponse({'results': []})

    cards = (
        card_model.objects
        .filter(name__icontains=q)
        .select_related('expansion')
        .order_by('expansion__release_date', 'card_number')
        [:page_size]
    )

    results = []
    for card in cards:
        latest = card.prices.first()
        results.append({
            'id': card.id,
            'name': card.name,
            'rarity': card.rarity,
            'card_number': card.card_number,
            'image_url': card.image_url,
            'selling_price': card.selling_price if card.selling_price != 0 else None,
            'latest_price': float(latest.price) if latest else None,
            'expansion': {
                'code': card.expansion.code,
                'name': card.expansion.name,
            },
        })

    return JsonResponse({'results': results})


# ════════════════════════════════════════════════════════════════
# 공통 뷰 로직 — bulk_price / bulk_run / bulk_issues / approve / edit
# ════════════════════════════════════════════════════════════════

def _bulk_price_view(request, cfg_key):
    cfg = _cfg(cfg_key)
    card_model = cfg['card_model']
    price_model = cfg['price_model']
    base_url = cfg['base_url']

    expansion_code = request.GET.get('expansion', '')
    selected_rarities = request.GET.getlist('rarities')

    selected_expansion = None
    if expansion_code:
        selected_expansion = cfg['expansion_model'].objects.filter(code=expansion_code).first()

    mall_names = _collect_mall_names(price_model, expansion_code=expansion_code or None)
    expansions = list(cfg['expansion_model'].objects.order_by('-release_date', '-created_at'))
    all_rarities = _get_rarities(card_model, expansion_code or None)

    raw_list = _load_raw_data(price_model, expansion_code=expansion_code or None, rarities=selected_rarities or None)
    shop_stats, overall_avg = _calc_shop_stats(raw_list)

    # ── 하락 대기 카드 수 (modified_price > 0 이고 modified_price < selling_price)
    drop_qs = card_model.objects.filter(modified_price__gt=0, selling_price__gt=0)
    drop_pending = sum(1 for c in drop_qs if c.modified_price < c.selling_price)
    # selling_price 미설정(0)인데 modified_price가 있는 경우
    new_pending = card_model.objects.filter(modified_price__gt=0, selling_price=0).count()
    needs_review = drop_pending + new_pending

    return render(request, 'dashboard/bulk_price.html', {
        'mall_names': json.dumps(mall_names),
        'mall_names_display': mall_names,
        'expansions': expansions,
        'needs_review': needs_review,
        'shop_stats_json': json.dumps(shop_stats, ensure_ascii=False),
        'shop_stats': shop_stats,
        'overall_avg': overall_avg,
        'selected_expansion': selected_expansion,
        'expansion_code': expansion_code,
        'all_rarities': all_rarities,
        'selected_rarities': selected_rarities,
        'selected_rarities_json': json.dumps(selected_rarities),
        'breadcrumb': [
            ('홈', '/'),
            (cfg['label'], f'{base_url}/expansions/'),
            ('일괄 판매가 설정', None),
        ],
        'config': {
            'label': cfg['label'],
            'expansion_list_url': f'{base_url}/expansions/',
            'bulk_price_url': f'{base_url}/bulk-price/',
            'bulk_run_url': f'{base_url}/bulk-price/run/',
            'bulk_issues_url': f'{base_url}/bulk-price/issues/',
            'high_rarity_list': cfg.get('high_rarity_list', '[]'),
        },
    })


def _bulk_run_view(request, cfg_key):
    """
    [업그레이드 로직]
    1. 가격 추출 성공 → modified_price 항상 저장
    2. 신규(selling_price=0)  → selling_price도 바로 저장
    3. 유지/상승              → selling_price 바로 업데이트
    4. 하락                   → modified_price만 저장, selling_price 유지 (하락 대기)
    5. 매칭 없음              → 변경 없음 (needs_review)
    """
    cfg = _cfg(cfg_key)
    card_model = cfg['card_model']
    price_model = cfg['price_model']

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': '잘못된 요청입니다.'}, status=400)

    priorities      = [p.strip() for p in data.get('priorities', []) if p.strip()]
    expansion_code  = data.get('expansion_code', '').strip()
    skip_priced     = data.get('skip_priced', False)
    rarities        = data.get('rarities', [])
    min_price_floor = int(data.get('min_price', 0) or 0)
    fallback_mode   = data.get('fallback_mode', '')  # 'avg', 'max', ''
    overwrite       = data.get('overwrite', False)    # True면 하락도 강제 반영

    if not priorities:
        return JsonResponse({'error': '우선순위를 1개 이상 설정해주세요.'}, status=400)

    cards_qs = card_model.objects.select_related('expansion').order_by('expansion__code', 'card_number')
    if expansion_code:
        cards_qs = cards_qs.filter(expansion__code=expansion_code)
    if rarities:
        cards_qs = cards_qs.filter(rarity__in=rarities)

    latest_price_id_qs = (
        price_model.objects
        .filter(card=OuterRef('pk'))
        .exclude(raw_data={})
        .exclude(raw_data=[])
        .order_by('-collected_at')
        .values('id')[:1]
    )
    cards_list = list(cards_qs.annotate(latest_price_id=Subquery(latest_price_id_qs)))

    price_ids = [c.latest_price_id for c in cards_list if c.latest_price_id]
    price_map = {cp.id: cp.raw_data for cp in price_model.objects.filter(id__in=price_ids)}

    to_update  = []   # bulk_update 대상
    skipped    = []   # skip_priced로 건너뜀
    drop_wait  = []   # 하락 대기 card id
    no_match   = []   # raw_data 매칭 없음

    result_detail = {'new': 0, 'same_or_up': 0, 'drop': 0}

    for card in cards_list:
        if skip_priced and card.selling_price != 0:
            skipped.append(card.id)
            continue

        raw = price_map.get(card.latest_price_id, [])
        if isinstance(raw, dict):
            raw = [raw]

        # ── 우선순위 매칭
        matched_price = None
        for mall_name in priorities:
            for item in raw:
                if item.get('mallName', '') == mall_name:
                    try:
                        price = int(float(item.get('lprice', 0)))
                        if price > 0:
                            matched_price = price
                    except (ValueError, TypeError):
                        pass
                    break
            if matched_price:
                break

        # ── 폴백
        if matched_price is None and fallback_mode in ('avg', 'max'):
            prices = []
            for item in raw:
                try:
                    p = int(float(item.get('lprice', 0)))
                    if p > 0:
                        prices.append(p)
                except (ValueError, TypeError):
                    pass
            if prices:
                raw_price = (sum(prices) / len(prices)) if fallback_mode == 'avg' else max(prices)
                matched_price = round(raw_price / 100) * 100

        # ── 매칭 실패
        if matched_price is None:
            no_match.append(card.id)
            continue

        # ── 최저가 하한선
        if min_price_floor > 0 and matched_price < min_price_floor:
            matched_price = min_price_floor

        old_selling = int(card.selling_price) if card.selling_price else 0

        # modified_price는 항상 저장
        card.modified_price = matched_price

        if old_selling == 0:
            # 신규 설정 → selling_price 바로 반영
            card.selling_price = matched_price
            result_detail['new'] += 1

        elif overwrite or matched_price >= old_selling:
            # 유지 또는 상승 (또는 강제 덮어쓰기) → selling_price 바로 반영
            card.selling_price = matched_price
            result_detail['same_or_up'] += 1

        else:
            # 하락 → selling_price 건드리지 않음, 하락 대기
            drop_wait.append(card.id)
            result_detail['drop'] += 1

        to_update.append(card)

    if to_update:
        card_model.objects.bulk_update(to_update, ['selling_price', 'modified_price'], batch_size=200)

    applied_count = result_detail['new'] + result_detail['same_or_up']

    return JsonResponse({
        'success': True,
        'total': len(cards_list),
        'set_count': applied_count,
        'skipped_count': len(skipped),
        'needs_review_count': len(no_match),
        'needs_review_ids': no_match[:100],
        'drop_count': result_detail['drop'],
        'drop_ids': drop_wait[:100],
        'detail': result_detail,
        'message': (
            f"완료: 반영 {applied_count}개 "
            f"(신규 {result_detail['new']} / 유지·상승 {result_detail['same_or_up']}) | "
            f"하락 대기 {result_detail['drop']}개 | 매칭 없음 {len(no_match)}개 | 스킵 {len(skipped)}개"
        ),
    })


def _bulk_issues_view(request, cfg_key):
    cfg = _cfg(cfg_key)
    card_model  = cfg['card_model']
    price_model = cfg['price_model']
    base_url    = cfg['base_url']
 
    mode               = request.GET.get('mode', 'drop')       # ← 신규
    expansion_code     = request.GET.get('expansion', '')
    selected_rarities  = request.GET.getlist('rarities')
    sort               = request.GET.get('sort', 'drop_pct')
 
    all_rarities = _get_rarities(card_model, expansion_code or None)
    expansions   = cfg['expansion_model'].objects.order_by('-release_date')
 
    # ── 판매가 미설정 모드 ────────────────────────────
    if mode == 'unpriced':
        qs = card_model.objects.filter(selling_price=0).select_related('expansion')
        if expansion_code:
            qs = qs.filter(expansion__code=expansion_code)
        if selected_rarities:
            qs = qs.filter(rarity__in=selected_rarities)
        if sort == 'name':
            qs = qs.order_by('name')
        else:
            qs = qs.order_by('expansion__code', 'card_number')
 
        # 사이드패널용 raw_data
        card_ids = [c.pk for c in qs]
        seen_raw = {}
        for cp in (
            price_model.objects.filter(card_id__in=card_ids)
            .exclude(raw_data={}).exclude(raw_data=[])
            .order_by('-collected_at')
            .values('card_id', 'raw_data')
        ):
            if cp['card_id'] not in seen_raw:
                seen_raw[cp['card_id']] = cp['raw_data']
 
        return render(request, 'dashboard/bulk_issues.html', {
            'mode':                'unpriced',
            'cards':               qs,           # unpriced 모드는 cards 변수 사용
            'drop_cards':          [],
            'expansions':          expansions,
            'expansion_code':      expansion_code,
            'selected_expansion':  expansion_code,
            'sort':                sort,
            'total_count':         qs.count(),
            'avg_drop_pct':        0,
            'max_drop':            0,
            'all_rarities':        all_rarities,
            'selected_rarities':   selected_rarities,
            'selected_rarities_json': json.dumps(selected_rarities),
            'card_raw_json':       json.dumps(seen_raw, ensure_ascii=False),
            'breadcrumb': [
                ('홈', '/'),
                (cfg['label'], f'{base_url}/expansions/'),
                ('일괄 판매가 설정', f'{base_url}/bulk-price/'),
                ('판매가 미설정 목록', None),
            ],
            'config': {
                'label':            cfg['label'],
                'bulk_price_url':   f'{base_url}/bulk-price/',
                'bulk_issues_url':  f'{base_url}/bulk-price/issues/',
                'approve_url':      f'{base_url}/bulk-price/approve/',
                'edit_url':         f'{base_url}/bulk-price/edit/',
                'set_price_url_prefix': f'{base_url}/cards/',
                'high_rarity_list': cfg.get('bulk_issues_high_rarity_list', cfg.get('high_rarity_list', '[]')),
                'unpriced_url':     f'{base_url}/bulk-price/issues/?mode=unpriced',
                'drop_url':         f'{base_url}/bulk-price/issues/?mode=drop',
            },
        })
 
    # ── 하락 대기 모드 (기존 로직) ───────────────────
    qs = card_model.objects.filter(
        modified_price__gt=0,
        selling_price__gt=0,
    ).select_related('expansion')
 
    if expansion_code:
        qs = qs.filter(expansion__code=expansion_code)
    if selected_rarities:
        qs = qs.filter(rarity__in=selected_rarities)
 
    drop_cards = []
    for card in qs:
        mod  = int(card.modified_price)
        sell = int(card.selling_price)
        if mod < sell:
            drop_amt = sell - mod
            drop_pct = round((drop_amt / sell) * 100, 1)
            drop_cards.append({
                'card':           card,
                'modified_price': mod,
                'selling_price':  sell,
                'drop_amt':       drop_amt,
                'drop_pct':       drop_pct,
            })
 
    if sort == 'drop_pct':
        drop_cards.sort(key=lambda x: -x['drop_pct'])
    elif sort == 'drop_amt':
        drop_cards.sort(key=lambda x: -x['drop_amt'])
    else:
        drop_cards.sort(key=lambda x: getattr(x['card'], 'name_kr', None) or x['card'].name or '')
 
    total_count   = len(drop_cards)
    avg_drop_pct  = round(sum(d['drop_pct'] for d in drop_cards) / total_count, 1) if total_count else 0
    max_drop      = max((d['drop_pct'] for d in drop_cards), default=0)
 
    drop_card_ids = [d['card'].pk for d in drop_cards]
    seen_raw = {}
    for cp in (
        price_model.objects.filter(card_id__in=drop_card_ids)
        .exclude(raw_data={}).exclude(raw_data=[])
        .order_by('-collected_at')
        .values('card_id', 'raw_data')
    ):
        if cp['card_id'] not in seen_raw:
            seen_raw[cp['card_id']] = cp['raw_data']
 
    return render(request, 'dashboard/bulk_issues.html', {
        'mode':                'drop',
        'cards':               [],
        'drop_cards':          drop_cards,
        'expansions':          expansions,
        'expansion_code':      expansion_code,
        'selected_expansion':  expansion_code,
        'sort':                sort,
        'total_count':         total_count,
        'avg_drop_pct':        avg_drop_pct,
        'max_drop':            max_drop,
        'all_rarities':        all_rarities,
        'selected_rarities':   selected_rarities,
        'selected_rarities_json': json.dumps(selected_rarities),
        'card_raw_json':       json.dumps(seen_raw, ensure_ascii=False),
        'breadcrumb': [
            ('홈', '/'),
            (cfg['label'], f'{base_url}/expansions/'),
            ('일괄 판매가 설정', f'{base_url}/bulk-price/'),
            ('하락 대기 목록', None),
        ],
        'config': {
            'label':            cfg['label'],
            'bulk_price_url':   f'{base_url}/bulk-price/',
            'bulk_issues_url':  f'{base_url}/bulk-price/issues/',
            'approve_url':      f'{base_url}/bulk-price/approve/',
            'edit_url':         f'{base_url}/bulk-price/edit/',
            'set_price_url_prefix': f'{base_url}/cards/',
            'high_rarity_list': cfg.get('bulk_issues_high_rarity_list', cfg.get('high_rarity_list', '[]')),
            'unpriced_url':     f'{base_url}/bulk-price/issues/?mode=unpriced',
            'drop_url':         f'{base_url}/bulk-price/issues/?mode=drop',
        },
    })

def _bulk_approve_view(request, cfg_key):
    """개별 카드 반영: modified_price → selling_price, modified_price 초기화"""
    cfg = _cfg(cfg_key)
    card_model = cfg['card_model']

    try:
        body    = json.loads(request.body)
        card_id = int(body.get('card_id'))
    except (json.JSONDecodeError, TypeError, ValueError):
        return JsonResponse({'error': 'Invalid request'}, status=400)

    card = get_object_or_404(card_model, pk=card_id)
    if not card.modified_price:
        return JsonResponse({'error': 'modified_price 없음'}, status=400)

    old_price          = int(card.selling_price) if card.selling_price else 0
    card.selling_price = card.modified_price
    card.modified_price = 0
    card.save(update_fields=['selling_price', 'modified_price'])

    return JsonResponse({
        'success':   True,
        'card_id':   card_id,
        'old_price': old_price,
        'new_price': int(card.selling_price),
    })


def _bulk_edit_view(request, cfg_key):
    """개별 카드 가격 직접 편집 후 selling_price 저장, modified_price 초기화"""
    cfg = _cfg(cfg_key)
    card_model = cfg['card_model']

    try:
        body      = json.loads(request.body)
        card_id   = int(body.get('card_id'))
        new_price = int(body.get('price'))
        if new_price <= 0:
            raise ValueError
    except (json.JSONDecodeError, TypeError, ValueError):
        return JsonResponse({'error': 'Invalid request'}, status=400)

    card = get_object_or_404(card_model, pk=card_id)
    old_price           = int(card.selling_price) if card.selling_price else 0
    card.selling_price  = new_price
    card.modified_price = 0
    card.save(update_fields=['selling_price', 'modified_price'])

    return JsonResponse({
        'success':   True,
        'card_id':   card_id,
        'old_price': old_price,
        'new_price': new_price,
    })


# ════════════════════════════════════════════════════════════════
# 포켓몬 한글판 — 뷰
# ════════════════════════════════════════════════════════════════

@staff_required
def pokemon_kr_expansion_list(request):
    return _expansion_list_view(request, 'pokemon_kr', {
        'bulk_price_url':         '/pokemon/kr/bulk-price/',
        'card_search_url':        '/pokemon/kr/cards/search/',
        'bulk_issues_url':        '/pokemon/kr/bulk-price/issues/',
        'reset_prices_url_prefix':'/pokemon/kr/expansions/',
        'reset_all_url':          '/pokemon/kr/reset-all-prices/',
    })


@staff_required
def pokemon_kr_card_list(request, code):
    expansion = get_object_or_404(Expansion, code=code)
    return _card_list_view(request, 'pokemon_kr', code, {
        'bulk_price_url':   f'/pokemon/kr/bulk-price/?expansion={expansion.code}',
        'reset_prices_url': f'/pokemon/kr/expansions/{expansion.code}/reset-prices/',
    })


@staff_required
def pokemon_kr_card_detail(request, pk):
    card = get_object_or_404(Card.objects.select_related('expansion'), pk=pk)
    latest_price_obj = card.prices.order_by('-collected_at').first()
    market_items, stats = _parse_market_items(latest_price_obj)
    base = '/pokemon/kr'

    return render(request, 'dashboard/card_detail.html', {
        'card':                   card,
        'card_type':              'pokemon_kr',
        'latest_price_obj':       latest_price_obj,
        'market_items':           market_items,
        'market_items_json':      json.dumps(market_items, ensure_ascii=False),
        'stats':                  stats,
        'set_price_url':          f'{base}/cards/{pk}/set-price/',
        'back_url':               f'{base}/expansions/{card.expansion.code}/cards/',
        'price_history_week_json':_price_history_json(card, card.prices),
        'breadcrumb': [
            ('홈', '/'),
            ('포켓몬 한글판', f'{base}/expansions/'),
            (card.expansion.name, f'{base}/expansions/{card.expansion.code}/cards/'),
            (card.name, None),
        ],
    })


@staff_required
@require_POST
def pokemon_kr_set_price(request, pk):
    return _set_price(Card, pk, request)


@staff_required
def pokemon_kr_card_search(request):
    return _card_search_view(request, Card)


@staff_required
@require_POST
def pokemon_kr_reset_prices(request, expansion_code):
    count = Card.objects.filter(expansion__code=expansion_code).update(selling_price=0)
    return JsonResponse({'success': True, 'count': count})


@staff_required
@require_POST
def pokemon_kr_reset_all_prices(request):
    count = Card.objects.all().update(selling_price=0)
    return JsonResponse({'success': True, 'count': count})


@staff_required
def pokemon_kr_bulk_price(request):
    return _bulk_price_view(request, 'pokemon_kr')


@staff_required
@require_POST
def pokemon_kr_bulk_run(request):
    return _bulk_run_view(request, 'pokemon_kr')


@staff_required
def pokemon_kr_bulk_issues(request):
    return _bulk_issues_view(request, 'pokemon_kr')


@staff_required
@require_POST
def pokemon_kr_bulk_approve(request):
    return _bulk_approve_view(request, 'pokemon_kr')


@staff_required
@require_POST
def pokemon_kr_bulk_edit(request):
    return _bulk_edit_view(request, 'pokemon_kr')


@staff_required
def pokemon_kr_shop_stats(request):
    raw_list = _load_raw_data(CardPrice)
    shop_stats, overall_avg = _calc_shop_stats(raw_list)
    expansions = Expansion.objects.order_by('-release_date')
    return render(request, 'dashboard/shop_stats.html', {
        'shop_stats_json':  json.dumps(shop_stats, ensure_ascii=False),
        'shop_stats':       shop_stats,
        'overall_avg':      overall_avg,
        'expansion':        None,
        'expansions':       expansions,
        'total_cards':      Card.objects.count(),
        'title':            '포켓몬 한글판 전체',
        'breadcrumb': [
            ('홈', '/'),
            ('포켓몬 한글판', '/pokemon/kr/expansions/'),
            ('경쟁 샵 랭킹', None),
        ],
    })


@staff_required
def pokemon_kr_shop_stats_detail(request, code):
    expansion = get_object_or_404(Expansion, code=code)
    raw_list = _load_raw_data(CardPrice, expansion_code=code)
    shop_stats, overall_avg = _calc_shop_stats(raw_list)
    expansions = Expansion.objects.order_by('-release_date')
    return render(request, 'dashboard/shop_stats.html', {
        'shop_stats_json':  json.dumps(shop_stats, ensure_ascii=False),
        'shop_stats':       shop_stats,
        'overall_avg':      overall_avg,
        'expansion':        expansion,
        'expansions':       expansions,
        'total_cards':      Card.objects.filter(expansion=expansion).count(),
        'title':            expansion.name,
        'breadcrumb': [
            ('홈', '/'),
            ('포켓몬 한글판', '/pokemon/kr/expansions/'),
            ('경쟁 샵 랭킹', '/pokemon/kr/shop-stats/'),
            (expansion.name, None),
        ],
    })


# ════════════════════════════════════════════════════════════════
# 포켓몬 한글판 — 즐겨찾기
# ════════════════════════════════════════════════════════════════

@staff_required
@require_POST
def pokemon_kr_toggle_favorite(request, card_id):
    try:
        card = Card.objects.get(pk=card_id)
    except Card.DoesNotExist:
        return JsonResponse({'error': '카드를 찾을 수 없습니다.'}, status=404)
    card.is_favorite = not card.is_favorite
    card.save(update_fields=['is_favorite'])
    return JsonResponse({'success': True, 'is_favorite': card.is_favorite})


@staff_required
def pokemon_kr_favorites(request):
    cards = (
        Card.objects.filter(is_favorite=True)
        .select_related('expansion')
        .prefetch_related('prices')
        .order_by('expansion__name', 'card_number')
    )
    card_data = []
    for card in cards:
        latest = card.prices.order_by('-collected_at').first()
        card_data.append({
            'card':         card,
            'latest_price': latest.price if latest else None,
            'collected_at': latest.collected_at if latest else None,
        })
    return render(request, 'dashboard/favorites.html', {
        'card_data':          card_data,
        'game':               'pokemon',
        'lang':               'kr',
        'title':              '즐겨찾기 — 포켓몬 한글판',
        'total':              len(card_data),
        'bulk_price_url':     '/pokemon/kr/bulk-price/',
        'reset_favorites_url':'/pokemon/kr/favorites/reset-prices/',
        'breadcrumb': [
            ('홈', '/'),
            ('포켓몬 한글판', '/pokemon/kr/expansions/'),
            ('즐겨찾기', None),
        ],
    })


# ════════════════════════════════════════════════════════════════
# 포켓몬 일본판 — 뷰
# ════════════════════════════════════════════════════════════════

@staff_required
def pokemon_jp_expansion_list(request):
    return _expansion_list_view(request, 'pokemon_jp', {
        'card_search_url': '/pokemon/jp/cards/search/',
    })


@staff_required
def pokemon_jp_card_list(request, code):
    return _card_list_view(request, 'pokemon_jp', code)


@staff_required
def pokemon_jp_card_detail(request, pk):
    card = get_object_or_404(JapanCard.objects.select_related('expansion'), pk=pk)
    base = '/pokemon/jp'

    latest_prices = {}
    for price in JapanCardPrice.objects.filter(card=card).order_by('-collected_at'):
        key = f"{price.source}_{price.condition}"
        if key not in latest_prices:
            latest_prices[key] = price

    price_values = [int(p.price) for p in latest_prices.values()]
    stats = _calc_stats(price_values)

    return render(request, 'dashboard/card_detail_jp.html', {
        'card':          card,
        'latest_prices': latest_prices,
        'stats':         stats,
        'set_price_url': f'{base}/cards/{pk}/set-price/',
        'back_url':      f'{base}/expansions/{card.expansion.code}/cards/',
        'breadcrumb': [
            ('홈', '/'),
            ('포켓몬 일본판', f'{base}/expansions/'),
            (card.expansion.name, f'{base}/expansions/{card.expansion.code}/cards/'),
            (card.name, None),
        ],
    })


@staff_required
@require_POST
def pokemon_jp_set_price(request, pk):
    return _set_price(JapanCard, pk, request)


# ════════════════════════════════════════════════════════════════
# 원피스 한글판 — 뷰
# ════════════════════════════════════════════════════════════════

@staff_required
def onepiece_kr_expansion_list(request):
    return _expansion_list_view(request, 'onepiece_kr', {
        'bulk_price_url':          '/onepiece/kr/bulk-price/',
        'card_search_url':         '/onepiece/kr/cards/search/',
        'bulk_issues_url':         '/onepiece/kr/bulk-price/issues/',
        'reset_prices_url_prefix': '/onepiece/kr/expansions/',
        'reset_all_url':           '/onepiece/kr/reset-all-prices/',
    })


@staff_required
def onepiece_kr_card_list(request, code):
    expansion = get_object_or_404(OnePieceExpansion, code=code)
    return _card_list_view(request, 'onepiece_kr', code, {
        'bulk_price_url':   f'/onepiece/kr/bulk-price/?expansion={expansion.code}',
        'reset_prices_url': f'/onepiece/kr/expansions/{expansion.code}/reset-prices/',
    })


@staff_required
def onepiece_kr_card_detail(request, pk):
    card = get_object_or_404(OnePieceCard.objects.select_related('expansion'), pk=pk)
    latest_price_obj = card.prices.order_by('-collected_at').first()
    market_items, stats = _parse_market_items(latest_price_obj)
    base = '/onepiece/kr'

    return render(request, 'dashboard/card_detail.html', {
        'card':                    card,
        'card_type':               'onepiece_kr',
        'latest_price_obj':        latest_price_obj,
        'market_items':            market_items,
        'market_items_json':       json.dumps(market_items, ensure_ascii=False),
        'stats':                   stats,
        'set_price_url':           f'{base}/cards/{pk}/set-price/',
        'back_url':                f'{base}/expansions/{card.expansion.code}/cards/',
        'price_history_week_json': _price_history_json(card, card.prices),
        'breadcrumb': [
            ('홈', '/'),
            ('원피스 한글판', f'{base}/expansions/'),
            (card.expansion.name, f'{base}/expansions/{card.expansion.code}/cards/'),
            (card.name, None),
        ],
    })


@staff_required
@require_POST
def onepiece_kr_set_price(request, pk):
    return _set_price(OnePieceCard, pk, request)


@staff_required
@require_POST
def onepiece_kr_reset_prices(request, expansion_code):
    count = OnePieceCard.objects.filter(expansion__code=expansion_code).update(selling_price=0)
    return JsonResponse({'success': True, 'count': count})


@staff_required
@require_POST
def onepiece_kr_reset_all_prices(request):
    count = OnePieceCard.objects.all().update(selling_price=0)
    return JsonResponse({'success': True, 'count': count})


@staff_required
def onepiece_kr_bulk_price(request):
    return _bulk_price_view(request, 'onepiece_kr')


@staff_required
@require_POST
def onepiece_kr_bulk_run(request):
    return _bulk_run_view(request, 'onepiece_kr')


@staff_required
def onepiece_kr_bulk_issues(request):
    return _bulk_issues_view(request, 'onepiece_kr')


@staff_required
@require_POST
def onepiece_kr_bulk_approve(request):
    return _bulk_approve_view(request, 'onepiece_kr')


@staff_required
@require_POST
def onepiece_kr_bulk_edit(request):
    return _bulk_edit_view(request, 'onepiece_kr')


@staff_required
def onepiece_kr_card_search(request):
    return _card_search_view(request, OnePieceCard)


# ════════════════════════════════════════════════════════════════
# 원피스 한글판 — 즐겨찾기
# ════════════════════════════════════════════════════════════════

@staff_required
@require_POST
def onepiece_kr_toggle_favorite(request, card_id):
    try:
        card = OnePieceCard.objects.get(pk=card_id)
    except OnePieceCard.DoesNotExist:
        return JsonResponse({'error': '카드를 찾을 수 없습니다.'}, status=404)
    card.is_favorite = not card.is_favorite
    card.save(update_fields=['is_favorite'])
    return JsonResponse({'success': True, 'is_favorite': card.is_favorite})


@staff_required
def onepiece_kr_favorites(request):
    cards = (
        OnePieceCard.objects.filter(is_favorite=True)
        .select_related('expansion')
        .prefetch_related('prices')
        .order_by('expansion__name', 'card_number')
    )
    card_data = []
    for card in cards:
        latest = card.prices.order_by('-collected_at').first()
        card_data.append({
            'card':         card,
            'latest_price': latest.price if latest else None,
            'collected_at': latest.collected_at if latest else None,
        })
    return render(request, 'dashboard/favorites.html', {
        'card_data':           card_data,
        'game':                'onepiece',
        'lang':                'kr',
        'title':               '즐겨찾기 — 원피스 한글판',
        'total':               len(card_data),
        'bulk_price_url':      '/onepiece/kr/bulk-price/',
        'reset_favorites_url': '/onepiece/kr/favorites/reset-prices/',
        'breadcrumb': [
            ('홈', '/'),
            ('원피스 한글판', '/onepiece/kr/expansions/'),
            ('즐겨찾기', None),
        ],
    })


# ════════════════════════════════════════════════════════════════
# 즐겨찾기 판매가 초기화
# ════════════════════════════════════════════════════════════════

@staff_required
@require_POST
def pokemon_kr_reset_favorite_prices(request):
    count = Card.objects.filter(is_favorite=True).update(selling_price=0)
    return JsonResponse({'success': True, 'count': count})


@staff_required
@require_POST
def onepiece_kr_reset_favorite_prices(request):
    count = OnePieceCard.objects.filter(is_favorite=True).update(selling_price=0)
    return JsonResponse({'success': True, 'count': count})