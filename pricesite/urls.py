"""
pricesite/urls.py
"""
from django.urls import path

from . import views

app_name = 'pricesite'

urlpatterns = [
    path('', views.home, name='home'),
    path('<str:game_key>/expansions/', views.expansion_list, name='expansion-list'),
    path('<str:game_key>/expansions/<str:code>/cards/', views.card_list, name='card-list'),
    path('<str:game_key>/cards/<int:pk>/', views.card_detail, name='card-detail'),
    path('<str:game_key>/cards/<int:pk>/price-history/', views.price_history, name='price-history'),
]
