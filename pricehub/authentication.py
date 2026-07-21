"""
pricehub/authentication.py

DRF 커스텀 인증 클래스.
요청 헤더:
    Authorization: Api-Key <key>
"""
from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import APIKey


class APIKeyAuthentication(BaseAuthentication):
    """
    Authorization: Api-Key <key> 헤더로 인증.
    유효한 키면 (None, key_instance) 반환 — 유저 없이 인증만 통과.
    """
    keyword = 'Api-Key'

    def authenticate(self, request):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith(self.keyword + ' '):
            return None  # 이 인증 방식 아님 → 다음 인증 시도

        raw_key = auth_header[len(self.keyword) + 1:].strip()
        return self._validate_key(raw_key)

    def _validate_key(self, raw_key: str):
        try:
            api_key = APIKey.objects.get(key=APIKey.hash_key(raw_key), is_active=True)
        except APIKey.DoesNotExist:
            raise AuthenticationFailed('유효하지 않은 API Key입니다.')

        # 마지막 사용 시각 업데이트
        APIKey.objects.filter(pk=api_key.pk).update(last_used_at=timezone.now())

        return (None, api_key)  # (user, auth)

    def authenticate_header(self, request):
        return self.keyword
