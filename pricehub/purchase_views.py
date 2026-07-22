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

from .models import PurchaseList, PurchaseListItem, RarityPurchasePrice, round_to_100
from .purchase_config import (
    GAME_TYPE_CARD_MODEL, GAME_TYPE_LABELS, RARITY_PRICE_GAME_TYPES,
    attach_cards, compute_rarity_price, get_rarity_price_map,
)
from .views import staff_required


# ════════════════════════════════════════════════════════════════
# 개요 (게임별 매입리스트 목록 + 새 리스트 생성)
# ════════════════════════════════════════════════════════════════

@staff_required
def purchase_list_index(request):
    """
    게임별 매입리스트 목록. 리스트가 쌓일수록(게임 종류가 늘거나, 주기적으로
    새 리스트를 만들수록) 화면이 길어지는 걸 막기 위해 게임당 가장 최근
    리스트만 상단에 바로 보여주고, 나머지는 접어둔다.
    """
    games = []
    for game_type, label in GAME_TYPE_LABELS.items():
        lists = list(
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
            'latest_list': lists[0] if lists else None,
            'older_lists': lists[1:],
            'list_count': len(lists),
            'active_count': sum(1 for l in lists if l.is_active),
            'supports_rarity': game_type in RARITY_PRICE_GAME_TYPES,
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
    매입리스트 상세 — 개별 등록한 카드만 보여준다(인기 카드 위주라 보통
    많지 않음). 나머지 카드는 이 화면에서 목록으로 보여주지 않고, 검색
    결과에서 큰 이미지로 확인하며 필요할 때만 추가한다(제목은 같은데
    이미지가 다른 카드가 많아 작은 목록보다 큰 이미지 확인이 중요함).
    """
    plist = get_object_or_404(PurchaseList, pk=list_id)
    items = list(plist.items.select_related('content_type').order_by('-added_at'))
    attach_cards(items)

    # 카드의 판매가가 추가 시점 이후 바뀌었을 수 있으므로, 현재 판매가로 스냅샷을 갱신하고
    # 추천 매입가를 다시 계산해 보여준다.
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
        )
        .order_by('name', 'card_number')[:60]
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


@staff_required
@require_POST
def purchase_list_copy(request, list_id):
    """
    기존 매입리스트를 복사해서 새 리스트를 만든다. 담긴 카드와 매입가
    (확정가/추천가 포함)를 전부 그대로 복사 — 반복되는 매입 주기마다
    이전 리스트를 시작점으로 삼아 필요한 카드만 조정하는 용도.
    """
    source = get_object_or_404(PurchaseList, pk=list_id)

    name = (request.POST.get('name') or '').strip() or f"{source.name} 복사본"

    new_list = PurchaseList.objects.create(
        name=name,
        game_type=source.game_type,
        description=source.description,
        default_purchase_ratio=source.default_purchase_ratio,
    )

    PurchaseListItem.objects.bulk_create([
        PurchaseListItem(
            purchase_list=new_list,
            content_type_id=it.content_type_id,
            object_id=it.object_id,
            selling_price_snapshot=it.selling_price_snapshot,
            purchase_ratio=it.purchase_ratio,
            recommended_purchase_price=it.recommended_purchase_price,
            purchase_price=it.purchase_price,
            memo=it.memo,
            decided_at=it.decided_at,
        )
        for it in source.items.all()
    ])

    return JsonResponse({
        'success': True,
        'redirect': f'/purchase-lists/detail/{new_list.id}/',
    })


# ════════════════════════════════════════════════════════════════
# 레어도별 매입 고정가 관리
#
# 매입리스트에 개별 등록 안 된 카드는 여기서 정한 고정가를 즉석으로
# 보여준다(별도 행을 만들지 않음). 게임 종류 전체에 공통 적용 —
# 일본판은 판매가 통화(엔)가 달라 대상에서 제외한다.
# ════════════════════════════════════════════════════════════════

@staff_required
def rarity_price_settings(request, game_type):
    if game_type not in RARITY_PRICE_GAME_TYPES:
        return redirect('pricehub:purchase-list-index')

    card_model = GAME_TYPE_CARD_MODEL[game_type]
    all_rarities = list(
        card_model.objects.exclude(rarity='').values_list('rarity', flat=True)
        .distinct().order_by('rarity')
    )
    price_map = get_rarity_price_map(game_type)
    rows = [{'rarity': r, 'price': price_map.get(r)} for r in all_rarities]

    return render(request, 'dashboard/rarity_price_settings.html', {
        'game_type': game_type,
        'game_label': GAME_TYPE_LABELS.get(game_type, game_type),
        'rows': rows,
    })


@staff_required
@require_POST
def rarity_price_save(request, game_type):
    """레어도 하나의 매입 고정가를 저장 (AJAX, upsert)."""
    if game_type not in RARITY_PRICE_GAME_TYPES:
        return JsonResponse({'success': False, 'error': '지원하지 않는 게임 종류입니다.'}, status=400)

    try:
        data = json.loads(request.body)
        rarity = (data.get('rarity') or '').strip()
        price = int(data['price'])
        if price < 0:
            raise ValueError
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        return JsonResponse({'success': False, 'error': '잘못된 요청입니다.'}, status=400)

    if not rarity:
        return JsonResponse({'success': False, 'error': '레어도가 비어있습니다.'}, status=400)

    obj, _ = RarityPurchasePrice.objects.update_or_create(
        game_type=game_type, rarity=rarity,
        defaults={'price': price},
    )
    return JsonResponse({'success': True, 'price': obj.price})
