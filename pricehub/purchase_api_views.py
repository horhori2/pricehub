"""
pricehub/purchase_api_views.py

매입리스트 외부 연동 API — API Key 인증 (기존 카드 API와 동일한 방식).

    GET /api/purchase-lists/                 매입리스트 목록
    GET /api/purchase-lists/<id>/            매입리스트 상세 (카드 목록 + 이미지 + 매입가 포함)
    GET /api/purchase-lists/<id>/items/      매입리스트 카드 목록만 (페이지네이션, decided_only 필터 지원)

모든 엔드포인트: Authorization: Api-Key <your-key>
"""
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, filters
from rest_framework.response import Response

from .authentication import APIKeyAuthentication
from .models import PurchaseList
from .permissions import HasAPIKey
from .purchase_config import attach_cards
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
