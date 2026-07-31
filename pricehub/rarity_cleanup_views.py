"""
pricehub/rarity_cleanup_views.py

원피스·디지몬 카드 레어도 정리 도구.

배경: 신제품(새 확장팩) 카탈로그를 크롤링해서 등록할 때, 같은 카드번호가
이미 있으면(패러렐/희소/스페셜/망가 등 변형) 크롤러가 몇 번째로 중복됐는지만
보고 레어도를 추정해서 저장한다:
  - 디지몬(scripts/catalog/save_digimon_cards_to_db.py): 상품코드 뒤에
    -V1(패러렐 추정), -V2(희소 추정), -V3(스페셜 추정)을 붙인다. 패러렐은
    사이트 아이콘으로 비교적 정확히 잡히지만 희소/스페셜은 순번만 보고
    찍은 값이라 실제와 다른 경우가 많다.
  - 원피스(scripts/catalog/save_onepiece_to_db.py): 카드번호의 _P1은
    "P-{원래레어도}", _P2 이상은 무조건 MANGA로 자동 지정한다. 실제로는
    _P2 이상이 MANGA가 아니라 SP 등 다른 레어도인 경우가 많다.

신제품 등록마다 반복되는 수동 보정 작업이라, 같은 카드번호(원피스는 _P
접미사를 뗀 기준)끼리 묶어서 이미지와 함께 보여주고 작업자가 직접 올바른
분류를 골라 저장하게 하는 표준 도구로 만든다.
"""
import json
import re

from django.db.models import Count
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from .models import DigimonCard, OnePieceCard
from .purchase_config import GAME_TYPE_LABELS
from .views import staff_required

PAGE_SIZE = 25  # 페이지당 카드번호 그룹 수

RARITY_CLEANUP_GAME_TYPES = ['onepiece_kr', 'digimon_kr']
_GAME_MODELS = {
    'onepiece_kr': OnePieceCard,
    'digimon_kr': DigimonCard,
}
_DIGIMON_CLASSIFICATIONS = ('none', 'parallel', 'scarce', 'special')
_P_SUFFIX_RE = re.compile(r'_[Pp]\d+$')


def _group_key(game_type, card_number):
    """같은 실물 카드로 묶기 위한 키. 원피스는 카드번호 자체에 _P1/_P2 접미사가
    붙어있어서 떼야 한 그룹으로 묶인다(디지몬은 이미 접미사 없이 저장됨)."""
    if game_type == 'onepiece_kr':
        return _P_SUFFIX_RE.sub('', card_number)
    return card_number


def _get_model(game_type):
    model = _GAME_MODELS.get(game_type)
    if model is None:
        raise Http404(f'지원하지 않는 게임 종류: {game_type}')
    return model


@staff_required
def rarity_cleanup_view(request, game_type):
    model = _get_model(game_type)
    only_dupes = request.GET.get('all') != '1'
    try:
        min_dupes = int(request.GET.get('min', 2))
    except (TypeError, ValueError):
        min_dupes = 2
    min_dupes = max(2, min_dupes)
    page = max(1, int(request.GET.get('page', 1) or 1))

    all_numbers = list(model.objects.values_list('card_number', flat=True))
    grouped_keys = {}
    for num in all_numbers:
        grouped_keys.setdefault(_group_key(game_type, num), []).append(num)

    keys = sorted(grouped_keys.keys())
    if only_dupes:
        keys = [k for k in keys if len(grouped_keys[k]) >= min_dupes]

    total_groups = len(keys)
    total_pages = max(1, -(-total_groups // PAGE_SIZE))
    page = min(page, total_pages)
    offset = (page - 1) * PAGE_SIZE
    page_keys = keys[offset:offset + PAGE_SIZE]

    numbers_on_page = [num for k in page_keys for num in grouped_keys[k]]
    cards = (
        model.objects
        .filter(card_number__in=numbers_on_page)
        .select_related('expansion')
        .order_by('card_number', 'shop_product_code')
    )
    by_key = {}
    for c in cards:
        by_key.setdefault(_group_key(game_type, c.card_number), []).append(c)
    groups = [(k, by_key[k]) for k in page_keys if k in by_key]

    _half = 3
    start = max(1, page - _half)
    end = min(total_pages, page + _half)
    if end - start < 6:
        if start == 1:
            end = min(total_pages, start + 6)
        else:
            start = max(1, end - 6)
    page_range = list(range(start, end + 1))

    return render(request, 'dashboard/rarity_cleanup.html', {
        'game_type': game_type,
        'game_label': GAME_TYPE_LABELS.get(game_type, game_type),
        'groups': groups,
        'page': page,
        'total_pages': total_pages,
        'total_groups': total_groups,
        'page_range': page_range,
        'only_dupes': only_dupes,
        'min_dupes': min_dupes,
        'onepiece_rarity_choices': OnePieceCard.RARITY_CHOICES if game_type == 'onepiece_kr' else None,
    })


@staff_required
@require_POST
def rarity_cleanup_save(request, game_type, card_id):
    model = _get_model(game_type)
    card = get_object_or_404(model, pk=card_id)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '잘못된 요청입니다.'}, status=400)

    if game_type == 'digimon_kr':
        classification = data.get('classification')
        if classification not in _DIGIMON_CLASSIFICATIONS:
            return JsonResponse({'success': False, 'error': '올바른 값을 선택하세요.'}, status=400)
        card.is_parallel = classification == 'parallel'
        card.is_scarce = classification == 'scarce'
        card.is_special = classification == 'special'
        card.save(update_fields=['is_parallel', 'is_scarce', 'is_special'])
        return JsonResponse({'success': True})

    if game_type == 'onepiece_kr':
        rarity = data.get('rarity')
        if rarity not in dict(OnePieceCard.RARITY_CHOICES):
            return JsonResponse({'success': False, 'error': '올바른 레어도를 선택하세요.'}, status=400)
        card.rarity = rarity
        card.save(update_fields=['rarity'])
        return JsonResponse({'success': True})

    return JsonResponse({'success': False, 'error': '지원하지 않는 게임 종류입니다.'}, status=400)
