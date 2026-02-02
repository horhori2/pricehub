from django.urls import path
from . import views

app_name = 'pricehub'

urlpatterns = [
    # ==================== 포켓몬 카드 ====================
    # 메인 페이지 (확장팩 목록)
    path('', views.expansion_list, name='expansion_list'),
    
    # 검색 결과
    path('search/', views.card_search, name='card_search'),
    
    # 확장팩 내 카드 목록
    path('expansion/<str:code>/', views.card_list, name='card_list'),
    
    # 카드 상세 페이지
    path('card/<int:card_id>/', views.card_detail, name='card_detail'),
    
    # ==================== 원피스 카드 ====================
    # 원피스 메인 페이지
    path('onepiece/', views.onepiece_expansion_list, name='onepiece_expansion_list'),
    
    # 원피스 검색
    path('onepiece/search/', views.onepiece_card_search, name='onepiece_card_search'),
    
    # 원피스 확장팩 내 카드 목록
    path('onepiece/expansion/<str:code>/', views.onepiece_card_list, name='onepiece_card_list'),
    
    # 원피스 카드 상세 페이지
    path('onepiece/card/<int:card_id>/', views.onepiece_card_detail, name='onepiece_card_detail'),
]