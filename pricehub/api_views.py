"""
pricehub/views.py

포켓몬 한글판 가격 API — API Key 인증 적용.

모든 엔드포인트:
    Authorization: Api-Key <your-key>

엔드포인트:
    GET /api/pokemon/kr/expansions/                확장팩 목록
    GET /api/pokemon/kr/expansions/<code>/         확장팩 상세
    GET /api/pokemon/kr/expansions/<code>/cards/   카드 목록
    GET /api/pokemon/kr/cards/<id>/                카드 상세 + 가격 이력
    GET /api/pokemon/kr/cards/search/              카드 검색 & 필터링
    GET /api/pokemon/kr/prices/latest/             최신 네이버 가격
    GET /api/pokemon/kr/prices/summary/            수집 현황 요약
"""
from django.db.models import Count, Prefetch, Q, Subquery, OuterRef
from rest_framework import generics, filters
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
import django_filters

from .models import Expansion, Card, CardPrice
from .serializers import (
    ExpansionListSerializer,
    ExpansionDetailSerializer,
    CardListSerializer,
    CardDetailSerializer,
    CardPriceSerializer,
)
from .authentication import APIKeyAuthentication
from .permissions import HasAPIKey


# ── 공통 인증 설정 ──────────────────────────────────────────
API_AUTH = {
    'authentication_classes': [APIKeyAuthentication],
    'permission_classes': [HasAPIKey],
}


# ── 공통 헬퍼 ────────────────────────────────────────────────

def _card_queryset_with_latest_prices():
    return (
        Card.objects
        .select_related('expansion')
        .prefetch_related(
            Prefetch('prices', queryset=CardPrice.objects.order_by('-collected_at')),
        )
    )


# ── 1. 확장팩 목록 ───────────────────────────────────────────
# GET /api/pokemon/kr/expansions/

class ExpansionListView(generics.ListAPIView):
    """
    확장팩 목록.

    Query Params:
      search    코드·이름 검색
      ordering  정렬 (기본: -release_date)
    """
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [HasAPIKey]
    serializer_class = ExpansionListSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['code', 'name']
    ordering_fields = ['release_date', 'code', 'name']
    ordering = ['-release_date']

    def get_queryset(self):
        return Expansion.objects.annotate(card_count=Count('cards'))


# ── 확장팩 상세 ──────────────────────────────────────────────
# GET /api/pokemon/kr/expansions/<code>/

class ExpansionDetailView(generics.RetrieveAPIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [HasAPIKey]
    serializer_class = ExpansionDetailSerializer
    lookup_field = 'code'

    def get_queryset(self):
        return Expansion.objects.annotate(card_count=Count('cards'))


# ── 2. 확장팩별 카드 목록 ────────────────────────────────────
# GET /api/pokemon/kr/expansions/<code>/cards/

class ExpansionCardListView(generics.ListAPIView):
    """
    특정 확장팩의 카드 목록.
    각 카드의 최신 시장가 + 타겟 스토어가 + 관리자 설정 판매가 포함.

    Query Params:
      rarity    레어도 필터
      search    카드명·번호 검색
      ordering  정렬
    """
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [HasAPIKey]
    serializer_class = CardListSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['rarity']
    search_fields = ['name', 'card_number']
    ordering_fields = ['card_number', 'name', 'rarity']
    ordering = ['card_number']

    def get_queryset(self):
        return _card_queryset_with_latest_prices().filter(
            expansion__code=self.kwargs['code']
        )


# ── 3. 카드 상세 + 가격 이력 ─────────────────────────────────
# GET /api/pokemon/kr/cards/<id>/

class CardDetailView(generics.RetrieveAPIView):
    """
    카드 상세 + 가격 이력 + 관리자 설정 판매가.

    Query Params:
      price_limit  가격 이력 최대 개수 (기본 30)
    """
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [HasAPIKey]
    serializer_class = CardDetailSerializer

    def get_queryset(self):
        return (
            Card.objects
            .select_related('expansion')
            .prefetch_related(
                Prefetch('prices', queryset=CardPrice.objects.order_by('-collected_at')),
            )
        )

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['price_limit'] = int(self.request.query_params.get('price_limit', 30))
        return ctx


# ── 4. 카드 검색 & 가격 필터링 ───────────────────────────────
# GET /api/pokemon/kr/cards/search/

class CardFilter(django_filters.FilterSet):
    expansion    = django_filters.CharFilter(field_name='expansion__code', lookup_expr='iexact')
    name         = django_filters.CharFilter(lookup_expr='icontains')
    rarity       = django_filters.CharFilter(lookup_expr='iexact')
    min_price    = django_filters.NumberFilter(field_name='prices__price', lookup_expr='gte')
    max_price    = django_filters.NumberFilter(field_name='prices__price', lookup_expr='lte')
    has_selling_price = django_filters.BooleanFilter(field_name='selling_price', lookup_expr='isnull', exclude=True)

    class Meta:
        model = Card
        fields = ['rarity']


class CardSearchView(generics.ListAPIView):
    """
    카드 검색 + 가격 범위 필터링.

    Query Params:
      search              카드명·번호·확장팩명
      expansion           확장팩 코드
      name                카드명 부분검색
      rarity              레어도
      min_price           시장 최소가
      max_price           시장 최대가
      has_selling_price   판매가 설정 여부 (true/false)
    """
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [HasAPIKey]
    serializer_class = CardListSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = CardFilter
    search_fields = ['name', 'card_number', 'expansion__name']
    ordering_fields = ['card_number', 'name', 'rarity', 'expansion__release_date']
    ordering = ['-expansion__release_date', 'card_number']

    def get_queryset(self):
        return _card_queryset_with_latest_prices().distinct()


# ── 5. 최신 네이버 가격 ──────────────────────────────────────
# GET /api/pokemon/kr/prices/latest/

class LatestNaverPriceListView(generics.ListAPIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [HasAPIKey]
    serializer_class = CardPriceSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['collected_at', 'price']
    ordering = ['-collected_at']

    def get_queryset(self):
        from django.utils import timezone
        from datetime import timedelta
        hours = int(self.request.query_params.get('hours', 24))
        since = timezone.now() - timedelta(hours=hours)
        qs = CardPrice.objects.filter(collected_at__gte=since).select_related('card', 'card__expansion')
        expansion_code = self.request.query_params.get('expansion')
        if expansion_code:
            qs = qs.filter(card__expansion__code=expansion_code)
        return qs


# ── 6. 수집 현황 요약 ─────────────────────────────────────────
# GET /api/pokemon/kr/prices/summary/

@api_view(['GET'])
@authentication_classes([APIKeyAuthentication])
@permission_classes([HasAPIKey])
def price_collection_summary(request):
    from django.utils import timezone
    from datetime import timedelta
    from django.db.models import Count, Max

    hours = int(request.query_params.get('hours', 24))
    since = timezone.now() - timedelta(hours=hours)

    naver = CardPrice.objects.filter(collected_at__gte=since).aggregate(
        total=Count('id'), last_collected=Max('collected_at'),
    )
    return Response({
        'naver': naver,
    })