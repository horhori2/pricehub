from django.urls import path
from . import views

app_name = 'pricehub'

urlpatterns = [
    # 포켓몬 한글판
    path('', views.expansion_list, name='expansion_list'),
    path('search/', views.card_search, name='card_search'),
    path('expansion/<str:expansion_code>/', views.card_list, name='card_list'),
    path('card/<int:card_id>/', views.card_detail, name='card_detail'),
    
    # 원피스
    path('onepiece/', views.onepiece_expansion_list, name='onepiece_expansion_list'),
    path('onepiece/search/', views.onepiece_card_search, name='onepiece_card_search'),
    path('onepiece/expansion/<str:expansion_code>/', views.onepiece_card_list, name='onepiece_card_list'),
    path('onepiece/card/<int:card_id>/', views.onepiece_card_detail, name='onepiece_card_detail'),
    
    # 포켓몬 일본판 (추가)
    path('japan/', views.japan_expansion_list, name='japan_expansion_list'),
    path('japan/search/', views.japan_card_search, name='japan_card_search'),
    path('japan/expansion/<str:expansion_code>/', views.japan_card_list, name='japan_card_list'),
    path('japan/card/<int:card_id>/', views.japan_card_detail, name='japan_card_detail'),
]