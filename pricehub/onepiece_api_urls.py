from django.urls import path
from . import api_views

app_name = 'onepiece_kr'

urlpatterns = [
    path('expansions/', api_views.OnePieceExpansionListView.as_view()),
    path('expansions/<str:code>/', api_views.OnePieceExpansionDetailView.as_view()),
    path('expansions/<str:code>/cards/', api_views.OnePieceCardListView.as_view()),
    path('cards/search/', api_views.OnePieceCardSearchView.as_view()),
    path('cards/by-product-code/<str:shop_product_code>/', api_views.onepiece_card_by_product_code),
]