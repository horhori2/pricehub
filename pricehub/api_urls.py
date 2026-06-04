"""
pricehub/api_urls.py — REST API + API 문서 (개발자용)
"""
from django.urls import path, include
from pricehub import api_docs_views
from . import api_views


def _tcg_api_urls(views):
    """
    확장팩 목록/상세, 카드 목록/검색/상세, 상품코드 조회 공통 패턴 생성.

    views 딕셔너리 keys:
        expansion_list, expansion_detail, expansion_card_list,
        card_search, card_detail (optional),
        card_by_product_code,
        price_latest (optional), price_summary (optional)
    """
    patterns = [
        path('expansions/',
             views['expansion_list'].as_view(),      name='expansion-list'),
        path('expansions/<str:code>/',
             views['expansion_detail'].as_view(),    name='expansion-detail'),
        path('expansions/<str:code>/cards/',
             views['expansion_card_list'].as_view(), name='expansion-card-list'),
        path('cards/search/',
             views['card_search'].as_view(),         name='card-search'),
        path('cards/by-product-code/<str:shop_product_code>/',
             views['card_by_product_code'],          name='card-by-product-code'),
    ]
    if 'card_detail' in views:
        patterns.append(
            path('cards/<int:pk>/', views['card_detail'].as_view(), name='card-detail')
        )
    if 'price_latest' in views:
        patterns.append(
            path('prices/latest/', views['price_latest'].as_view(), name='price-naver-latest')
        )
    if 'price_summary' in views:
        patterns.append(
            path('prices/summary/', views['price_summary'], name='price-summary')
        )
    return patterns


_pokemon_kr_views = {
    'expansion_list':       api_views.ExpansionListView,
    'expansion_detail':     api_views.ExpansionDetailView,
    'expansion_card_list':  api_views.ExpansionCardListView,
    'card_search':          api_views.CardSearchView,
    'card_detail':          api_views.CardDetailView,
    'card_by_product_code': api_views.card_by_product_code,
    'price_latest':         api_views.LatestNaverPriceListView,
    'price_summary':        api_views.price_collection_summary,
}

_onepiece_kr_views = {
    'expansion_list':       api_views.OnePieceExpansionListView,
    'expansion_detail':     api_views.OnePieceExpansionDetailView,
    'expansion_card_list':  api_views.OnePieceCardListView,
    'card_search':          api_views.OnePieceCardSearchView,
    'card_by_product_code': api_views.onepiece_card_by_product_code,
}

# 원피스 한글판 (별도 include용)
onepiece_kr_urlpatterns = (
    _tcg_api_urls(_onepiece_kr_views),
    'onepiece_kr',
)

# 포켓몬 한글판 (기본 include 대상)
app_name = 'pokemon_kr'
urlpatterns = _tcg_api_urls(_pokemon_kr_views)