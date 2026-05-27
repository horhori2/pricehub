"""
pricehub/permissions.py

API Key 인증된 요청만 허용하는 Permission 클래스.
"""
from rest_framework.permissions import BasePermission
from .models import APIKey


class HasAPIKey(BasePermission):
    """
    APIKeyAuthentication 으로 인증된 요청만 허용.
    request.auth 가 APIKey 인스턴스인지 확인.
    """
    message = 'API Key가 필요합니다. Authorization: Api-Key <key> 헤더를 추가하세요.'

    def has_permission(self, request, view):
        return isinstance(request.auth, APIKey)
