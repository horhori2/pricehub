"""
pricehub/urls.py
"""
from django.urls import path, include
from . import views as v
from . import purchase_views as pv
from pricehub import api_docs_views

app_name = 'pricehub'


def _card_urls(prefix, views, *, has_bulk=False, has_shop_stats=False,
               has_search=False, has_reset=False, has_favorites=False,
               has_price_history=False):
    name = prefix.replace('/', '-')

    patterns = [
        path('expansions/',
             views['expansion_list'],
             name=f'{name}-expansions'),
        path('expansions/stats/',
             views['expansion_stats'],
             name=f'{name}-expansion-stats'),
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

    if has_price_history:
        patterns.append(
            path('cards/<int:pk>/price-history/',
                 views['price_history'],
                 name=f'{name}-price-history')
        )

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
            path('bulk-price/',                     views['bulk_price'],              name=f'{name}-bulk-price'),
            path('bulk-price/verify/',              views['bulk_verify'],             name=f'{name}-bulk-verify'),
            path('bulk-price/verify/candidates/',   views['bulk_verify_candidates'],  name=f'{name}-bulk-verify-candidates'),
            path('bulk-price/stats/',               views['bulk_shop_stats'],         name=f'{name}-bulk-shop-stats'),
            path('bulk-price/run/',                 views['bulk_run'],                name=f'{name}-bulk-run'),
            path('bulk-price/drop/',                views['bulk_drop'],               name=f'{name}-bulk-drop'),
            path('bulk-price/rise/',                views['bulk_rise'],               name=f'{name}-bulk-rise'),
            path('bulk-price/unpriced/',            views['bulk_unpriced'],           name=f'{name}-bulk-unpriced'),
            path('bulk-price/underpriced/',         views['bulk_underpriced'],        name=f'{name}-bulk-underpriced'),
            path('bulk-price/approve/',             views['bulk_approve'],            name=f'{name}-bulk-approve'),
            path('bulk-price/edit/',                views['bulk_edit'],               name=f'{name}-bulk-edit'),
            path('bulk-price/inline-cards/',        views['bulk_inline_cards'],       name=f'{name}-bulk-inline-cards'),
        ]
    if has_shop_stats:
        patterns += [
            path('shop-stats/',            views['shop_stats'],        name=f'{name}-shop-stats'),
            path('shop-stats/<str:code>/', views['shop_stats_detail'], name=f'{name}-shop-stats-detail'),
        ]
    if has_favorites:
        patterns += [
            path('cards/<int:card_id>/favorite/',
                 views['toggle_favorite'],      name=f'{name}-toggle-favorite'),
        ]

    return [path(f'{prefix}/', include(patterns))]

_pokemon_kr_views = {
    'expansion_list':    v.pokemon_kr_expansion_list,
    'expansion_stats':   v.pokemon_kr_expansion_stats,
    'card_list':         v.pokemon_kr_card_list,
    'set_price':         v.pokemon_kr_set_price,
    'search':            v.pokemon_kr_card_search,
    'reset_prices':      v.pokemon_kr_reset_prices,
    'reset_all':         v.pokemon_kr_reset_all_prices,
    'shop_stats':        v.pokemon_kr_shop_stats,
    'shop_stats_detail': v.pokemon_kr_shop_stats_detail,
    'toggle_favorite':   v.pokemon_kr_toggle_favorite,
    'price_history':     v.pokemon_kr_price_history,
    **v.game_views('pokemon_kr'),  # card_detail, bulk_* 12종
}

_pokemon_jp_views = {
    'expansion_list':  v.pokemon_jp_expansion_list,
    'expansion_stats': v.pokemon_jp_expansion_stats,
    'card_list':      v.pokemon_jp_card_list,
    'card_detail':    v.pokemon_jp_card_detail,
    'set_price':      v.pokemon_jp_set_price,
}

_onepiece_kr_views = {
    'expansion_list':  v.onepiece_kr_expansion_list,
    'expansion_stats': v.onepiece_kr_expansion_stats,
    'card_list':       v.onepiece_kr_card_list,
    'set_price':       v.onepiece_kr_set_price,
    'search':          v.onepiece_kr_card_search,
    'reset_prices':    v.onepiece_kr_reset_prices,
    'reset_all':       v.onepiece_kr_reset_all_prices,
    'toggle_favorite': v.onepiece_kr_toggle_favorite,
    'price_history':   v.onepiece_kr_price_history,
    **v.game_views('onepiece_kr'),  # card_detail, bulk_* 12종
}

_digimon_kr_views = {
    'expansion_list':  v.digimon_kr_expansion_list,
    'expansion_stats': v.digimon_kr_expansion_stats,
    'card_list':       v.digimon_kr_card_list,
    'set_price':       v.digimon_kr_set_price,
    'search':          v.digimon_kr_card_search,
    'reset_prices':    v.digimon_kr_reset_prices,
    'reset_all':       v.digimon_kr_reset_all_prices,
    'toggle_favorite': v.digimon_kr_toggle_favorite,
    'price_history':   v.digimon_kr_price_history,
    **v.game_views('digimon_kr'),  # card_detail, bulk_* 12종
}


urlpatterns = [
    path('login/',  v.dashboard_login,  name='dashboard-login'),
    path('logout/', v.dashboard_logout, name='dashboard-logout'),
    path('',        v.home,             name='dashboard-home'),

    *_card_urls('pokemon/kr', _pokemon_kr_views,
                has_search=True, has_reset=True, has_bulk=True,
                has_shop_stats=True, has_favorites=True, has_price_history=True),

    *_card_urls('pokemon/jp', _pokemon_jp_views),

    *_card_urls('onepiece/kr', _onepiece_kr_views,
                has_search=True, has_reset=True, has_bulk=True,
                has_favorites=True, has_price_history=True),

    *_card_urls('digimon/kr', _digimon_kr_views,
                has_search=True, has_reset=True, has_bulk=True,
                has_favorites=True, has_price_history=True),

    path('api-docs/', api_docs_views.api_docs, name='api-docs'),

    # ── 매입리스트 관리 ──
    path('purchase-lists/',
         pv.purchase_list_index, name='purchase-list-index'),
    path('purchase-lists/<str:game_type>/create/',
         pv.purchase_list_create, name='purchase-list-create'),
    path('purchase-lists/detail/<int:list_id>/',
         pv.purchase_list_detail, name='purchase-list-detail'),
    path('purchase-lists/detail/<int:list_id>/search-cards/',
         pv.purchase_list_search_cards, name='purchase-list-search-cards'),
    path('purchase-lists/detail/<int:list_id>/add-card/',
         pv.purchase_list_add_card, name='purchase-list-add-card'),
    path('purchase-lists/detail/<int:list_id>/toggle-active/',
         pv.purchase_list_toggle_active, name='purchase-list-toggle-active'),
    path('purchase-lists/detail/<int:list_id>/delete/',
         pv.purchase_list_delete, name='purchase-list-delete'),
    path('purchase-lists/detail/<int:list_id>/copy/',
         pv.purchase_list_copy, name='purchase-list-copy'),
    path('purchase-lists/items/<int:item_id>/set-price/',
         pv.purchase_list_set_price, name='purchase-list-set-price'),
    path('purchase-lists/items/<int:item_id>/remove/',
         pv.purchase_list_remove_item, name='purchase-list-remove-item'),

    # ── 레어도별 매입 고정가 관리 ──
    path('purchase-lists/rarity-prices/<str:game_type>/',
         pv.rarity_price_settings, name='rarity-price-settings'),
    path('purchase-lists/rarity-prices/<str:game_type>/save/',
         pv.rarity_price_save, name='rarity-price-save'),
]