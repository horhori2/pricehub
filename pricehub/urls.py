# pricehub/urls.py
from django.urls import path
from . import views

app_name = 'pricehub'

urlpatterns = [
    # 메인 페이지 (확장팩 목록)
    path('', views.expansion_list, name='expansion_list'),
    
    # 확장팩 내 카드 목록
    path('expansion/<str:code>/', views.card_list, name='card_list'),
    
    # 카드 상세 페이지
    path('card/<int:card_id>/', views.card_detail, name='card_detail'),
]