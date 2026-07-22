"""
pricehub/purchase_views.py

매입리스트 관리 대시보드 (staff 전용).
- 게임별(포켓몬/원피스/디지몬 등) 매입리스트를 만들고, 개별 카드를 담아 매입가를 결정한다.
- 추천 매입가 = 판매가 × 매입리스트의 매입가 비율(기본 50%). 최종 결정은 가격 관리자가 확정.
"""
import json

from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .models import PurchaseList, PurchaseListItem, RarityPurchaseRatio, round_to_100
from .purchase_config import (
    GAME_TYPE_CARD_MODEL, GAME_TYPE_LABELS, RARITY_RATIO_GAME_TYPES,
    compute_rarity_price, get_rarity_ratio_map,
)
from .utils import safe_json_dumps
from .views import staff_required


# ════════════════════════════════════════════════════════════════
# 개요 (게임별 매입리스트 목록 + 새 리스트 생성)
# ════════════════════════════════════════════════════════════════

@staff_required
def purchase_list_index(request):
    games = []
    for game_type, label in GAME_TYPE_LABELS.items():
        qs = (
            PurchaseList.objects
            .filter(game_type=game_type)
            .annotate(
                item_count=Count('items', distinct=True),
                decided_count=Count(
                    'items', filter=Q(items__purchase_price__isnull=False), distinct=True
                ),
            )
            .order_by('-created_at')
        )
        games.append({
            'game_type': game_type,
            'label': label,
            'lists': qs,
            'list_count': qs.count(),
            'active_count': qs.filter(is_active=True).count(),
            'supports_rarity': game_type in RARITY_RATIO_GAME_TYPES,
        })
    return render(request, 'dashboard/purchase_list_index.html', {'games': games})


@staff_required
@require_POST
def purchase_list_create(request, game_type):
    if game_type not in GAME_TYPE_CARD_MODEL:
        return JsonResponse({'success': False, 'error': '알 수 없는 게임 종류입니다.'}, status=400)

    name = (request.POST.get('name') or '').strip()
    if not name:
        return redirect('pricehub:purchase-list-index')

    try:
        ratio = float(request.POST.get('default_purchase_ratio', '50'))
    except (TypeError, ValueError):
        ratio = 50
    ratio = max(0, min(100, ratio))

    plist = PurchaseList.objects.create(
        name=name,
        game_type=game_type,
        description=(request.POST.get('description') or '').strip(),
        default_purchase_ratio=ratio,
    )
    return redirect('pricehub:purchase-list-detail', list_id=plist.id)


# ════════════════════════════════════════════════════════════════
# 매입리스트 상세 (카드 검색/추가 + 매입가 결정)
# ════════════════════════════════════════════════════════════════

@staff_required
def purchase_list_detail(request, list_id):
    """
    매입리스트 상세 — 전체 카드를 등록/미등록 구분 없이 한 화면에 보여준다.
    등록된 카드는 확정/추천 매입가(판매가 기준)를, 미등록 카드는 레어도별
    비율(관리 화면에서 설정) × 시장 최저가로 즉석 계산한 값을 보여준다
    (미등록 카드는 DB에 별도 행을 만들지 않음 — 화면에 보여줄 때만 계산).
    """
    plist = get_object_or_404(PurchaseList, pk=list_id)
    card_model = GAME_TYPE_CARD_MODEL.get(plist.game_type)
    content_type = ContentType.objects.get_for_model(card_model)
    expansion_model = card_model._meta.get_field('expansion').related_model

    registered_map = {
        it.object_id: it
        for it in plist.items.filter(content_type=content_type)
    }

    supports_rarity = plist.game_type in RARITY_RATIO_GAME_TYPES
    ratio_map = get_rarity_ratio_map(plist.game_type) if supports_rarity else {}

    cards_qs = card_model.objects.select_related('expansion').order_by('card_number')

    expansion_code = request.GET.get('expansion', '')
    if expansion_code:
        cards_qs = cards_qs.filter(expansion__code=expansion_code)

    all_rarities = list(
        card_model.objects.exclude(rarity='').values_list('rarity', flat=True)
        .distinct().order_by('rarity')
    )
    selected_rarities = request.GET.getlist('rarities')
    if selected_rarities:
        cards_qs = cards_qs.filter(rarity__in=selected_rarities)

    status_filter = request.GET.get('status', 'all')
    if status_filter == 'registered':
        cards_qs = cards_qs.filter(id__in=registered_map.keys())
    elif status_filter == 'unregistered':
        cards_qs = cards_qs.exclude(id__in=registered_map.keys())

    # 페이지네이션
    per_page = 100
    total_count = cards_qs.count()
    page = max(1, int(request.GET.get('page', 1) or 1))
    total_pages = max(1, -(-total_count // per_page))
    page = min(page, total_pages)
    offset = (page - 1) * per_page
    cards_page = list(cards_qs[offset:offset + per_page])

    rows = []
    for card in cards_page:
        item = registered_map.get(card.id)
        if item is not None:
            # 판매가가 추가 시점 이후 바뀌었을 수 있으므로 현재가로 갱신 후 추천가 재계산
            current_price = getattr(card, 'selling_price', 0) or 0
            if item.selling_price_snapshot != current_price:
                item.selling_price_snapshot = current_price
                item.save(update_fields=['selling_price_snapshot', 'recommended_purchase_price'])
            rows.append({'registered': True, 'card': card, 'item': item})
        else:
            rows.append({
                'registered': False,
                'card': card,
                'market_price': getattr(card, 'latest_market_price', None),
                'ratio': ratio_map.get(card.rarity),
                'computed_price': compute_rarity_price(card, ratio_map) if supports_rarity else None,
            })

    _half = 3
    _start = max(1, page - _half)
    _end = min(total_pages, page + _half)
    if _end - _start < 6:
        if _start == 1:
            _end = min(total_pages, _start + 6)
        else:
            _start = max(1, _end - 6)
    page_range = list(range(_start, _end + 1))

    return render(request, 'dashboard/purchase_list_detail.html', {
        'plist': plist,
        'rows': rows,
        'game_label': GAME_TYPE_LABELS.get(plist.game_type, plist.game_type),
        'supports_rarity': supports_rarity,
        'total_count': total_count,
        'registered_count': len(registered_map),
        'expansions': expansion_model.objects.order_by('-release_date'),
        'expansion_code': expansion_code,
        'all_rarities': all_rarities,
        'selected_rarities': selected_rarities,
        'selected_rarities_json': safe_json_dumps(selected_rarities),
        'status_filter': status_filter,
        'page': page,
        'total_pages': total_pages,
        'page_range': page_range,
    })


@staff_required
@require_GET
def purchase_list_search_cards(request, list_id):
    """리스트에 담을 카드를 검색 (AJAX). 이름 / 카드번호 / 상품코드로 검색."""
    plist = get_object_or_404(PurchaseList, pk=list_id)
    model = GAME_TYPE_CARD_MODEL.get(plist.game_type)
    if model is None:
        return JsonResponse({'results': []})

    q = (request.GET.get('q') or '').strip()
    if not q:
        return JsonResponse({'results': []})

    qs = (
        model.objects.select_related('expansion')
        .filter(
            Q(name__icontains=q)
            | Q(card_number__icontains=q)
            | Q(shop_product_code__icontains=q)
        )[:20]
    )

    content_type = ContentType.objects.get_for_model(model)
    existing_ids = set(
        plist.items.filter(content_type=content_type).values_list('object_id', flat=True)
    )

    ratio = float(plist.default_purchase_ratio)
    results = []
    for c in qs:
        selling_price = getattr(c, 'selling_price', 0) or 0
        results.append({
            'id': c.id,
            'name': c.name,
            'card_number': getattr(c, 'card_number', ''),
            'rarity': getattr(c, 'rarity', ''),
            'image_url': getattr(c, 'image_url', ''),
            'expansion_name': c.expansion.name if getattr(c, 'expansion', None) else '',
            'selling_price': selling_price,
            'recommended_purchase_price': round_to_100(selling_price * ratio / 100),
            'already_added': c.id in existing_ids,
        })
    return JsonResponse({'results': results})


@staff_required
@require_POST
def purchase_list_add_card(request, list_id):
    """검색된 카드를 매입리스트에 추가 (AJAX)."""
    plist = get_object_or_404(PurchaseList, pk=list_id)
    model = GAME_TYPE_CARD_MODEL.get(plist.game_type)
    if model is None:
        return JsonResponse({'success': False, 'error': '알 수 없는 게임 종류입니다.'}, status=400)

    try:
        data = json.loads(request.body)
        card_id = int(data.get('card_id'))
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({'success': False, 'error': '잘못된 요청입니다.'}, status=400)

    card = get_object_or_404(model, pk=card_id)
    content_type = ContentType.objects.get_for_model(model)

    item, created = PurchaseListItem.objects.get_or_create(
        purchase_list=plist,
        content_type=content_type,
        object_id=card.id,
        defaults={
            'selling_price_snapshot': getattr(card, 'selling_price', 0) or 0,
            'purchase_ratio': plist.default_purchase_ratio,
        },
    )
    if not created:
        return JsonResponse({'success': False, 'error': '이미 매입리스트에 추가된 카드입니다.'})

    return JsonResponse({
        'success': True,
        'item': {
            'id': item.id,
            'card_name': card.name,
            'card_number': getattr(card, 'card_number', ''),
            'rarity': getattr(card, 'rarity', ''),
            'image_url': getattr(card, 'image_url', ''),
            'selling_price': item.selling_price_snapshot,
            'recommended_purchase_price': item.recommended_purchase_price,
            'purchase_ratio': float(item.purchase_ratio),
            'purchase_price': item.purchase_price,
        },
    })


@staff_required
@require_POST
def purchase_list_set_price(request, item_id):
    """
    가격 관리자가 매입가를 확정/수정 (AJAX).

    body 예시:
      {"purchase_price": 12000}   → 매입가 확정
      {"purchase_ratio": 45}      → 비율을 바꿔 추천가만 재계산 (확정은 유지되지 않음)
      {"clear": true}             → 확정 취소 (다시 추천가 상태로)
    """
    item = get_object_or_404(PurchaseListItem, pk=item_id)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '잘못된 요청입니다.'}, status=400)

    if data.get('clear'):
        item.purchase_price = None
        item.decided_at = None
        item.save(update_fields=['purchase_price', 'decided_at'])
        return JsonResponse({
            'success': True,
            'purchase_price': None,
            'recommended_purchase_price': item.recommended_purchase_price,
        })

    if 'purchase_ratio' in data:
        try:
            ratio = float(data['purchase_ratio'])
        except (TypeError, ValueError):
            return JsonResponse({'success': False, 'error': '비율 값이 올바르지 않습니다.'}, status=400)
        item.purchase_ratio = max(0, min(100, ratio))
        item.save(update_fields=['purchase_ratio', 'recommended_purchase_price'])
        return JsonResponse({
            'success': True,
            'recommended_purchase_price': item.recommended_purchase_price,
            'purchase_ratio': float(item.purchase_ratio),
        })

    if 'purchase_price' in data:
        try:
            price = int(data['purchase_price'])
            if price < 0:
                raise ValueError
        except (TypeError, ValueError):
            return JsonResponse({'success': False, 'error': '올바른 매입가를 입력하세요.'}, status=400)
        item.purchase_price = price
        item.decided_at = timezone.now()
        item.save(update_fields=['purchase_price', 'decided_at'])
        return JsonResponse({
            'success': True,
            'purchase_price': item.purchase_price,
            'decided_at': item.decided_at.strftime('%Y-%m-%d %H:%M'),
        })

    return JsonResponse({'success': False, 'error': '변경할 값이 없습니다.'}, status=400)


@staff_required
@require_POST
def purchase_list_remove_item(request, item_id):
    item = get_object_or_404(PurchaseListItem, pk=item_id)
    item.delete()
    return JsonResponse({'success': True})


@staff_required
@require_POST
def purchase_list_toggle_active(request, list_id):
    plist = get_object_or_404(PurchaseList, pk=list_id)
    plist.is_active = not plist.is_active
    plist.save(update_fields=['is_active'])
    return JsonResponse({'success': True, 'is_active': plist.is_active})


@staff_required
@require_POST
def purchase_list_delete(request, list_id):
    plist = get_object_or_404(PurchaseList, pk=list_id)
    plist.delete()
    return JsonResponse({'success': True, 'redirect': '/purchase-lists/'})


# ════════════════════════════════════════════════════════════════
# 레어도별 매입가 비율 관리
#
# 매입리스트에 개별 등록 안 된 카드는 여기서 정한 비율을 시장 최저가에
# 곱해 즉석 계산한 값을 보여준다(별도 행을 만들지 않음). 게임 종류 전체에
# 공통 적용 — 일본판은 판매가 통화(엔)가 달라 대상에서 제외한다.
# ════════════════════════════════════════════════════════════════

@staff_required
def rarity_ratio_settings(request, game_type):
    if game_type not in RARITY_RATIO_GAME_TYPES:
        return redirect('pricehub:purchase-list-index')

    card_model = GAME_TYPE_CARD_MODEL[game_type]
    all_rarities = list(
        card_model.objects.exclude(rarity='').values_list('rarity', flat=True)
        .distinct().order_by('rarity')
    )
    ratio_map = get_rarity_ratio_map(game_type)
    rows = [{'rarity': r, 'ratio': ratio_map.get(r)} for r in all_rarities]

    return render(request, 'dashboard/rarity_ratio_settings.html', {
        'game_type': game_type,
        'game_label': GAME_TYPE_LABELS.get(game_type, game_type),
        'rows': rows,
    })


@staff_required
@require_POST
def rarity_ratio_save(request, game_type):
    """레어도 하나의 매입가 비율을 저장 (AJAX, upsert)."""
    if game_type not in RARITY_RATIO_GAME_TYPES:
        return JsonResponse({'success': False, 'error': '지원하지 않는 게임 종류입니다.'}, status=400)

    try:
        data = json.loads(request.body)
        rarity = (data.get('rarity') or '').strip()
        ratio = float(data['ratio'])
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        return JsonResponse({'success': False, 'error': '잘못된 요청입니다.'}, status=400)

    if not rarity:
        return JsonResponse({'success': False, 'error': '레어도가 비어있습니다.'}, status=400)
    ratio = max(0, min(100, ratio))

    obj, _ = RarityPurchaseRatio.objects.update_or_create(
        game_type=game_type, rarity=rarity,
        defaults={'ratio': ratio},
    )
    return JsonResponse({'success': True, 'ratio': float(obj.ratio)})
