# pricehub/throttling.py
from rest_framework.throttling import SimpleRateThrottle


class APIKeyRateThrottle(SimpleRateThrottle):
    """
    API Key(APIKeyAuthentication)당 요청 빈도 제한.

    request.user는 API Key 인증에서 항상 비어있으므로(익명) 기본
    UserRateThrottle/AnonRateThrottle로는 모든 클라이언트가 같은 버킷을
    공유하게 된다. 대신 인증된 APIKey 인스턴스(request.auth)를 기준으로
    나눠서 클라이언트별로 독립적인 한도를 적용한다.
    """
    scope = 'api_key'

    def get_cache_key(self, request, view):
        api_key = getattr(request, 'auth', None)
        if not api_key:
            # 인증 실패 요청은 HasAPIKey permission에서 별도로 막히므로 여기선 스로틀 대상 아님
            return None
        return self.cache_format % {
            'scope': self.scope,
            'ident': api_key.pk,
        }
