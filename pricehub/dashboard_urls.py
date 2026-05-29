"""
pricehub/dashboard_urls.py
"""
from django.urls import path
from . import dashboard_views

urlpatterns = [
     # 로그인/로그아웃
     path('login/',  dashboard_views.dashboard_login,  name='dashboard-login'),
     path('logout/', dashboard_views.dashboard_logout, name='dashboard-logout'),

     # 홈 (카테고리 선택)
     path('', dashboard_views.home, name='dashboard-home'),

     # ── 포켓몬 한글판 ──────────────────────────────────────
     path('pokemon/kr/expansions/',
          dashboard_views.pokemon_kr_expansion_list, name='pokemon-kr-expansions'),
     path('pokemon/kr/expansions/<str:code>/cards/',
          dashboard_views.pokemon_kr_card_list, name='pokemon-kr-card-list'),
     path('pokemon/kr/cards/<int:pk>/',
          dashboard_views.pokemon_kr_card_detail, name='pokemon-kr-card-detail'),
     path('pokemon/kr/cards/<int:pk>/set-price/',
          dashboard_views.pokemon_kr_set_price, name='pokemon-kr-set-price'),
     path('pokemon/kr/cards/search/', dashboard_views.pokemon_kr_card_search, name='pokemon-kr-card-search'),

     # ── 포켓몬 일본판 ──────────────────────────────────────
     path('pokemon/jp/expansions/',
          dashboard_views.pokemon_jp_expansion_list, name='pokemon-jp-expansions'),
     path('pokemon/jp/expansions/<str:code>/cards/',
          dashboard_views.pokemon_jp_card_list, name='pokemon-jp-card-list'),
     path('pokemon/jp/cards/<int:pk>/',
          dashboard_views.pokemon_jp_card_detail, name='pokemon-jp-card-detail'),
     path('pokemon/jp/cards/<int:pk>/set-price/',
          dashboard_views.pokemon_jp_set_price, name='pokemon-jp-set-price'),

     # ── 원피스 한글판 ──────────────────────────────────────
     path('onepiece/kr/expansions/',
          dashboard_views.onepiece_kr_expansion_list, name='onepiece-kr-expansions'),
     path('onepiece/kr/expansions/<str:code>/cards/',
          dashboard_views.onepiece_kr_card_list, name='onepiece-kr-card-list'),
     path('onepiece/kr/cards/<int:pk>/',
          dashboard_views.onepiece_kr_card_detail, name='onepiece-kr-card-detail'),
     path('onepiece/kr/cards/<int:pk>/set-price/',
          dashboard_views.onepiece_kr_set_price, name='onepiece-kr-set-price'),
     path('onepiece/kr/cards/search/', dashboard_views.onepiece_kr_card_search, name='onepiece-kr-card-search'),

     # ── 일괄 가격 설정 ──────────────────────────────────────
     path('pokemon/kr/bulk-price/',         dashboard_views.pokemon_kr_bulk_price,   name='pokemon-kr-bulk-price'),
     path('pokemon/kr/bulk-price/run/',     dashboard_views.pokemon_kr_bulk_run,     name='pokemon-kr-bulk-run'),
     path('pokemon/kr/bulk-price/issues/',  dashboard_views.pokemon_kr_bulk_issues,  name='pokemon-kr-bulk-issues'),
     path('pokemon/kr/shop-stats/',         dashboard_views.pokemon_kr_shop_stats,        name='pokemon-kr-shop-stats'),
     path('pokemon/kr/shop-stats/<str:code>/', dashboard_views.pokemon_kr_shop_stats_detail, name='pokemon-kr-shop-stats-detail'),

     path('onepiece/kr/bulk-price/',         dashboard_views.onepiece_kr_bulk_price,   name='onepiece-kr-bulk-price'),
     path('onepiece/kr/bulk-price/run/',     dashboard_views.onepiece_kr_bulk_run,     name='onepiece-kr-bulk-run'),
     path('onepiece/kr/bulk-price/issues/',  dashboard_views.onepiece_kr_bulk_issues,  name='onepiece-kr-bulk-issues'),
]
