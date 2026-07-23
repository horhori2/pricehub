"""
pricehub/api_views.py

TCG 카드 가격 API — API Key 인증 적용.

모든 엔드포인트:
    Authorization: Api-Key <your-key>

포켓몬 한글판:
    GET /api/pokemon/kr/expansions/
    GET /api/pokemon/kr/expansions/<code>/
    GET /api/pokemon/kr/expansions/<code>/cards/
    GET /api/pokemon/kr/cards/<id>/
    GET /api/pokemon/kr/cards/search/
    GET /api/pokemon/kr/cards/by-product-code/<code>/
    GET /api/pokemon/kr/prices/latest/
    GET /api/pokemon/kr/prices/summary/

원피스 한글판:
    GET /api/onepiece/kr/expansions/
    GET /api/onepiece/kr/expansions/<code>/
    GET /api/onepiece/kr/expansions/<code>/cards/
    GET /api/onepiece/kr/cards/search/
    GET /api/onepiece/kr/cards/by-product-code/<code>/
"""
from datetime import timedelta

from django.utils import timezone
from django.db.models import Count, Max, Subquery, OuterRef
from rest_framework import generics, filters, status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
import django_filters

from django.shortcuts import get_object_or_404

from .models import (
    Expansion, Card, CardPrice,
    OnePieceExpansion, OnePieceCard, OnePieceCardPrice,
    DigimonExpansion, DigimonCard, DigimonCardPrice,
    JapanExpansion, JapanCard, JapanCardPrice,
)
from .serializers import (
    ExpansionListSerializer,
    ExpansionDetailSerializer,
    CardListSerializer,
    CardDetailSerializer,
    CardPriceSerializer,
    OnePieceExpansionListSerializer,
    OnePieceCardListSerializer,
    DigimonExpansionListSerializer,
    DigimonCardListSerializer,
    JapanExpansionListSerializer,
    JapanCardListSerializer,
)
from .authentication import APIKeyAuthentication
from .permissions import HasAPIKey
from .views import (
    _PRICE_HISTORY_RANGE_DAYS,
    _calc_stats,
    _jp_latest_prices,
    _jp_price_history_data,
    _parse_market_items,
    _price_history_data,
)


# ════════════════════════════════════════════════════════════════
# 공통 기반
# ════════════════════════════════════════════════════════════════

class APIKeyMixin:
    """모든 API 뷰에 공통 인증·권한을 주입하는 Mixin"""
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [HasAPIKey]


class ExpansionListMixin(APIKeyMixin, generics.ListAPIView):
    """확장팩 목록 공통 뷰 (card_count 어노테이션 + 검색·정렬)"""
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['code', 'name']
    ordering_fields = ['release_date', 'code', 'name']
    ordering = ['-release_date']

    # 하위 클래스에서 지정
    expansion_model = None

    def get_queryset(self):
        return self.expansion_model.objects.annotate(card_count=Count('cards'))


class ExpansionDetailMixin(APIKeyMixin, generics.RetrieveAPIView):
    """확장팩 상세 공통 뷰"""
    lookup_field = 'code'

    expansion_model = None

    def get_queryset(self):
        return self.expansion_model.objects.annotate(card_count=Count('cards'))


class CardListMixin(APIKeyMixin, generics.ListAPIView):
    """확장팩별 카드 목록 공통 뷰"""
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['rarity']
    search_fields = ['name', 'card_number']
    ordering_fields = ['card_number', 'name', 'rarity']
    ordering = ['card_number']

    card_model = None

    def get_queryset(self):
        return (
            self.card_model.objects
            .select_related('expansion')
            .filter(expansion__code=self.kwargs['code'])
        )


class CardSearchMixin(APIKeyMixin, generics.ListAPIView):
    """카드 검색 공통 뷰"""
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'card_number', 'expansion__name']
    ordering_fields = ['card_number', 'name', 'expansion__release_date']
    ordering = ['-expansion__release_date', 'card_number']

    card_model = None

    def get_queryset(self):
        return self.card_model.objects.select_related('expansion').distinct()


class PriceSnapshotMixin(APIKeyMixin, generics.GenericAPIView):
    """
    카드 최신 가격 스냅샷 — 한글판은 판매처별 가격 분포(market_items),
    일본판은 출처×등급별 최신 가격(latest_prices). 매일 갱신되는 값이라
    DB에 캐시하지 않고 요청마다 최신 데이터를 계산해 돌려준다.
    """
    card_model = None
    is_japan = False

    def get(self, request, pk):
        card = get_object_or_404(self.card_model, pk=pk)
        if self.is_japan:
            latest_prices = _jp_latest_prices(card)
            price_values = [int(p.price) for p in latest_prices.values()]
            data = [
                {'source': p.source, 'condition': p.condition, 'price': int(p.price)}
                for p in latest_prices.values()
            ]
            return Response({'latest_prices': data, 'stats': _calc_stats(price_values)})

        latest_price_obj = card.prices.order_by('-collected_at').first()
        market_items, stats = _parse_market_items(latest_price_obj)
        return Response({'market_items': market_items, 'stats': stats})


class PriceHistoryMixin(APIKeyMixin, generics.GenericAPIView):
    """가격 변화 그래프용 기간별(1주/1개월/1년) 이력."""
    card_model = None
    is_japan = False

    def get(self, request, pk):
        card = get_object_or_404(self.card_model, pk=pk)
        range_key = request.query_params.get('range', 'month')
        days = _PRICE_HISTORY_RANGE_DAYS.get(range_key, 30)
        if self.is_japan:
            history = _jp_price_history_data(card, days=days)
        else:
            history = _price_history_data(card, card.prices, days=days)
        return Response({'range': range_key, 'history': history})


def _card_by_product_code_view(request, shop_product_code, card_model):
    """상품코드로 카드 조회 — 포켓몬·원피스 공용"""
    qs = card_model.objects.select_related('expansion')
    try:
        card = qs.get(shop_product_code=shop_product_code)
    except card_model.DoesNotExist:
        return Response(
            {'error': f"상품코드 '{shop_product_code}'에 해당하는 카드가 없습니다."},
            status=status.HTTP_404_NOT_FOUND,
        )
    except card_model.MultipleObjectsReturned:
        card = qs.filter(shop_product_code=shop_product_code).first()

    selling_price = card.selling_price
    return Response({
        'id': card.id,
        'card_number': card.card_number,
        'name': card.name,
        'rarity': card.rarity,
        'selling_price': selling_price if selling_price != 0 else None,
        'shop_product_code': card.shop_product_code,
        'expansion': {
            'code': card.expansion.code,
            'name': card.expansion.name,
        },
    })


# ════════════════════════════════════════════════════════════════
# 포켓몬 한글판
# ════════════════════════════════════════════════════════════════

class ExpansionListView(ExpansionListMixin):
    """
    확장팩 목록.

    Query Params:
      search    코드·이름 검색
      ordering  정렬 (기본: -release_date)
    """
    serializer_class = ExpansionListSerializer
    expansion_model = Expansion


class ExpansionDetailView(ExpansionDetailMixin):
    serializer_class = ExpansionDetailSerializer
    expansion_model = Expansion


class ExpansionCardListView(CardListMixin):
    """
    특정 확장팩의 카드 목록.
    각 카드의 최신 시장가 + 타겟 스토어가 + 관리자 설정 판매가 포함.

    Query Params:
      rarity    레어도 필터
      search    카드명·번호 검색
      ordering  정렬
    """
    serializer_class = CardListSerializer
    card_model = Card

    def get_queryset(self):
        # prices를 통째로 prefetch하지 않는다 — 카드당 가격 이력이 수백 건씩
        # 쌓여 있어(raw_data 포함 용량 큼) 확장팩 전체를 순회할 때 매우
        # 느려짐. serializer가 카드별로 최신 1건만 인덱스 조회한다.
        return (
            Card.objects
            .select_related('expansion')
            .filter(expansion__code=self.kwargs['code'])
        )


class CardFilter(django_filters.FilterSet):
    expansion         = django_filters.CharFilter(field_name='expansion__code', lookup_expr='iexact')
    name              = django_filters.CharFilter(lookup_expr='icontains')
    rarity            = django_filters.CharFilter(lookup_expr='iexact')
    min_price         = django_filters.NumberFilter(field_name='prices__price', lookup_expr='gte')
    max_price         = django_filters.NumberFilter(field_name='prices__price', lookup_expr='lte')
    has_selling_price = django_filters.BooleanFilter(field_name='selling_price', lookup_expr='isnull', exclude=True)

    class Meta:
        model = Card
        fields = ['rarity']


class CardSearchView(CardSearchMixin):
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
    serializer_class = CardListSerializer
    filterset_class = CardFilter
    ordering_fields = ['card_number', 'name', 'rarity', 'expansion__release_date']
    card_model = Card

    def get_queryset(self):
        return (
            Card.objects
            .select_related('expansion')
            .distinct()
        )


class CardDetailView(APIKeyMixin, generics.RetrieveAPIView):
    """
    카드 상세 + 가격 이력 + 관리자 설정 판매가.

    Query Params:
      price_limit  가격 이력 최대 개수 (기본 30)
    """
    serializer_class = CardDetailSerializer

    def get_queryset(self):
        # prices는 prefetch하지 않는다 — CardDetailSerializer가
        # price_limit만큼만 쿼리셋에서 직접 슬라이스(LIMIT)해서 가져온다.
        return Card.objects.select_related('expansion')

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['price_limit'] = int(self.request.query_params.get('price_limit', 30))
        return ctx


class LatestNaverPriceListView(APIKeyMixin, generics.ListAPIView):
    """
    최신 네이버 가격.

    Query Params:
      hours      조회 기간 (기본 24시간)
      expansion  확장팩 코드 필터
    """
    serializer_class = CardPriceSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['collected_at', 'price']
    ordering = ['-collected_at']

    def get_queryset(self):
        hours = int(self.request.query_params.get('hours', 24))
        since = timezone.now() - timedelta(hours=hours)
        qs = CardPrice.objects.filter(collected_at__gte=since).select_related('card', 'card__expansion')
        expansion_code = self.request.query_params.get('expansion')
        if expansion_code:
            qs = qs.filter(card__expansion__code=expansion_code)
        return qs


@api_view(['GET'])
@authentication_classes([APIKeyAuthentication])
@permission_classes([HasAPIKey])
def price_collection_summary(request):
    """
    수집 현황 요약.

    Query Params:
      hours  집계 기간 (기본 24시간)
    """
    hours = int(request.query_params.get('hours', 24))
    since = timezone.now() - timedelta(hours=hours)
    naver = CardPrice.objects.filter(collected_at__gte=since).aggregate(
        total=Count('id'),
        last_collected=Max('collected_at'),
    )
    return Response({'naver': naver})


@api_view(['GET'])
@authentication_classes([APIKeyAuthentication])
@permission_classes([HasAPIKey])
def card_by_product_code(request, shop_product_code):
    """상품코드로 포켓몬 카드 조회"""
    return _card_by_product_code_view(request, shop_product_code, Card)


class PokemonPriceSnapshotView(PriceSnapshotMixin):
    card_model = Card


class PokemonPriceHistoryView(PriceHistoryMixin):
    card_model = Card


# ════════════════════════════════════════════════════════════════
# 원피스 한글판
# ════════════════════════════════════════════════════════════════

class OnePieceExpansionListView(ExpansionListMixin):
    serializer_class = OnePieceExpansionListSerializer
    expansion_model = OnePieceExpansion


class OnePieceExpansionDetailView(ExpansionDetailMixin):
    serializer_class = OnePieceExpansionListSerializer
    expansion_model = OnePieceExpansion


class OnePieceCardListView(CardListMixin):
    serializer_class = OnePieceCardListSerializer
    card_model = OnePieceCard


class OnePieceCardSearchView(CardSearchMixin):
    serializer_class = OnePieceCardListSerializer
    card_model = OnePieceCard


@api_view(['GET'])
@authentication_classes([APIKeyAuthentication])
@permission_classes([HasAPIKey])
def onepiece_card_by_product_code(request, shop_product_code):
    """상품코드로 원피스 카드 조회"""
    return _card_by_product_code_view(request, shop_product_code, OnePieceCard)


class OnePiecePriceSnapshotView(PriceSnapshotMixin):
    card_model = OnePieceCard


class OnePiecePriceHistoryView(PriceHistoryMixin):
    card_model = OnePieceCard


# ════════════════════════════════════════════════════════════════
# 디지몬 한글판
# ════════════════════════════════════════════════════════════════

class DigimonExpansionListView(ExpansionListMixin):
    serializer_class = DigimonExpansionListSerializer
    expansion_model = DigimonExpansion


class DigimonExpansionDetailView(ExpansionDetailMixin):
    serializer_class = DigimonExpansionListSerializer
    expansion_model = DigimonExpansion


class DigimonCardListView(CardListMixin):
    serializer_class = DigimonCardListSerializer
    card_model = DigimonCard


class DigimonCardSearchView(CardSearchMixin):
    serializer_class = DigimonCardListSerializer
    card_model = DigimonCard


@api_view(['GET'])
@authentication_classes([APIKeyAuthentication])
@permission_classes([HasAPIKey])
def digimon_card_by_product_code(request, shop_product_code):
    """상품코드로 디지몬 카드 조회"""
    return _card_by_product_code_view(request, shop_product_code, DigimonCard)


class DigimonPriceSnapshotView(PriceSnapshotMixin):
    card_model = DigimonCard


class DigimonPriceHistoryView(PriceHistoryMixin):
    card_model = DigimonCard


# ════════════════════════════════════════════════════════════════
# 포켓몬 일본판
# ════════════════════════════════════════════════════════════════

class JapanExpansionListView(ExpansionListMixin):
    serializer_class = JapanExpansionListSerializer
    expansion_model = JapanExpansion


class JapanExpansionDetailView(ExpansionDetailMixin):
    serializer_class = JapanExpansionListSerializer
    expansion_model = JapanExpansion


class JapanCardListView(CardListMixin):
    serializer_class = JapanCardListSerializer
    card_model = JapanCard


class JapanCardSearchView(CardSearchMixin):
    serializer_class = JapanCardListSerializer
    card_model = JapanCard


class JapanPriceSnapshotView(PriceSnapshotMixin):
    card_model = JapanCard
    is_japan = True


class JapanPriceHistoryView(PriceHistoryMixin):
    card_model = JapanCard
    is_japan = True


@api_view(['GET'])
@authentication_classes([APIKeyAuthentication])
@permission_classes([HasAPIKey])
def japan_card_by_product_code(request, shop_product_code):
    """상품코드로 포켓몬 일본판 카드 조회"""
    return _card_by_product_code_view(request, shop_product_code, JapanCard)