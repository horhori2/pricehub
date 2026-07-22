"""
pricehub/purchase_api_views.py

매입리스트 외부 연동 API — API Key 인증 (기존 카드 API와 동일한 방식).

    GET /api/purchase-lists/                 매입리스트 목록
    GET /api/purchase-lists/<id>/            매입리스트 상세 (카드 목록 + 이미지 + 매입가 포함)
    GET /api/purchase-lists/<id>/items/      매입리스트 카드 목록만 (페이지네이션, decided_only 필터 지원)

모든 엔드포인트: Authorization: Api-Key <your-key>
"""
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, filters
from rest_framework.response import Response
from rest_framework.views import APIView

from .authentication import APIKeyAuthentication
from .models import PurchaseList, PurchaseListItem
from .permissions import HasAPIKey
from .purchase_config import (
    GAME_TYPE_CARD_MODEL, RARITY_PRICE_GAME_TYPES,
    attach_cards, compute_rarity_price, get_rarity_price_map,
)
from .serializers import (
    PurchaseListDetailSerializer,
    PurchaseListItemSerializer,
    PurchaseListSerializer,
)


class PurchaseListMixin:
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [HasAPIKey]


def _annotated_qs():
    return PurchaseList.objects.annotate(
        item_count=Count('items', distinct=True),
        decided_count=Count('items', filter=Q(items__purchase_price__isnull=False), distinct=True),
    )


class PurchaseLookupView(PurchaseListMixin, APIView):
    """
    상품코드로 카드의 매입가를 조회 — 오프라인 매장 연동용.

    GET /api/purchase-lists/lookup/?game_type=pokemon_kr&shop_product_code=PKM-m2-001-K

    매입가 결정 순서:
      1. 해당 게임 종류에서 가장 최근에 만든 활성(is_active) 매입리스트에
         카드가 개별 등록돼 있으면 그 확정가(없으면 추천가)를 반환.
      2. 등록 안 돼 있으면 레어도별 매입 고정가(설정된 경우)를 반환
         (일본판은 통화가 달라 미지원).
      3. 둘 다 없으면 purchase_price는 null.
    """
    def get(self, request):
        game_type = request.query_params.get('game_type')
        code = (request.query_params.get('shop_product_code') or '').strip()

        card_model = GAME_TYPE_CARD_MODEL.get(game_type)
        if card_model is None:
            return Response({'error': '유효하지 않은 game_type입니다.'}, status=400)
        if not code:
            return Response({'error': 'shop_product_code가 필요합니다.'}, status=400)

        try:
            card = card_model.objects.select_related('expansion').get(shop_product_code=code)
        except card_model.DoesNotExist:
            return Response({'found': False, 'error': '해당 상품코드의 카드를 찾을 수 없습니다.'}, status=404)

        card_data = {
            'id': card.id,
            'name': card.name,
            'card_number': getattr(card, 'card_number', None),
            'rarity': getattr(card, 'rarity', None),
            'shop_product_code': card.shop_product_code,
            'image_url': getattr(card, 'image_url', None),
            'expansion': (
                {'code': card.expansion.code, 'name': card.expansion.name}
                if getattr(card, 'expansion', None) else None
            ),
        }

        purchase_price = None
        price_source = None
        purchase_list_data = None

        active_list = (
            PurchaseList.objects
            .filter(game_type=game_type, is_active=True)
            .order_by('-created_at')
            .first()
        )
        if active_list is not None:
            content_type = ContentType.objects.get_for_model(card_model)
            item = PurchaseListItem.objects.filter(
                purchase_list=active_list, content_type=content_type, object_id=card.id,
            ).first()
            if item is not None:
                purchase_price = item.final_purchase_price
                price_source = 'registered'
                purchase_list_data = {'id': active_list.id, 'name': active_list.name}

        if purchase_price is None and game_type in RARITY_PRICE_GAME_TYPES:
            price_map = get_rarity_price_map(game_type)
            rarity_price = compute_rarity_price(card, price_map)
            if rarity_price is not None:
                purchase_price = rarity_price
                price_source = 'rarity_fixed'

        return Response({
            'found': True,
            'card': card_data,
            'purchase_price': purchase_price,
            'price_source': price_source,
            'purchase_list': purchase_list_data,
        })


class PurchaseListListView(PurchaseListMixin, generics.ListAPIView):
    """
    매입리스트 목록.

    Query Params:
      game_type   게임 구분 필터 (pokemon_kr / pokemon_jp / onepiece_kr / digimon_kr)
      is_active   활성 여부 (true/false)
      ordering    정렬 (기본: -created_at)
    """
    serializer_class = PurchaseListSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'updated_at', 'name']
    ordering = ['-created_at']

    def get_queryset(self):
        qs = _annotated_qs()
        game_type = self.request.query_params.get('game_type')
        if game_type:
            qs = qs.filter(game_type=game_type)
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() in ('1', 'true', 'yes'))
        return qs


class PurchaseListDetailView(PurchaseListMixin, generics.RetrieveAPIView):
    """매입리스트 상세 — 카드 목록 / 이미지 / 카드 정보 / 매입가 포함"""
    serializer_class = PurchaseListDetailSerializer

    def get_queryset(self):
        return _annotated_qs()

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        items = list(instance.items.select_related('content_type').order_by('-added_at'))
        attach_cards(items)
        instance._prefetched_items = items
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class PurchaseListItemsView(PurchaseListMixin, generics.ListAPIView):
    """
    매입리스트에 담긴 카드 목록만 조회 (카드 정보 + 이미지 + 매입가).

    Query Params:
      decided_only  매입가가 확정된 카드만 (true/false)
      ordering      정렬 (기본: -added_at)
    """
    serializer_class = PurchaseListItemSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['added_at', 'decided_at', 'purchase_price']
    ordering = ['-added_at']

    def get_queryset(self):
        plist = get_object_or_404(PurchaseList, pk=self.kwargs['pk'])
        qs = plist.items.select_related('content_type')
        decided_only = self.request.query_params.get('decided_only')
        if decided_only is not None and decided_only.lower() in ('1', 'true', 'yes'):
            qs = qs.filter(purchase_price__isnull=False)
        return qs

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        items = list(queryset)
        attach_cards(items)
        page = self.paginate_queryset(items)
        serializer = self.get_serializer(page if page is not None else items, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)
