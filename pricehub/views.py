"""
pricehub/views.py

판매가 관리 대시보드.
- 홈: 게임(포켓몬/원피스/디지몬) × 언어(한글판/일본판) 선택
- 각 카테고리별: 확장팩 목록 → 카드 목록 → 카드 상세 + 판매가 설정
"""
import json
import logging
import re
from urllib.parse import urlencode

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.db.models import OuterRef, Subquery, F

logger = logging.getLogger(__name__)

try:
    import openpyxl
except ImportError:
    openpyxl = None

from django.utils import timezone
from datetime import timedelta

from .models import (
    Expansion, Card, CardPrice,
    OnePieceExpansion, OnePieceCard, OnePieceCardPrice,
    JapanExpansion, JapanCard, JapanCardPrice,
    DigimonExpansion, DigimonCard, DigimonCardPrice,
)
from .utils import OUR_SHOPS, safe_json_dumps


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
        'toggle_favorite_url_base': '/onepiece/kr/cards/',
    },
    'digimon_kr': {
        'label': '디지몬 한글판',
        'expansion_model': DigimonExpansion,
        'card_model': DigimonCard,
        'price_model': DigimonCardPrice,
        'base_url': '/digimon/kr',
        'high_rarity_list': "['SEC','SR']",
        'bulk_issues_high_rarity_list': "['SEC','SR']",
        'card_detail_template': 'dashboard/card_detail.html',
        'card_type_key': 'digimon_kr',
        'toggle_favorite_url_base': '/digimon/kr/cards/',
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
    elif request.GET.get('expired'):
        error = '세션이 만료되었거나 다른 곳에서 로그인해 인증이 초기화됐습니다. 다시 로그인해주세요.'
    return render(request, 'dashboard/login.html', {'error': error})


def dashboard_logout(request):
    logout(request)
    return redirect('/login/')


def csrf_failure(request, reason=""):
    """
    CSRF 검증 실패 처리 (settings.CSRF_FAILURE_VIEW).

    로그인 성공 시 Django가 보안을 위해 CSRF 토큰을 회전시키는데(rotate_token),
    세션 만료로 여러 탭/오래 열려있던 로그인 폼이 옛 토큰을 들고 있다가 제출되면
    쿠키와 안 맞아 CSRF 검증에 실패한다. 기본 403 디버그 화면 대신 안내와 함께
    로그인 페이지로 돌려보낸다.
    """
    logger.warning('CSRF 검증 실패 (%s): %s %s', reason, request.method, request.path)
    next_url = request.POST.get('next') or request.GET.get('next') or '/'
    query = urlencode({'next': next_url, 'expired': '1'})
    return redirect(f'/login/?{query}')


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
            'regions': [
                {
                    'label': '한글판',
                    'key': 'kr',
                    'url': _url('digimon_kr', '/expansions/'),
                    'total': DigimonCard.objects.count(),
                    'unpriced': DigimonCard.objects.filter(selling_price=0).count(),
                },
            ],
        },
    ]

    tools = [
        {
            'icon': '📋',
            'title': '엑셀-DB 상품코드 검증',
            'desc': '가격 일괄 수정용 엑셀을 업로드해 DB에 등록된 카드명·이미지와 상품코드 기준으로 비교합니다.',
            'items': [
                {'label': '포켓몬 한글판', 'url': _url('pokemon_kr', '/bulk-price/verify/')},
                {'label': '원피스 한글판', 'url': _url('onepiece_kr', '/bulk-price/verify/')},
                {'label': '디지몬 한글판', 'url': _url('digimon_kr', '/bulk-price/verify/')},
            ],
        },
        {
            'icon': '💰',
            'title': '매입리스트 관리',
            'desc': '게임별 매입리스트를 만들어 카드를 담고, 판매가 대비 매입가 비율(기본 50%)로 추천 매입가를 받아 가격 관리자가 최종 확정합니다.',
            'items': [
                {'label': '매입리스트 바로가기', 'url': '/purchase-lists/'},
            ],
        },
    ]

    return render(request, 'dashboard/home.html', {'categories': categories, 'tools': tools})


# ════════════════════════════════════════════════════════════════
# 공통 헬퍼 — 가격 데이터
# ════════════════════════════════════════════════════════════════

def _load_raw_data(card_model, expansion_code=None, rarities=None):
    """
    카드별 최신 raw_data 반환.

    Card.latest_raw_data 캐시(가격 수집 시마다 자동 갱신됨)를 그대로 읽는다.
    예전엔 price_model(가격 히스토리 전체 테이블)을 GROUP BY MAX(id)로 스캔했는데,
    히스토리가 누적될수록(카드당 수백 건) 매 요청마다 전체 테이블을 훑어야 해서
    데이터가 쌓일수록 점점 느려지는 문제가 있었다.
    """
    qs = card_model.objects.exclude(latest_raw_data__isnull=True).exclude(latest_raw_data=[])
    if expansion_code:
        qs = qs.filter(expansion__code=expansion_code)
    if rarities:
        qs = qs.filter(rarity__in=rarities)

    return list(qs.values_list('latest_raw_data', flat=True))


def _collect_mall_names(card_model, expansion_code=None, limit=500):
    """raw_data에서 mallName 빈도 집계 — Card.latest_raw_data 캐시 사용"""
    qs = card_model.objects.exclude(latest_raw_data__isnull=True).exclude(latest_raw_data=[])
    if expansion_code:
        qs = qs.filter(expansion__code=expansion_code)

    name_count = {}
    for raw in qs.values_list('latest_raw_data', flat=True)[:limit]:
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
    return safe_json_dumps(
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


def _underpriced_count(cfg):
    """판매가가 최근 수집된 시장 최저가보다 낮은 카드 수.

    일본판은 시장가(엔)와 판매가(원) 통화가 달라 비교가 성립하지 않으므로 호출측에서 제외한다.
    """
    card_model = cfg['card_model']
    price_model = cfg['price_model']
    latest_price_qs = price_model.objects.filter(card=OuterRef('pk')).order_by('-collected_at')
    try:
        return (
            card_model.objects
            .annotate(latest_market_price=Subquery(latest_price_qs.values('price')[:1]))
            .filter(
                selling_price__gt=0,
                latest_market_price__isnull=False,
                selling_price__lt=F('latest_market_price'),
            )
            .count()
        )
    except Exception:
        return 0


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

    try:
        drop_count = card_model.objects.filter(
            modified_price__gt=0,
            selling_price__gt=0,
            modified_price__lt=F('selling_price'),
        ).count()
    except Exception:
        drop_count = 0

    # 일본판은 시장가(엔)·판매가(원) 통화가 달라 비교 대상에서 제외
    underpriced_count = _underpriced_count(cfg) if cfg_key != 'pokemon_jp' else 0

    ctx = {
        'expansions': expansions,
        'total_cards': sum(e.card_count for e in expansions),
        'total_unpriced': sum(e.unpriced_count for e in expansions),
        'total_drop': drop_count,
        'total_underpriced': underpriced_count,
        'base_url': base_url,
        'title': cfg['label'],
        'breadcrumb': [('홈', '/'), (cfg['label'], None)],
        'card_detail_base_url': f'{base_url}/cards/',
        'bulk_drop_url':     f'{base_url}/bulk-price/drop/',
        'bulk_unpriced_url': f'{base_url}/bulk-price/unpriced/',
        'bulk_underpriced_url': f'{base_url}/bulk-price/underpriced/' if cfg_key != 'pokemon_jp' else '',
    }
    if extra_ctx:
        ctx.update(extra_ctx)
    return render(request, 'dashboard/expansion_list.html', ctx)


def _digimon_tags(card):
    tags = []
    if card.is_parallel:
        tags.append(('패러렐', 'tag-parallel'))
    if card.is_scarce:
        tags.append(('희소', 'tag-scarce'))
    if card.is_special:
        tags.append(('스페셜', 'tag-special'))
    return tags


def _onepiece_tags(card):
    if card.rarity == 'MANGA':
        return [('망가', 'tag-manga')]
    if card.rarity == 'SP':
        return [('스페셜', 'tag-special')]
    if card.rarity.startswith('P-'):
        return [('패러렐', 'tag-parallel')]
    return []


def _pokemon_kr_tags(card):
    return [('특일', 'tag-teukil')] if card.is_teukil else []


# 카드 종류별 뱃지 태그 계산 함수 (없는 종류는 태그 컬럼 자체를 숨김)
_TAG_FUNCS = {
    'digimon_kr':  _digimon_tags,
    'onepiece_kr': _onepiece_tags,
    'pokemon_kr':  _pokemon_kr_tags,
}


def _card_list_view(request, cfg_key, code, extra_ctx=None):
    cfg = _cfg(cfg_key)
    expansion_model = cfg['expansion_model']
    card_model = cfg['card_model']
    price_model = cfg['price_model']
    base_url = cfg['base_url']

    expansion = get_object_or_404(expansion_model, code=code)
    latest_price_qs = price_model.objects.filter(card=OuterRef('pk')).order_by('-collected_at')
    cards_qs = (
        card_model.objects.filter(expansion=expansion)
        .annotate(
            latest_market_price=Subquery(latest_price_qs.values('price')[:1]),
            latest_collected_at=Subquery(latest_price_qs.values('collected_at')[:1]),
        )
        .order_by('card_number')
    )

    filter_type = request.GET.get('filter', 'all')
    if filter_type == 'unpriced':
        cards_qs = cards_qs.filter(selling_price=0)
    elif filter_type == 'priced':
        cards_qs = cards_qs.filter(selling_price__gt=0)
    elif filter_type == 'favorites':
        cards_qs = cards_qs.filter(is_favorite=True)
    elif filter_type == 'underpriced':
        cards_qs = cards_qs.filter(
            selling_price__gt=0,
            latest_market_price__isnull=False,
            selling_price__lt=F('latest_market_price'),
        )

    # 레어도 필터
    all_rarities = list(
        card_model.objects.filter(expansion=expansion)
        .values_list('rarity', flat=True)
        .distinct()
        .order_by('rarity')
    )
    selected_rarities = request.GET.getlist('rarities')
    if selected_rarities:
        cards_qs = cards_qs.filter(rarity__in=selected_rarities)

    # 정렬
    sort = request.GET.get("sort", "number")
    if sort == "price_asc":
        from django.db.models import Case, When, IntegerField
        cards_qs = cards_qs.annotate(
            _price_sort=Case(
                When(selling_price__isnull=True, then=999999999),
                When(selling_price=0,            then=999999999),
                default='selling_price',
                output_field=IntegerField(),
            )
        ).order_by('_price_sort', 'card_number')
    elif sort == "price_desc":
        from django.db.models import Case, When, IntegerField
        cards_qs = cards_qs.annotate(
            _price_sort=Case(
                When(selling_price__isnull=True, then=-1),
                When(selling_price=0,            then=-1),
                default='selling_price',
                output_field=IntegerField(),
            )
        ).order_by('-_price_sort', 'card_number')
    elif sort == "market_asc":
        from django.db.models import F as _F
        cards_qs = cards_qs.order_by(_F('latest_market_price').asc(nulls_last=True), 'card_number')
    elif sort == "market_desc":
        from django.db.models import F as _F
        cards_qs = cards_qs.order_by(_F('latest_market_price').desc(nulls_last=True), 'card_number')
    else:
        cards_qs = cards_qs.order_by("card_number")

    # 페이지네이션
    per_page    = 100
    total_count = cards_qs.count()
    page        = max(1, int(request.GET.get('page', 1) or 1))
    total_pages = max(1, -(-total_count // per_page))
    page        = min(page, total_pages)
    offset      = (page - 1) * per_page
    cards_list  = list(cards_qs[offset:offset + per_page])

    # 카드 종류별 뱃지 태그 (패러렐/희소/스페셜/특일 등)
    tag_func = _TAG_FUNCS.get(cfg_key)
    show_tag_column = tag_func is not None
    if tag_func:
        for c in cards_list:
            c.tag_badges = tag_func(c)

    _half  = 3
    _start = max(1, page - _half)
    _end   = min(total_pages, page + _half)
    if _end - _start < 6:
        if _start == 1:
            _end = min(total_pages, _start + 6)
        else:
            _start = max(1, _end - 6)
    page_range = list(range(_start, _end + 1))

    # 카드별 최신 raw_data (사이드 패널 판매처 목록용 — raw_data 필드 없는 모델은 스킵)
    card_ids = [c.pk for c in cards_list]
    seen_raw = {}
    if hasattr(price_model, 'raw_data') or any(
        f.name == 'raw_data' for f in price_model._meta.get_fields()
    ):
        for cp in (
            price_model.objects.filter(card_id__in=card_ids)
            .exclude(raw_data={}).exclude(raw_data=[])
            .order_by('-collected_at')
            .values('card_id', 'raw_data')
        ):
            if cp['card_id'] not in seen_raw:
                seen_raw[cp['card_id']] = cp['raw_data']

    fav_ctx = {}
    if 'toggle_favorite_url_base' in cfg:
        fav_ctx = {
            'toggle_favorite_url_base': cfg['toggle_favorite_url_base'],
            'favorite_count': card_model.objects.filter(expansion=expansion, is_favorite=True).count(),
        }

    ctx = {
        'expansion':        expansion,
        'cards':            cards_list,
        'filter_type':      filter_type,
        'all_rarities':     all_rarities,
        'selected_rarities': selected_rarities,
        'selected_rarities_json': safe_json_dumps(selected_rarities),
        'card_raw_json':    safe_json_dumps(seen_raw, ensure_ascii=False),
        'total_count':      total_count,
        'page':             page,
        'total_pages':      total_pages,
        'page_range':       page_range,
        'sort':             sort,
        'show_tag_column':  show_tag_column,
        'show_underpriced_filter': cfg_key != 'pokemon_jp',
        'breadcrumb': [
            ('홈', '/'),
            (cfg['label'], f'{base_url}/expansions/'),
            (expansion.name, None),
        ],
        'detail_base_url': f'{base_url}/cards',
        'back_url':        f'{base_url}/expansions/',
        **fav_ctx,
    }
    if extra_ctx:
        ctx.update(extra_ctx)
    return render(request, 'dashboard/card_list.html', ctx)


def _card_detail_view(request, cfg_key, pk):
    cfg = _cfg(cfg_key)
    card_model = cfg['card_model']
    base_url = cfg['base_url']

    card = get_object_or_404(card_model.objects.select_related('expansion'), pk=pk)
    latest_price_obj = card.prices.order_by('-collected_at').first()
    market_items, stats = _parse_market_items(latest_price_obj)

    return render(request, 'dashboard/card_detail.html', {
        'card':                    card,
        'card_type':               cfg_key,
        'latest_price_obj':        latest_price_obj,
        'market_items':            market_items,
        'market_items_json':       safe_json_dumps(market_items, ensure_ascii=False),
        'stats':                   stats,
        'set_price_url':           f'{base_url}/cards/{pk}/set-price/',
        'back_url':                f'{base_url}/expansions/{card.expansion.code}/cards/',
        'price_history_week_json': _price_history_json(card, card.prices),
        'breadcrumb': [
            ('홈', '/'),
            (cfg['label'], f'{base_url}/expansions/'),
            (card.expansion.name, f'{base_url}/expansions/{card.expansion.code}/cards/'),
            (card.name, None),
        ],
    })


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
# 공통 뷰 로직 — bulk_price / bulk_run / bulk_drop / bulk_unpriced / approve / edit
# ════════════════════════════════════════════════════════════════

def _bulk_shop_stats_api(request, cfg_key):
    """bulk-price/stats/ — shop_stats + mall_names AJAX 엔드포인트"""
    cfg = _cfg(cfg_key)
    card_model  = cfg['card_model']

    expansion_code    = request.GET.get('expansion', '') or None
    selected_rarities = request.GET.getlist('rarities') or None

    mall_names = _collect_mall_names(card_model, expansion_code=expansion_code)
    raw_list   = _load_raw_data(card_model, expansion_code=expansion_code, rarities=selected_rarities)
    shop_stats, overall_avg = _calc_shop_stats(raw_list)

    return JsonResponse({
        'mall_names': mall_names,
        'shop_stats': shop_stats,
        'overall_avg': overall_avg,
    }, safe=False)


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

    expansions = list(cfg['expansion_model'].objects.order_by('-release_date', '-created_at'))
    all_rarities = _get_rarities(card_model, expansion_code or None)

    # shop_stats는 페이지 로드 후 AJAX로 비동기 로딩 (bulk-price/stats/ 엔드포인트)
    mall_names = []
    shop_stats = []
    overall_avg = 0

    drop_pending = card_model.objects.filter(
        modified_price__gt=0,
        selling_price__gt=0,
        modified_price__lt=F('selling_price'),
    ).count()
    rise_pending = card_model.objects.filter(
        selling_price__gt=0,
        modified_price__gt=F('selling_price'),
    ).count()
    new_pending = card_model.objects.filter(modified_price__gt=0, selling_price=0).count()
    needs_review = drop_pending + rise_pending + new_pending
    underpriced_pending = _underpriced_count(cfg)

    return render(request, 'dashboard/bulk_price.html', {
        'mall_names': safe_json_dumps(mall_names),
        'mall_names_display': mall_names,
        'expansions': expansions,
        'needs_review': needs_review,
        'underpriced_pending': underpriced_pending,
        'shop_stats_json': safe_json_dumps(shop_stats, ensure_ascii=False),
        'shop_stats': shop_stats,
        'overall_avg': overall_avg,
        'selected_expansion': selected_expansion,
        'expansion_code': expansion_code,
        'all_rarities': all_rarities,
        'selected_rarities': selected_rarities,
        'selected_rarities_json': safe_json_dumps(selected_rarities),
        'breadcrumb': [
            ('홈', '/'),
            (cfg['label'], f'{base_url}/expansions/'),
            ('일괄 판매가 설정', None),
        ],
        'config': {
            'label':                cfg['label'],
            'expansion_list_url':   f'{base_url}/expansions/',
            'bulk_price_url':       f'{base_url}/bulk-price/',
            'bulk_shop_stats_url':  f'{base_url}/bulk-price/stats/',
            'bulk_run_url':         f'{base_url}/bulk-price/run/',
            'drop_url':             f'{base_url}/bulk-price/drop/',
            'rise_url':             f'{base_url}/bulk-price/rise/',
            'unpriced_url':         f'{base_url}/bulk-price/unpriced/',
            'underpriced_url':      f'{base_url}/bulk-price/underpriced/',
            'inline_cards_url':     f'{base_url}/bulk-price/inline-cards/',
            'approve_url':          f'{base_url}/bulk-price/approve/',
            'edit_url':             f'{base_url}/bulk-price/edit/',
            'set_price_url_prefix': f'{base_url}/cards/',
            'high_rarity_list':     cfg.get('high_rarity_list', '[]'),
        },
    })


def _bulk_run_view(request, cfg_key):
    """
    1. 가격 추출 성공 → modified_price 항상 저장
    2. 신규(selling_price=0)  → selling_price도 바로 저장
    3. 유지(동일가)            → selling_price 바로 업데이트 (변화 없음)
    4. 상승                   → modified_price만 저장, selling_price 유지 (상승 대기 — 레어도 오매칭 등 확인 필요)
    5. 하락                   → modified_price만 저장, selling_price 유지 (하락 대기)
    6. 매칭 없음              → 변경 없음 (needs_review)
    ※ overwrite=True 인 경우 상승/하락 관계없이 즉시 덮어씀 (관리자가 명시적으로 동의한 경우)
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
    fallback_mode   = data.get('fallback_mode', '')
    overwrite       = data.get('overwrite', False)

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

    to_update  = []
    skipped    = []
    drop_wait  = []
    rise_wait  = []
    no_match   = []

    result_detail = {'new': 0, 'same_or_up': 0, 'rise': 0, 'drop': 0}

    for card in cards_list:
        if skip_priced and card.selling_price != 0:
            skipped.append(card.id)
            continue

        raw = price_map.get(card.latest_price_id, [])
        if isinstance(raw, dict):
            raw = [raw]

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

        if matched_price is None:
            no_match.append(card.id)
            continue

        if min_price_floor > 0 and matched_price < min_price_floor:
            matched_price = min_price_floor

        old_selling = int(card.selling_price) if card.selling_price else 0
        card.modified_price = matched_price

        if old_selling == 0:
            card.selling_price = matched_price
            result_detail['new'] += 1
        elif overwrite:
            card.selling_price = matched_price
            result_detail['same_or_up'] += 1
        elif matched_price > old_selling:
            # 레어도 오매칭 등으로 잘못 상승하는 경우가 있어 바로 반영하지 않고 관리자 확인을 거친다.
            rise_wait.append(card.id)
            result_detail['rise'] += 1
        elif matched_price < old_selling:
            drop_wait.append(card.id)
            result_detail['drop'] += 1
        else:
            card.selling_price = matched_price
            result_detail['same_or_up'] += 1

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
        'rise_count': result_detail['rise'],
        'rise_ids': rise_wait[:100],
        'detail': result_detail,
        'message': (
            f"완료: 반영 {applied_count}개 "
            f"(신규 {result_detail['new']} / 유지 {result_detail['same_or_up']}) | "
            f"상승 대기 {result_detail['rise']}개 | 하락 대기 {result_detail['drop']}개 | "
            f"매칭 없음 {len(no_match)}개 | 스킵 {len(skipped)}개"
        ),
    })


def _common_issues_config(cfg):
    """bulk_drop / bulk_unpriced 뷰에서 공통으로 쓰는 config dict 생성"""
    base_url = cfg['base_url']
    return {
        'label':                cfg['label'],
        'bulk_price_url':       f'{base_url}/bulk-price/',
        'approve_url':          f'{base_url}/bulk-price/approve/',
        'edit_url':             f'{base_url}/bulk-price/edit/',
        'set_price_url_prefix': f'{base_url}/cards/',
        'high_rarity_list':     cfg.get('bulk_issues_high_rarity_list', cfg.get('high_rarity_list', '[]')),
        'drop_url':             f'{base_url}/bulk-price/drop/',
        'rise_url':             f'{base_url}/bulk-price/rise/',
        'unpriced_url':         f'{base_url}/bulk-price/unpriced/',
        'underpriced_url':      f'{base_url}/bulk-price/underpriced/',
        'inline_cards_url':     f'{base_url}/bulk-price/inline-cards/',
    }


def _bulk_drop_view(request, cfg_key):
    """가격 하락 대기 목록 — modified_price < selling_price 인 카드"""
    cfg = _cfg(cfg_key)
    card_model  = cfg['card_model']
    price_model = cfg['price_model']
    base_url    = cfg['base_url']

    expansion_code    = request.GET.get('expansion', '')
    selected_rarities = request.GET.getlist('rarities')
    sort              = request.GET.get('sort', 'drop_pct')
    page              = max(1, int(request.GET.get('page', 1) or 1))
    per_page          = 100

    all_rarities = _get_rarities(card_model, expansion_code or None)
    expansions   = cfg['expansion_model'].objects.order_by('-release_date')

    qs = card_model.objects.filter(
        modified_price__gt=0,
        selling_price__gt=0,
    ).select_related('expansion')

    if expansion_code:
        qs = qs.filter(expansion__code=expansion_code)
    if selected_rarities:
        qs = qs.filter(rarity__in=selected_rarities)

    all_drop_cards = []
    for card in qs:
        mod  = int(card.modified_price)
        sell = int(card.selling_price)
        if mod < sell:
            drop_amt = sell - mod
            drop_pct = round((drop_amt / sell) * 100, 1)
            all_drop_cards.append({
                'card':           card,
                'modified_price': mod,
                'selling_price':  sell,
                'drop_amt':       drop_amt,
                'drop_pct':       drop_pct,
            })

    if sort == 'drop_pct':
        all_drop_cards.sort(key=lambda x: -x['drop_pct'])
    elif sort == 'drop_amt':
        all_drop_cards.sort(key=lambda x: -x['drop_amt'])
    else:
        all_drop_cards.sort(key=lambda x: getattr(x['card'], 'name_kr', None) or x['card'].name or '')

    total_count  = len(all_drop_cards)
    avg_drop_pct = round(sum(d['drop_pct'] for d in all_drop_cards) / total_count, 1) if total_count else 0
    max_drop     = max((d['drop_pct'] for d in all_drop_cards), default=0)

    # ── 페이지네이션 ──
    total_pages  = max(1, -(-total_count // per_page))   # ceiling division
    page         = min(page, total_pages)
    offset       = (page - 1) * per_page
    drop_cards   = all_drop_cards[offset:offset + per_page]

    # 페이지 번호 목록 (최대 7개, 현재 페이지 중심)
    _half = 3
    _start = max(1, page - _half)
    _end   = min(total_pages, page + _half)
    if _end - _start < 6:
        if _start == 1:
            _end = min(total_pages, _start + 6)
        else:
            _start = max(1, _end - 6)
    page_range = list(range(_start, _end + 1))

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

    return render(request, 'dashboard/bulk_drop.html', {
        'active_tab':             'drop',
        'drop_cards':             drop_cards,
        'expansions':             expansions,
        'expansion_code':         expansion_code,
        'sort':                   sort,
        'total_count':            total_count,
        'avg_drop_pct':           avg_drop_pct,
        'max_drop':               max_drop,
        'all_rarities':           all_rarities,
        'selected_rarities':      selected_rarities,
        'selected_rarities_json': safe_json_dumps(selected_rarities),
        'card_raw_json':          safe_json_dumps(seen_raw, ensure_ascii=False),
        'page':                   page,
        'total_pages':            total_pages,
        'per_page':               per_page,
        'page_range':             page_range,
        'breadcrumb': [
            ('홈', '/'),
            (cfg['label'], f'{base_url}/expansions/'),
            ('일괄 판매가 설정', f'{base_url}/bulk-price/'),
            ('하락 대기 목록', None),
        ],
        'config': _common_issues_config(cfg),
    })


def _bulk_rise_view(request, cfg_key):
    """가격 상승 대기 목록 — modified_price > selling_price 인 카드 (레어도 오매칭 등 확인 후 반영)"""
    cfg = _cfg(cfg_key)
    card_model  = cfg['card_model']
    price_model = cfg['price_model']
    base_url    = cfg['base_url']

    expansion_code    = request.GET.get('expansion', '')
    selected_rarities = request.GET.getlist('rarities')
    sort              = request.GET.get('sort', 'rise_pct')
    page              = max(1, int(request.GET.get('page', 1) or 1))
    per_page          = 100

    all_rarities = _get_rarities(card_model, expansion_code or None)
    expansions   = cfg['expansion_model'].objects.order_by('-release_date')

    qs = card_model.objects.filter(
        modified_price__gt=0,
        selling_price__gt=0,
    ).select_related('expansion')

    if expansion_code:
        qs = qs.filter(expansion__code=expansion_code)
    if selected_rarities:
        qs = qs.filter(rarity__in=selected_rarities)

    all_rise_cards = []
    for card in qs:
        mod  = int(card.modified_price)
        sell = int(card.selling_price)
        if mod > sell:
            rise_amt = mod - sell
            rise_pct = round((rise_amt / sell) * 100, 1)
            all_rise_cards.append({
                'card':           card,
                'modified_price': mod,
                'selling_price':  sell,
                'rise_amt':       rise_amt,
                'rise_pct':       rise_pct,
            })

    if sort == 'rise_pct':
        all_rise_cards.sort(key=lambda x: -x['rise_pct'])
    elif sort == 'rise_amt':
        all_rise_cards.sort(key=lambda x: -x['rise_amt'])
    else:
        all_rise_cards.sort(key=lambda x: getattr(x['card'], 'name_kr', None) or x['card'].name or '')

    total_count  = len(all_rise_cards)
    avg_rise_pct = round(sum(d['rise_pct'] for d in all_rise_cards) / total_count, 1) if total_count else 0
    max_rise     = max((d['rise_pct'] for d in all_rise_cards), default=0)

    # ── 페이지네이션 ──
    total_pages  = max(1, -(-total_count // per_page))   # ceiling division
    page         = min(page, total_pages)
    offset       = (page - 1) * per_page
    rise_cards   = all_rise_cards[offset:offset + per_page]

    # 페이지 번호 목록 (최대 7개, 현재 페이지 중심)
    _half = 3
    _start = max(1, page - _half)
    _end   = min(total_pages, page + _half)
    if _end - _start < 6:
        if _start == 1:
            _end = min(total_pages, _start + 6)
        else:
            _start = max(1, _end - 6)
    page_range = list(range(_start, _end + 1))

    rise_card_ids = [d['card'].pk for d in rise_cards]
    seen_raw = {}
    for cp in (
        price_model.objects.filter(card_id__in=rise_card_ids)
        .exclude(raw_data={}).exclude(raw_data=[])
        .order_by('-collected_at')
        .values('card_id', 'raw_data')
    ):
        if cp['card_id'] not in seen_raw:
            seen_raw[cp['card_id']] = cp['raw_data']

    return render(request, 'dashboard/bulk_rise.html', {
        'active_tab':             'rise',
        'rise_cards':             rise_cards,
        'expansions':             expansions,
        'expansion_code':         expansion_code,
        'sort':                   sort,
        'total_count':            total_count,
        'avg_rise_pct':           avg_rise_pct,
        'max_rise':               max_rise,
        'all_rarities':           all_rarities,
        'selected_rarities':      selected_rarities,
        'selected_rarities_json': safe_json_dumps(selected_rarities),
        'card_raw_json':          safe_json_dumps(seen_raw, ensure_ascii=False),
        'page':                   page,
        'total_pages':            total_pages,
        'per_page':               per_page,
        'page_range':             page_range,
        'breadcrumb': [
            ('홈', '/'),
            (cfg['label'], f'{base_url}/expansions/'),
            ('일괄 판매가 설정', f'{base_url}/bulk-price/'),
            ('상승 대기 목록', None),
        ],
        'config': _common_issues_config(cfg),
    })


def _underpriced_view(request, cfg_key):
    """저가 경고 목록 — 판매가가 최근 수집된 시장 최저가보다 낮은 카드 (매일 collect_price 결과 기준)"""
    cfg = _cfg(cfg_key)
    card_model  = cfg['card_model']
    price_model = cfg['price_model']
    base_url    = cfg['base_url']

    expansion_code    = request.GET.get('expansion', '')
    selected_rarities = request.GET.getlist('rarities')
    sort              = request.GET.get('sort', 'under_pct')
    page              = max(1, int(request.GET.get('page', 1) or 1))
    per_page          = 100

    all_rarities = _get_rarities(card_model, expansion_code or None)
    expansions   = cfg['expansion_model'].objects.order_by('-release_date')

    latest_price_qs = price_model.objects.filter(card=OuterRef('pk')).order_by('-collected_at')
    qs = (
        card_model.objects
        .select_related('expansion')
        .annotate(
            latest_market_price=Subquery(latest_price_qs.values('price')[:1]),
            latest_collected_at=Subquery(latest_price_qs.values('collected_at')[:1]),
        )
        .filter(
            selling_price__gt=0,
            latest_market_price__isnull=False,
            selling_price__lt=F('latest_market_price'),
        )
    )

    if expansion_code:
        qs = qs.filter(expansion__code=expansion_code)
    if selected_rarities:
        qs = qs.filter(rarity__in=selected_rarities)

    all_under_cards = []
    for card in qs:
        sell   = int(card.selling_price)
        market = int(card.latest_market_price)
        under_amt = market - sell
        under_pct = round((under_amt / market) * 100, 1)
        all_under_cards.append({
            'card':          card,
            'selling_price': sell,
            'market_price':  market,
            'collected_at':  card.latest_collected_at,
            'under_amt':     under_amt,
            'under_pct':     under_pct,
        })

    if sort == 'under_amt':
        all_under_cards.sort(key=lambda x: -x['under_amt'])
    elif sort == 'name':
        all_under_cards.sort(key=lambda x: x['card'].name or '')
    else:
        sort = 'under_pct'
        all_under_cards.sort(key=lambda x: -x['under_pct'])

    total_count   = len(all_under_cards)
    avg_under_pct = round(sum(d['under_pct'] for d in all_under_cards) / total_count, 1) if total_count else 0
    max_under     = max((d['under_pct'] for d in all_under_cards), default=0)

    # ── 페이지네이션 ──
    total_pages     = max(1, -(-total_count // per_page))   # ceiling division
    page            = min(page, total_pages)
    offset          = (page - 1) * per_page
    under_cards     = all_under_cards[offset:offset + per_page]

    # 페이지 번호 목록 (최대 7개, 현재 페이지 중심)
    _half = 3
    _start = max(1, page - _half)
    _end   = min(total_pages, page + _half)
    if _end - _start < 6:
        if _start == 1:
            _end = min(total_pages, _start + 6)
        else:
            _start = max(1, _end - 6)
    page_range = list(range(_start, _end + 1))

    under_card_ids = [d['card'].pk for d in under_cards]
    seen_raw = {}
    for cp in (
        price_model.objects.filter(card_id__in=under_card_ids)
        .exclude(raw_data={}).exclude(raw_data=[])
        .order_by('-collected_at')
        .values('card_id', 'raw_data')
    ):
        if cp['card_id'] not in seen_raw:
            seen_raw[cp['card_id']] = cp['raw_data']

    return render(request, 'dashboard/bulk_underpriced.html', {
        'active_tab':             'underpriced',
        'under_cards':            under_cards,
        'card_raw_json':          safe_json_dumps(seen_raw, ensure_ascii=False),
        'expansions':             expansions,
        'expansion_code':         expansion_code,
        'sort':                   sort,
        'total_count':            total_count,
        'avg_under_pct':          avg_under_pct,
        'max_under':              max_under,
        'all_rarities':           all_rarities,
        'selected_rarities':      selected_rarities,
        'selected_rarities_json': safe_json_dumps(selected_rarities),
        'page':                   page,
        'total_pages':            total_pages,
        'per_page':               per_page,
        'page_range':             page_range,
        'breadcrumb': [
            ('홈', '/'),
            (cfg['label'], f'{base_url}/expansions/'),
            ('일괄 판매가 설정', f'{base_url}/bulk-price/'),
            ('저가 경고 목록', None),
        ],
        'config': _common_issues_config(cfg),
    })


def _bulk_unpriced_view(request, cfg_key):
    """판매가 미설정 목록 — selling_price=0 인 카드"""
    cfg = _cfg(cfg_key)
    card_model  = cfg['card_model']
    price_model = cfg['price_model']
    base_url    = cfg['base_url']

    expansion_code    = request.GET.get('expansion', '')
    selected_rarities = request.GET.getlist('rarities')
    sort              = request.GET.get('sort', 'name')
    page              = max(1, int(request.GET.get('page', 1) or 1))
    per_page          = 100

    all_rarities = _get_rarities(card_model, expansion_code or None)
    expansions   = cfg['expansion_model'].objects.order_by('-release_date')

    qs = card_model.objects.filter(selling_price=0).select_related('expansion')
    if expansion_code:
        qs = qs.filter(expansion__code=expansion_code)
    if selected_rarities:
        qs = qs.filter(rarity__in=selected_rarities)
    qs = qs.order_by('expansion__code', 'card_number')

    total_count = qs.count()

    # ── 페이지네이션 ──
    total_pages = max(1, -(-total_count // per_page))   # ceiling division
    page        = min(page, total_pages)
    offset      = (page - 1) * per_page
    cards_page  = qs[offset:offset + per_page]

    # 페이지 번호 목록 (최대 7개, 현재 페이지 중심)
    _half = 3
    _start = max(1, page - _half)
    _end   = min(total_pages, page + _half)
    if _end - _start < 6:
        if _start == 1:
            _end = min(total_pages, _start + 6)
        else:
            _start = max(1, _end - 6)
    page_range = list(range(_start, _end + 1))

    card_ids = [c.pk for c in cards_page]
    seen_raw = {}
    for cp in (
        price_model.objects.filter(card_id__in=card_ids)
        .exclude(raw_data={}).exclude(raw_data=[])
        .order_by('-collected_at')
        .values('card_id', 'raw_data')
    ):
        if cp['card_id'] not in seen_raw:
            seen_raw[cp['card_id']] = cp['raw_data']

    return render(request, 'dashboard/bulk_unpriced.html', {
        'active_tab':             'unpriced',
        'cards':                  cards_page,
        'expansions':             expansions,
        'expansion_code':         expansion_code,
        'sort':                   sort,
        'total_count':            total_count,
        'all_rarities':           all_rarities,
        'selected_rarities':      selected_rarities,
        'selected_rarities_json': safe_json_dumps(selected_rarities),
        'card_raw_json':          safe_json_dumps(seen_raw, ensure_ascii=False),
        'page':                   page,
        'total_pages':            total_pages,
        'per_page':               per_page,
        'page_range':             page_range,
        'breadcrumb': [
            ('홈', '/'),
            (cfg['label'], f'{base_url}/expansions/'),
            ('일괄 판매가 설정', f'{base_url}/bulk-price/'),
            ('판매가 미설정 목록', None),
        ],
        'config': _common_issues_config(cfg),
    })


def _bulk_inline_cards_view(request, cfg_key):
    """
    인라인 결과 패널용 — card_id 목록을 받아 카드 기본 정보 + raw_data 반환.
    POST body: { "card_ids": [1, 2, ...], "mode": "unpriced" | "drop" }
    """
    cfg         = _cfg(cfg_key)
    card_model  = cfg['card_model']
    price_model = cfg['price_model']

    try:
        body     = json.loads(request.body)
        card_ids = [int(i) for i in body.get('card_ids', [])][:200]  # 최대 200개
        mode     = body.get('mode', 'unpriced')
    except (json.JSONDecodeError, TypeError, ValueError):
        return JsonResponse({'error': 'Invalid request'}, status=400)

    if not card_ids:
        return JsonResponse({'cards': [], 'raw': {}})

    cards = list(
        card_model.objects.filter(pk__in=card_ids)
        .select_related('expansion')
        .values(
            'id', 'name', 'rarity', 'card_number', 'image_url',
            'selling_price', 'modified_price',
            'expansion__code', 'expansion__name',
        )
    )

    # raw_data 수집 (카드 ID별 최신 1건)
    seen_raw = {}
    for cp in (
        price_model.objects.filter(card_id__in=card_ids)
        .exclude(raw_data={}).exclude(raw_data=[])
        .order_by('-collected_at')
        .values('card_id', 'raw_data')
    ):
        if cp['card_id'] not in seen_raw:
            seen_raw[cp['card_id']] = cp['raw_data']

    # 하락 모드면 drop_pct 계산 추가
    result_cards = []
    for c in cards:
        item = {
            'id':             c['id'],
            'name':           c['name'],
            'rarity':         c['rarity'],
            'card_number':    c['card_number'],
            'image_url':      c['image_url'] or '',
            'selling_price':  int(c['selling_price'] or 0),
            'modified_price': int(c['modified_price'] or 0),
            'expansion_code': c['expansion__code'],
            'expansion_name': c['expansion__name'],
        }
        if mode == 'drop' and item['selling_price'] > 0:
            drop_amt = item['selling_price'] - item['modified_price']
            item['drop_pct'] = round((drop_amt / item['selling_price']) * 100, 1)
        result_cards.append(item)

    return JsonResponse({
        'cards': result_cards,
        'raw':   {str(k): v for k, v in seen_raw.items()},
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

    old_price           = int(card.selling_price) if card.selling_price else 0
    card.selling_price  = card.modified_price
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
# 공통 뷰 로직 — 엑셀 ↔ DB 상품코드 검증
# ════════════════════════════════════════════════════════════════

# 고정 엑셀 레이아웃: 1~5행은 제목/안내 행, 6행부터 실데이터
# B열 = 상품코드, D열 = 상품명, Z열 = 이미지URL (0-based 인덱스)
VERIFY_DATA_START_ROW = 6   # 1-based, 이 행부터 데이터
VERIFY_CODE_COL  = 1   # B열
VERIFY_NAME_COL  = 3   # D열
VERIFY_IMAGE_COL = 25  # Z열

# 상품코드 끝의 '-V숫자'(미러/패러렐 버전) 패턴
_VERIFY_VERSION_SUFFIX_RE = re.compile(r'-V\d+$', re.IGNORECASE)


def _verify_base_code(code):
    """'DGM-RB1-034-K-V1' → 'DGM-RB1-034-K' (끝의 -V숫자만 제거)"""
    return _VERIFY_VERSION_SUFFIX_RE.sub('', code or '')


def _verify_read_excel(uploaded_file):
    """
    업로드된 엑셀에서 고정 레이아웃 기준으로 데이터 행을 읽어옴.
    1~5행은 건너뛰고 6행부터 데이터로 처리. (header_row 없음, data_rows만 반환)
    """
    wb = openpyxl.load_workbook(uploaded_file, data_only=True, read_only=False)
    ws = wb.worksheets[0]

    data_rows = []
    for row in ws.iter_rows(min_row=VERIFY_DATA_START_ROW, values_only=True):
        if row is None or all(c is None or str(c).strip() == '' for c in row):
            continue
        data_rows.append(row)

    wb.close()
    return data_rows


def _bulk_verify_view(request, cfg_key):
    """
    엑셀 업로드 → 상품코드(B열, 6행부터) 기준으로 DB 카드와 1:1 비교.
    상품명은 D열, 이미지URL은 Z열로 고정.
    GET: 업로드 폼 표시
    POST: 엑셀 파싱 + 비교 결과 표시
    """
    cfg = _cfg(cfg_key)
    card_model = cfg['card_model']
    base_url = cfg['base_url']

    ctx = {
        'config': {
            'label':           cfg['label'],
            'bulk_price_url':  f'{base_url}/bulk-price/',
            'verify_url':      f'{base_url}/bulk-price/verify/',
            'candidates_url':  f'{base_url}/bulk-price/verify/candidates/',
        },
        'breadcrumb': [
            ('홈', '/'),
            (cfg['label'], f"{base_url}/expansions/"),
            ('엑셀-DB 상품코드 검증', None),
        ],
        'uploaded': False,
    }

    if request.method != 'POST':
        return render(request, 'dashboard/bulk_verify.html', ctx)

    if openpyxl is None:
        ctx['error'] = '서버에 openpyxl이 설치되어 있지 않습니다. 관리자에게 문의하세요.'
        return render(request, 'dashboard/bulk_verify.html', ctx)

    excel_file = request.FILES.get('excel_file')
    if not excel_file:
        ctx['error'] = '엑셀 파일을 선택해주세요.'
        return render(request, 'dashboard/bulk_verify.html', ctx)

    try:
        data_rows = _verify_read_excel(excel_file)
    except Exception as e:
        ctx['error'] = f'엑셀 파일을 읽는 중 오류가 발생했습니다: {e}'
        return render(request, 'dashboard/bulk_verify.html', ctx)

    if not data_rows:
        ctx['error'] = f'{VERIFY_DATA_START_ROW}행부터 데이터를 찾을 수 없습니다. 엑셀 양식을 확인해주세요.'
        return render(request, 'dashboard/bulk_verify.html', ctx)

    def _cell(row, idx):
        if idx >= len(row):
            return ''
        val = row[idx]
        return '' if val is None else str(val).strip()

    excel_rows = []
    excel_codes = []
    for row in data_rows:
        code = _cell(row, VERIFY_CODE_COL)
        if not code:
            continue
        excel_rows.append({
            'code':  code,
            'name':  _cell(row, VERIFY_NAME_COL),
            'image': _cell(row, VERIFY_IMAGE_COL),
        })
        excel_codes.append(code)

    if not excel_rows:
        ctx['error'] = '엑셀에서 유효한 상품코드(B열)를 찾지 못했습니다.'
        return render(request, 'dashboard/bulk_verify.html', ctx)

    # DB에서 해당 상품코드들을 일괄 조회 (대소문자 구분 없이 매칭)
    db_cards = (
        card_model.objects
        .filter(shop_product_code__in=excel_codes)
        .select_related('expansion')
    )
    db_map_exact = {c.shop_product_code: c for c in db_cards}
    # 대소문자 차이로 못 찾은 코드 보강 조회
    missing_codes = [c for c in excel_codes if c not in db_map_exact]
    if missing_codes:
        extra = (
            card_model.objects
            .filter(shop_product_code__iregex=r'^(' + '|'.join(re.escape(c) for c in missing_codes) + r')$')
            .select_related('expansion')
        )
        for c in extra:
            db_map_exact.setdefault(c.shop_product_code, c)

    db_map_lower = {code.lower(): card for code, card in db_map_exact.items()}

    results = []
    auto_match_count = 0    # 이미지 URL이 완전히 동일 → 자동 확인 완료
    needs_check_count = 0   # 등록은 되어 있으나 이미지 URL이 달라 육안 확인 필요
    notfound_count = 0      # DB에 상품코드 자체가 없음

    for row in excel_rows:
        code = row['code']
        card = db_map_exact.get(code) or db_map_lower.get(code.lower())

        if not card:
            notfound_count += 1
            results.append({
                'code':         code,
                'base_code':    _verify_base_code(code),
                'excel_name':   row['name'],
                'excel_image':  row['image'],
                'db_name':      None,
                'db_image':     None,
                'db_expansion': None,
                'status':       'notfound',
            })
            continue

        # 이미지 URL이 글자 그대로 동일하면 같은 이미지로 간주해 자동 통과.
        # 그 외(이미지가 다르거나 비어있는 경우)는 작업자가 직접 눈으로 비교해야 함.
        image_url_same = bool(row['image']) and bool(card.image_url) and row['image'] == card.image_url
        status = 'auto_match' if image_url_same else 'needs_check'

        if status == 'auto_match':
            auto_match_count += 1
        else:
            needs_check_count += 1

        results.append({
            'code':         code,
            'base_code':    _verify_base_code(code),
            'excel_name':   row['name'],
            'excel_image':  row['image'],
            'db_name':      card.name,
            'db_image':     card.image_url,
            'db_expansion': card.expansion.name if card.expansion_id else '',
            'status':       status,
            'card_id':      card.pk,
        })

    # 보기 좋게: 확인이 필요한 항목 우선 정렬 (DB 미등록 → 육안확인 필요 → 자동일치)
    status_order = {'notfound': 0, 'needs_check': 1, 'auto_match': 2}
    results.sort(key=lambda r: status_order.get(r['status'], 9))

    only_problems = request.GET.get('only_problems') == '1' or request.POST.get('only_problems') == '1'
    display_results = [r for r in results if r['status'] != 'auto_match'] if only_problems else results

    ctx.update({
        'uploaded':              True,
        'results':               display_results,
        'total_count':           len(results),
        'auto_match_count':      auto_match_count,
        'needs_check_count':     needs_check_count,
        'notfound_count':        notfound_count,
        'only_problems':         only_problems,
        'file_name':             getattr(excel_file, 'name', ''),
    })
    return render(request, 'dashboard/bulk_verify.html', ctx)


def _bulk_verify_candidates_view(request, cfg_key):
    """
    같은 베이스 상품코드(끝의 -V숫자 제거)를 가진 DB 카드 후보 전체를 반환.
    예: base_code='DGM-RB1-034-K' → DGM-RB1-034-K, -V1, -V2, -V3 ... 전부 조회.
    엑셀-DB 검증 페이지에서 "확인 필요" 카드를 클릭했을 때 AJAX로 호출.
    """
    cfg = _cfg(cfg_key)
    card_model = cfg['card_model']

    base_code = request.GET.get('base_code', '').strip()
    if not base_code:
        return JsonResponse({'error': 'base_code가 필요합니다.'}, status=400)

    # base_code 자체이거나, base_code 뒤에 -V숫자가 붙은 코드들을 전부 조회
    pattern = r'^' + re.escape(base_code) + r'(-V\d+)?$'
    candidates = (
        card_model.objects
        .filter(shop_product_code__iregex=pattern)
        .select_related('expansion')
        .order_by('shop_product_code')
    )

    return JsonResponse({
        'base_code': base_code,
        'candidates': [
            {
                'card_id':           c.pk,
                'shop_product_code': c.shop_product_code,
                'name':              c.name,
                'image_url':         c.image_url,
                'expansion':         c.expansion.name if c.expansion_id else '',
                'rarity':            c.rarity,
            }
            for c in candidates
        ],
    })


# ════════════════════════════════════════════════════════════════
# 게임별 얇은 위임 뷰 생성 — bulk_* 12종 + card_detail
#
# 게임 카테고리(포켓몬/원피스/디지몬 한글판) 간 차이가 cfg_key 하나뿐인
# 뷰들만 대상으로 한다. expansion_list/card_list는 게임별 extra_ctx가
# 실제로 다르고, set_price/card_search는 시그니처가 다르고,
# reset_prices/toggle_favorite/shop_stats는 자체 로직을 가지고 있어서
# 이 팩토리로 일반화하면 오히려 read 하기 어려워진다 — 대상에서 제외.
# ════════════════════════════════════════════════════════════════

def _make_game_view(base_view, cfg_key, require_post=False):
    """base_view(request, cfg_key, *args, **kwargs)를 호출하는 얇은 위임 뷰 생성.

    기존 코드의 `@staff_required` `@require_POST` 데코레이터 순서(staff_required가
    바깥쪽)를 그대로 유지한다 — require_POST를 먼저 적용해 감싸고, 그 결과를
    staff_required로 한 번 더 감싼다.
    """
    def _view(request, *args, **kwargs):
        return base_view(request, cfg_key, *args, **kwargs)
    _view.__name__ = f"{cfg_key}__{base_view.__name__.lstrip('_')}"
    if require_post:
        _view = require_POST(_view)
    _view = staff_required(_view)
    return _view


_GAME_VIEW_TYPES = [
    # (urls.py views dict의 key, 위임할 공용 뷰, POST 전용 여부)
    ('bulk_price',             _bulk_price_view,             False),
    ('bulk_verify',            _bulk_verify_view,            False),
    ('bulk_verify_candidates', _bulk_verify_candidates_view, False),
    ('bulk_shop_stats',        _bulk_shop_stats_api,         False),
    ('bulk_run',               _bulk_run_view,                True),
    ('bulk_drop',              _bulk_drop_view,              False),
    ('bulk_rise',              _bulk_rise_view,              False),
    ('bulk_unpriced',          _bulk_unpriced_view,          False),
    ('bulk_underpriced',       _underpriced_view,            False),
    ('bulk_approve',           _bulk_approve_view,            True),
    ('bulk_inline_cards',      _bulk_inline_cards_view,       True),
    ('bulk_edit',              _bulk_edit_view,               True),
    ('card_detail',            _card_detail_view,            False),
]


def game_views(cfg_key):
    """cfg_key(pokemon_kr/onepiece_kr/digimon_kr)의 bulk_*/card_detail 위임 뷰 dict 생성.

    urls.py에서 `**v.game_views('pokemon_kr')`처럼 풀어서 views dict에 병합해 쓴다.
    """
    return {
        name: _make_game_view(base_view, cfg_key, require_post)
        for name, base_view, require_post in _GAME_VIEW_TYPES
    }


# ════════════════════════════════════════════════════════════════
# 포켓몬 한글판 — 뷰
# ════════════════════════════════════════════════════════════════

@staff_required
def pokemon_kr_expansion_list(request):
    return _expansion_list_view(request, 'pokemon_kr', {
        'bulk_price_url':          '/pokemon/kr/bulk-price/',
        'card_search_url':         '/pokemon/kr/cards/search/',
        'reset_prices_url_prefix': '/pokemon/kr/expansions/',
        'reset_all_url':           '/pokemon/kr/reset-all-prices/',
    })


@staff_required
def pokemon_kr_card_list(request, code):
    expansion = get_object_or_404(Expansion, code=code)
    return _card_list_view(request, 'pokemon_kr', code, {
        'bulk_price_url':   f'/pokemon/kr/bulk-price/?expansion={expansion.code}',
        'reset_prices_url': f'/pokemon/kr/expansions/{expansion.code}/reset-prices/',
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
def pokemon_kr_shop_stats(request):
    raw_list = _load_raw_data(Card)
    shop_stats, overall_avg = _calc_shop_stats(raw_list)
    expansions = Expansion.objects.order_by('-release_date')
    return render(request, 'dashboard/shop_stats.html', {
        'shop_stats_json':  safe_json_dumps(shop_stats, ensure_ascii=False),
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
    raw_list = _load_raw_data(Card, expansion_code=code)
    shop_stats, overall_avg = _calc_shop_stats(raw_list)
    expansions = Expansion.objects.order_by('-release_date')
    return render(request, 'dashboard/shop_stats.html', {
        'shop_stats_json':  safe_json_dumps(shop_stats, ensure_ascii=False),
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


# ════════════════════════════════════════════════════════════════
# 디지몬 한글판 — 뷰
# ════════════════════════════════════════════════════════════════

@staff_required
def digimon_kr_expansion_list(request):
    return _expansion_list_view(request, 'digimon_kr', {
        'bulk_price_url':          '/digimon/kr/bulk-price/',
        'card_search_url':         '/digimon/kr/cards/search/',
        'reset_prices_url_prefix': '/digimon/kr/expansions/',
        'reset_all_url':           '/digimon/kr/reset-all-prices/',
    })


@staff_required
def digimon_kr_card_list(request, code):
    expansion = get_object_or_404(DigimonExpansion, code=code)
    return _card_list_view(request, 'digimon_kr', code, {
        'bulk_price_url':   f'/digimon/kr/bulk-price/?expansion={expansion.code}',
        'reset_prices_url': f'/digimon/kr/expansions/{expansion.code}/reset-prices/',
    })


@staff_required
@require_POST
def digimon_kr_set_price(request, pk):
    return _set_price(DigimonCard, pk, request)


@staff_required
def digimon_kr_card_search(request):
    return _card_search_view(request, DigimonCard)


@staff_required
@require_POST
def digimon_kr_reset_prices(request, expansion_code):
    count = DigimonCard.objects.filter(expansion__code=expansion_code).update(selling_price=0)
    return JsonResponse({'success': True, 'count': count})


@staff_required
@require_POST
def digimon_kr_reset_all_prices(request):
    count = DigimonCard.objects.all().update(selling_price=0)
    return JsonResponse({'success': True, 'count': count})


@staff_required
@require_POST
def digimon_kr_toggle_favorite(request, card_id):
    try:
        card = DigimonCard.objects.get(pk=card_id)
    except DigimonCard.DoesNotExist:
        return JsonResponse({'error': '카드를 찾을 수 없습니다.'}, status=404)
    card.is_favorite = not card.is_favorite
    card.save(update_fields=['is_favorite'])
    return JsonResponse({'success': True, 'is_favorite': card.is_favorite})