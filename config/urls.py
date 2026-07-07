from django.contrib import admin
from django.urls import path, include
from pricehub import api_urls
from pricehub import api_docs_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # 대시보드 — 가격 관리자용 (루트에서 바로 접근)
    path('', include('pricehub.urls', namespace='pricehub')),

    # 매입리스트                                
    path('api/purchase-lists/', include(api_urls.purchase_list_urlpatterns)),

    # REST API — 개발자용
    path('api/pokemon/kr/',  include('pricehub.api_urls',               namespace='pokemon_kr')),
    path('api/onepiece/kr/', include(api_urls.onepiece_kr_urlpatterns)),
    path('api/digimon/kr/',  include(api_urls.digimon_kr_urlpatterns)),

    # API 문서 — 개발자용
    path('api-docs/', api_docs_views.api_docs, name='api-docs'),


]