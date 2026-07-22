"""
pricehub/templatetags/cache_bust.py

정적 파일(dashboard.js/css 등) 수정 후 배포해도 브라우저가 예전 캐시를
계속 쓰는 문제 방지용. 소스 파일의 수정 시각(mtime)을 쿼리스트링으로
붙여서, 파일이 바뀌면 URL도 바뀌어 브라우저가 새로 받아가게 한다.
`git pull`로 파일이 갱신되면 mtime도 함께 바뀌므로 배포 때마다 자동 적용됨.
"""
import os

from django import template
from django.conf import settings
from django.templatetags.static import static as static_url

register = template.Library()


@register.simple_tag
def static_v(path):
    url = static_url(path)
    full_path = os.path.join(settings.BASE_DIR, 'static', path)
    try:
        version = int(os.path.getmtime(full_path))
    except OSError:
        return url
    separator = '&' if '?' in url else '?'
    return f'{url}{separator}v={version}'
