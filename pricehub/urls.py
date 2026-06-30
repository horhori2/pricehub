"""
pricehub/urls.py
"""
from django.urls import path, include
from . import views as v
from pricehub import api_docs_views

app_name = 'pricehub'


def _card_urls(prefix, views, *, has_bulk=False, has_shop_stats=False,
               has_search=False, has_reset=False, has_favorites=False):
    name = prefix.replace('/', '-')

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
            path('bulk-price/',                     views['bulk_price'],              name=f'{name}-bulk-price'),
            path('bulk-price/verify/',              views['bulk_verify'],             name=f'{name}-bulk-verify'),
            path('bulk-price/verify/candidates/',   views['bulk_verify_candidates'],  name=f'{name}-bulk-verify-candidates'),
            path('bulk-price/stats/',               views['bulk_shop_stats'],         name=f'{name}-bulk-shop-stats'),
            path('bulk-price/run/',                 views['bulk_run'],                name=f'{name}-bulk-run'),
            path('bulk-price/drop/',                views['bulk_drop'],               name=f'{name}-bulk-drop'),
            path('bulk-price/unpriced/',            views['bulk_unpriced'],           name=f'{name}-bulk-unpriced'),
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
    'card_list':         v.pokemon_kr_card_list,
    'card_detail':       v.pokemon_kr_card_detail,
    'set_price':         v.pokemon_kr_set_price,
    'search':            v.pokemon_kr_card_search,
    'reset_prices':      v.pokemon_kr_reset_prices,
    'reset_all':         v.pokemon_kr_reset_all_prices,
    'bulk_price':        v.pokemon_kr_bulk_price,
    'bulk_verify':       v.pokemon_kr_bulk_verify,
    'bulk_verify_candidates': v.pokemon_kr_bulk_verify_candidates,
    'bulk_run':          v.pokemon_kr_bulk_run,
    'bulk_drop':         v.pokemon_kr_bulk_drop,
    'bulk_unpriced':     v.pokemon_kr_bulk_unpriced,
    'shop_stats':        v.pokemon_kr_shop_stats,
    'shop_stats_detail': v.pokemon_kr_shop_stats_detail,
    'toggle_favorite':   v.pokemon_kr_toggle_favorite,
    'bulk_approve':      v.pokemon_kr_bulk_approve,
    'bulk_edit':         v.pokemon_kr_bulk_edit,
    'bulk_shop_stats':   v.pokemon_kr_bulk_shop_stats,
    'bulk_inline_cards': v.pokemon_kr_bulk_inline_cards,
}

_pokemon_jp_views = {
    'expansion_list': v.pokemon_jp_expansion_list,
    'card_list':      v.pokemon_jp_card_list,
    'card_detail':    v.pokemon_jp_card_detail,
    'set_price':      v.pokemon_jp_set_price,
}

_onepiece_kr_views = {
    'expansion_list':  v.onepiece_kr_expansion_list,
    'card_list':       v.onepiece_kr_card_list,
    'card_detail':     v.onepiece_kr_card_detail,
    'set_price':       v.onepiece_kr_set_price,
    'search':          v.onepiece_kr_card_search,
    'reset_prices':    v.onepiece_kr_reset_prices,
    'reset_all':       v.onepiece_kr_reset_all_prices,
    'bulk_price':      v.onepiece_kr_bulk_price,
    'bulk_verify':     v.onepiece_kr_bulk_verify,
    'bulk_verify_candidates': v.onepiece_kr_bulk_verify_candidates,
    'bulk_run':        v.onepiece_kr_bulk_run,
    'bulk_drop':       v.onepiece_kr_bulk_drop,
    'bulk_unpriced':   v.onepiece_kr_bulk_unpriced,
    'toggle_favorite':  v.onepiece_kr_toggle_favorite,
    'bulk_approve':     v.onepiece_kr_bulk_approve,
    'bulk_edit':        v.onepiece_kr_bulk_edit,
    'bulk_shop_stats':  v.onepiece_kr_bulk_shop_stats,
    'bulk_inline_cards': v.onepiece_kr_bulk_inline_cards,
}

_digimon_kr_views = {
    'expansion_list':    v.digimon_kr_expansion_list,
    'card_list':         v.digimon_kr_card_list,
    'card_detail':       v.digimon_kr_card_detail,
    'set_price':         v.digimon_kr_set_price,
    'search':            v.digimon_kr_card_search,
    'reset_prices':      v.digimon_kr_reset_prices,
    'reset_all':         v.digimon_kr_reset_all_prices,
    'bulk_price':        v.digimon_kr_bulk_price,
    'bulk_verify':       v.digimon_kr_bulk_verify,
    'bulk_verify_candidates': v.digimon_kr_bulk_verify_candidates,
    'bulk_run':          v.digimon_kr_bulk_run,
    'bulk_drop':         v.digimon_kr_bulk_drop,
    'bulk_unpriced':     v.digimon_kr_bulk_unpriced,
    'toggle_favorite':   v.digimon_kr_toggle_favorite,
    'bulk_approve':      v.digimon_kr_bulk_approve,
    'bulk_edit':         v.digimon_kr_bulk_edit,
    'bulk_shop_stats':   v.digimon_kr_bulk_shop_stats,
    'bulk_inline_cards': v.digimon_kr_bulk_inline_cards,
}


urlpatterns = [
    path('login/',  v.dashboard_login,  name='dashboard-login'),
    path('logout/', v.dashboard_logout, name='dashboard-logout'),
    path('',        v.home,             name='dashboard-home'),

    *_card_urls('pokemon/kr', _pokemon_kr_views,
                has_search=True, has_reset=True, has_bulk=True,
                has_shop_stats=True, has_favorites=True),

    *_card_urls('pokemon/jp', _pokemon_jp_views),

    *_card_urls('onepiece/kr', _onepiece_kr_views,
                has_search=True, has_reset=True, has_bulk=True,
                has_favorites=True),

    *_card_urls('digimon/kr', _digimon_kr_views,
                has_search=True, has_reset=True, has_bulk=True,
                has_favorites=True),

    path('api-docs/', api_docs_views.api_docs, name='api-docs'),
]