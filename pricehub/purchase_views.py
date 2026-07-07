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

from .models import PurchaseList, PurchaseListItem, round_to_100
from .purchase_config import GAME_TYPE_CARD_MODEL, GAME_TYPE_LABELS, attach_cards
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
    plist = get_object_or_404(PurchaseList, pk=list_id)
    items = list(plist.items.select_related('content_type').order_by('-added_at'))
    attach_cards(items)

    # 카드의 판매가가 추가 시점 이후 바뀌었을 수 있으므로, 현재 판매가로 스냅샷을 갱신하고
    # 추천 매입가(50% 등)를 다시 계산해 보여준다.
    for item in items:
        card = item.cached_card
        if card is None:
            continue
        current_price = getattr(card, 'selling_price', 0) or 0
        if item.selling_price_snapshot != current_price:
            item.selling_price_snapshot = current_price
            item.save(update_fields=['selling_price_snapshot', 'recommended_purchase_price'])

    rows = [{'item': item, 'card': item.cached_card} for item in items]

    return render(request, 'dashboard/purchase_list_detail.html', {
        'plist': plist,
        'rows': rows,
        'game_label': GAME_TYPE_LABELS.get(plist.game_type, plist.game_type),
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
