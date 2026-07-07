"""
pricehub/purchase_config.py

매입리스트 기능에서 공통으로 쓰는 게임 타입 ↔ 카드 모델 매핑,
그리고 GenericForeignKey 조회 시 N+1 쿼리를 막기 위한 유틸.
"""
from collections import defaultdict

from django.contrib.contenttypes.models import ContentType

from .models import Card, JapanCard, OnePieceCard, DigimonCard

GAME_TYPE_CARD_MODEL = {
    'pokemon_kr': Card,
    'pokemon_jp': JapanCard,
    'onepiece_kr': OnePieceCard,
    'digimon_kr': DigimonCard,
}

GAME_TYPE_LABELS = {
    'pokemon_kr': '포켓몬 한글판',
    'pokemon_jp': '포켓몬 일본판',
    'onepiece_kr': '원피스 한글판',
    'digimon_kr': '디지몬 한글판',
}


def get_card_model(game_type):
    model = GAME_TYPE_CARD_MODEL.get(game_type)
    if model is None:
        raise ValueError(f"알 수 없는 game_type: {game_type}")
    return model


def attach_cards(items):
    """
    PurchaseListItem 목록에 대해 GenericForeignKey를 N+1 없이 일괄 조회하여
    각 item에 _card_cache 속성으로 붙여준다. (item.cached_card 로 사용)

    items: PurchaseListItem 쿼리셋 또는 리스트 (list()로 평가된 상태여야 함)
    """
    items = list(items)
    by_content_type = defaultdict(list)
    for item in items:
        by_content_type[item.content_type_id].append(item.object_id)

    cards_by_ct = {}
    for ct_id, obj_ids in by_content_type.items():
        ct = ContentType.objects.get_for_id(ct_id)
        model = ct.model_class()
        qs = model.objects.filter(id__in=obj_ids)
        # expansion 필드가 있는 모델만 select_related
        if any(f.name == 'expansion' for f in model._meta.get_fields()):
            qs = qs.select_related('expansion')
        cards_by_ct[ct_id] = {c.id: c for c in qs}

    for item in items:
        item._card_cache = cards_by_ct.get(item.content_type_id, {}).get(item.object_id)

    return items
