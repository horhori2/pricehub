# pricehub/api_urls.py
from django.urls import path
from . import api_views

app_name = 'pokemon_kr'

urlpatterns = [
    path('expansions/', api_views.ExpansionListView.as_view(), name='expansion-list'),
    path('expansions/<str:code>/', api_views.ExpansionDetailView.as_view(), name='expansion-detail'),
    path('expansions/<str:code>/cards/', api_views.ExpansionCardListView.as_view(), name='expansion-card-list'),
    path('cards/search/', api_views.CardSearchView.as_view(), name='card-search'),
    path('cards/<int:pk>/', api_views.CardDetailView.as_view(), name='card-detail'),
    path('prices/latest/', api_views.LatestNaverPriceListView.as_view(), name='price-naver-latest'),
    path('prices/summary/', api_views.price_collection_summary, name='price-summary'),
]