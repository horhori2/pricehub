from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('pricehub.urls', namespace='pricehub')),  # 기존 템플릿 뷰

    # ← 새로 추가
    path('api/pokemon/kr/', include('pricehub.api_urls', namespace='pokemon_kr')),
    path('api/onepiece/kr/', include('pricehub.onepiece_api_urls')), 
    path('dashboard/', include('pricehub.dashboard_urls')),
]