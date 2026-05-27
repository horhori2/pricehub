"""
pricehub/models.py 에 추가할 APIKey 모델
"""
import secrets
from django.db import models


class APIKey(models.Model):
    """
    외부 클라이언트용 API Key.

    발급:
        python manage.py shell
        >>> from pricehub.models import APIKey
        >>> APIKey.objects.create_key(name='카드관리프로그램')
    """
    name = models.CharField(max_length=100, verbose_name='클라이언트명', help_text='예: 카드관리프로그램')
    key = models.CharField(max_length=64, unique=True, verbose_name='API Key')
    is_active = models.BooleanField(default=True, verbose_name='활성 여부')
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True, verbose_name='마지막 사용')

    objects = models.Manager()

    class Meta:
        db_table = 'api_key'
        verbose_name = 'API Key'
        verbose_name_plural = 'API Key 목록'

    def __str__(self):
        return f"{self.name} ({'활성' if self.is_active else '비활성'})"

    @classmethod
    def create_key(cls, name: str) -> tuple:
        """
        새 API Key 발급.
        Returns: (APIKey instance, raw_key)
        raw_key는 이 시점에만 확인 가능 — DB에는 저장되지 않음.
        """
        raw_key = secrets.token_urlsafe(32)
        instance = cls.objects.create(name=name, key=raw_key)
        return instance, raw_key
