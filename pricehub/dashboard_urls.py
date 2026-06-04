"""
pricehub/dashboard_urls.py
"""
from django.urls import path, include
from . import views as v

# ── 헬퍼: 카테고리별 URL 패턴 생성 ─────────────────────────────────
def _card_urls(prefix, views, *, has_bulk=False, has_shop_stats=False, has_search=False, has_reset=False):
    """
    공통 카드 URL 패턴을 생성합니다.

    Args:
        prefix:         URL/name 접두어  ex) 'pokemon/kr', 'onepiece/kr'
        views:          해당 prefix에 대응하는 view 함수 딕셔너리
                        keys: expansion_list, card_list, card_detail,
                              set_price, [search], [reset_prices],
                              [reset_all], [bulk_price], [bulk_run],
                              [bulk_issues], [shop_stats], [shop_stats_detail]
        has_bulk:       bulk-price 3종 세트 포함 여부
        has_shop_stats: shop-stats 2종 포함 여부
        has_search:     카드 검색 엔드포인트 포함 여부
        has_reset:      reset-prices / reset-all-prices 포함 여부
    """
    name = prefix.replace('/', '-')   # 'pokemon/kr' → 'pokemon-kr'

    patterns = [
        path('expansions/',
             views['expansion_list'],
             name=f'{name}-expansions'),
        path('expansions/<str:code>/cards/',
             views['card_list'],
             name=f'{name}-card-list'),
        path('cards/<int:pk>/',
             views['card_detail'],
             name=f'{name}-card-detail'),
        path('cards/<int:pk>/set-price/',
             views['set_price'],
             name=f'{name}-set-price'),
    ]

    if has_search:
        patterns.append(
            path('cards/search/', views['search'], name=f'{name}-card-search')
        )
    if has_reset:
        patterns += [
            path('expansions/<str:expansion_code>/reset-prices/',
                 views['reset_prices'],
                 name=f'{name}-reset-prices'),
            path('reset-all-prices/',
                 views['reset_all'],
                 name=f'{name}-reset-all-prices'),
        ]
    if has_bulk:
        patterns += [
            path('bulk-price/',        views['bulk_price'],  name=f'{name}-bulk-price'),
            path('bulk-price/run/',    views['bulk_run'],    name=f'{name}-bulk-run'),
            path('bulk-price/issues/', views['bulk_issues'], name=f'{name}-bulk-issues'),
        ]
    if has_shop_stats:
        patterns += [
            path('shop-stats/',             views['shop_stats'],        name=f'{name}-shop-stats'),
            path('shop-stats/<str:code>/',  views['shop_stats_detail'], name=f'{name}-shop-stats-detail'),
        ]

    return [path(f'{prefix}/', include(patterns))]


# ── 카테고리별 뷰 매핑 ────────────────────────────────────────────

_pokemon_kr_views = {
    'expansion_list':   v.pokemon_kr_expansion_list,
    'card_list':        v.pokemon_kr_card_list,
    'card_detail':      v.pokemon_kr_card_detail,
    'set_price':        v.pokemon_kr_set_price,
    'search':           v.pokemon_kr_card_search,
    'reset_prices':     v.pokemon_kr_reset_prices,
    'reset_all':        v.pokemon_kr_reset_all_prices,
    'bulk_price':       v.pokemon_kr_bulk_price,
    'bulk_run':         v.pokemon_kr_bulk_run,
    'bulk_issues':      v.pokemon_kr_bulk_issues,
    'shop_stats':       v.pokemon_kr_shop_stats,
    'shop_stats_detail': v.pokemon_kr_shop_stats_detail,
}

_pokemon_jp_views = {
    'expansion_list':   v.pokemon_jp_expansion_list,
    'card_list':        v.pokemon_jp_card_list,
    'card_detail':      v.pokemon_jp_card_detail,
    'set_price':        v.pokemon_jp_set_price,
}

_onepiece_kr_views = {
    'expansion_list':   v.onepiece_kr_expansion_list,
    'card_list':        v.onepiece_kr_card_list,
    'card_detail':      v.onepiece_kr_card_detail,
    'set_price':        v.onepiece_kr_set_price,
    'search':           v.onepiece_kr_card_search,
    'reset_prices':     v.onepiece_kr_reset_prices,
    'reset_all':        v.onepiece_kr_reset_all_prices,
    'bulk_price':       v.onepiece_kr_bulk_price,
    'bulk_run':         v.onepiece_kr_bulk_run,
    'bulk_issues':      v.onepiece_kr_bulk_issues,
}


# ── URL 패턴 조립 ─────────────────────────────────────────────────

urlpatterns = [
    # 로그인/로그아웃
    path('login/',  v.dashboard_login,  name='dashboard-login'),
    path('logout/', v.dashboard_logout, name='dashboard-logout'),

    # 홈
    path('', v.home, name='dashboard-home'),

    # 포켓몬 한글판 
    *_card_urls('pokemon/kr', _pokemon_kr_views,
                has_search=True, has_reset=True, has_bulk=True, has_shop_stats=True),

    # 포켓몬 일본판
    *_card_urls('pokemon/jp', _pokemon_jp_views),

    # 원피스 한글판
    *_card_urls('onepiece/kr', _onepiece_kr_views,
                has_search=True, has_reset=True, has_bulk=True),
]