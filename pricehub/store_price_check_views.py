"""
pricehub/store_price_check_views.py

"스토어 가격 비교" 화면 — card-controltower(네이버 스마트스토어 관리 백엔드)가 알려주는
매장별 실제 판매가/판매상태를 PriceHub 자체 판매가와 대조해서 보여준다.
로직은 store_price_check.py, HTTP 호출은 card_controltower_client.py.
"""
from django.conf import settings
from django.http import Http404
from django.shortcuts import render, redirect

from .views import staff_required
from . import card_controltower_client, store_price_check
from .card_controltower_client import CardControltowerAPIError
from .utils import safe_json_dumps

_TABS = ('drop', 'rise', 'unregistered')
_PER_PAGE = 100


@staff_required
def store_price_check_index(request):
    return redirect('pricehub:store-price-check', store='gwangju')


@staff_required
def store_price_check_view(request, store):
    if store not in settings.CARD_CONTROLTOWER_STORES:
        raise Http404(f'알 수 없는 매장: {store}')

    force_refresh = request.GET.get('refresh') == '1'
    error = None
    drops, rises, unregistered = [], [], []

    try:
        # 부산/광주 이미지를 나란히 보여주려면 보고 있는 매장뿐 아니라 전 매장 데이터가 필요.
        all_store_cards = card_controltower_client.fetch_all_store_cards(force_refresh=force_refresh)
        drops, rises, unregistered = store_price_check.categorize(all_store_cards, store)
    except CardControltowerAPIError as e:
        error = str(e)

    tab = request.GET.get('tab', 'drop')
    if tab not in _TABS:
        tab = 'drop'
    rows = {'drop': drops, 'rise': rises, 'unregistered': unregistered}[tab]

    q = request.GET.get('q', '').strip()
    if q:
        rows = [
            r for r in rows
            if q in (r.get('productName') or '') or q in (r.get('sellerProductCode') or '')
        ]

    total_count = len(rows)
    page = max(1, int(request.GET.get('page', 1) or 1))
    total_pages = max(1, -(-total_count // _PER_PAGE))
    page = min(page, total_pages)
    offset = (page - 1) * _PER_PAGE
    page_rows = rows[offset:offset + _PER_PAGE]

    half = 3
    start = max(1, page - half)
    end = min(total_pages, page + half)
    if end - start < 6:
        if start == 1:
            end = min(total_pages, start + 6)
        else:
            start = max(1, end - 6)
    page_range = list(range(start, end + 1))

    # 판매처 목록 사이드 패널 — 지금 보이는 페이지 분량만 조회(카드 목록 페이지와 동일 패턴).
    card_raw = store_price_check.fetch_market_raw_data(page_rows)

    return render(request, 'dashboard/store_price_check.html', {
        'error': error,
        'store': store,
        'store_label': settings.CARD_CONTROLTOWER_STORES[store]['label'],
        'stores': settings.CARD_CONTROLTOWER_STORES,
        'tab': tab,
        'q': q,
        'rows': page_rows,
        'card_raw_json': safe_json_dumps(card_raw, ensure_ascii=False),
        'counts': {'drop': len(drops), 'rise': len(rises), 'unregistered': len(unregistered)},
        'total_count': total_count,
        'page': page,
        'total_pages': total_pages,
        'page_range': page_range,
        'breadcrumb': [
            ('홈', '/'),
            ('스토어 가격 비교', None),
        ],
    })
