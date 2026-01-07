# pricehub/models.py
from django.db import models
from django.core.validators import MinValueValidator


class Expansion(models.Model):
    """확장팩 모델"""
    code = models.CharField(
        max_length=20, 
        unique=True, 
        verbose_name='확장팩번호',
        help_text='예: m2'
    )
    name = models.CharField(
        max_length=100, 
        verbose_name='시리즈명',
        help_text='예: 인페르노X'
    )
    image_url = models.URLField(
        max_length=500, 
        verbose_name='확장팩 이미지'
    )
    release_date = models.DateField(
        null=True, 
        blank=True, 
        verbose_name='출시일'
    )
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name='생성일시'
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name='수정일시'
    )

    class Meta:
        db_table = 'expansion'
        verbose_name = '확장팩'
        verbose_name_plural = '확장팩 목록'
        ordering = ['-release_date', '-created_at']

    def __str__(self):
        return f"{self.code} - {self.name}"


class Card(models.Model):
    """싱글카드 모델"""
    
    RARITY_CHOICES = [
        ('UR', 'UR'),
        ('SSR', 'SSR'),
        ('SR', 'SR'),
        ('RR', 'RR'),
        ('RRR', 'RRR'),
        ('CHR', 'CHR'),
        ('CSR', 'CSR'),
        ('BWR', 'BWR'),
        ('AR', 'AR'),
        ('SAR', 'SAR'),
        ('HR', 'HR'),
        ('R', 'R'),
        ('U', 'U'),
        ('C', 'C'),
        ('몬스터볼', '몬스터볼'),
        ('마스터볼', '마스터볼'),
        ('이로치', '이로치'),
        ('미러', '미러'),
    ]
    
    expansion = models.ForeignKey(
        Expansion,
        on_delete=models.CASCADE,
        related_name='cards',
        verbose_name='확장팩'
    )
    card_number = models.CharField(
        max_length=10, 
        verbose_name='카드번호',
        help_text='예: 001'
    )
    name = models.CharField(
        max_length=100, 
        verbose_name='카드명',
        help_text='예: 뚜벅쵸'
    )
    rarity = models.CharField(
        max_length=20, 
        choices=RARITY_CHOICES, 
        verbose_name='레어도'
    )
    shop_product_code = models.CharField(
        max_length=50, 
        unique=True, 
        verbose_name='네이버상품코드',
        help_text='예: PKM-m2-001-K'
    )
    image_url = models.URLField(
        max_length=500, 
        verbose_name='이미지주소'
    )
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name='생성일시'
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name='수정일시'
    )

    class Meta:
        db_table = 'card'
        verbose_name = '싱글카드'
        verbose_name_plural = '싱글카드 목록'
        ordering = ['expansion', 'card_number']
        indexes = [
            models.Index(fields=['expansion', 'card_number']),
            models.Index(fields=['shop_product_code']),
        ]
        # unique_together 제거 (미러/몬스터볼/마스터볼 때문에)
        # unique_together = [['expansion', 'card_number']]

    def __str__(self):
        return f"{self.card_number} - {self.name} ({self.rarity})"

class CardPrice(models.Model):
    """카드 가격 히스토리 모델"""
    
    card = models.ForeignKey(
        Card,
        on_delete=models.CASCADE,
        related_name='prices',
        verbose_name='카드'
    )
    price = models.PositiveIntegerField(
        validators=[MinValueValidator(0)],
        verbose_name='판매가'
    )
    source = models.CharField(
        max_length=50,
        default='naver_shopping',
        verbose_name='출처'
    )
    collected_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='수집시간'
    )

    class Meta:
        db_table = 'card_price'
        verbose_name = '카드가격'
        verbose_name_plural = '카드가격 히스토리'
        ordering = ['-collected_at']
        indexes = [
            models.Index(fields=['card', '-collected_at']),
            models.Index(fields=['collected_at']),
        ]

    def __str__(self):
        return f"{self.card.name} - {self.price}원 ({self.collected_at.strftime('%Y-%m-%d %H:%M')})"
    
class TargetStorePrice(models.Model):
    """특정 판매처(타겟 스토어) 가격 추적 모델"""
    
    card = models.ForeignKey(
        Card,
        on_delete=models.CASCADE,
        related_name='target_prices',
        verbose_name='카드'
    )
    price = models.PositiveIntegerField(
        validators=[MinValueValidator(0)],
        verbose_name='판매가'
    )
    store_name = models.CharField(
        max_length=100,
        default='TCG999',
        verbose_name='타겟 판매처'
    )
    collected_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='수집시간'
    )
    
    class Meta:
        db_table = 'target_store_price'
        verbose_name = '타겟 스토어 가격'
        verbose_name_plural = '타겟 스토어 가격 히스토리'
        ordering = ['-collected_at']
        indexes = [
            models.Index(fields=['card', '-collected_at']),
            models.Index(fields=['store_name', '-collected_at']),
            models.Index(fields=['collected_at']),
        ]
    
    def __str__(self):
        return f"{self.card.name} - {self.price}원 [{self.store_name}] ({self.collected_at.strftime('%Y-%m-%d %H:%M')})"