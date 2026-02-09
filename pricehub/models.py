# pricehub/models.py
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone


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
        ('MUR', 'MUR'),
        ('MA', 'MA'),
        ('R', 'R'),
        ('U', 'U'),
        ('C', 'C'),
        ('몬스터볼', '몬스터볼'),
        ('마스터볼', '마스터볼'),
        ('볼 미러', '볼 미러'),
        ('타입 미러', '타입 미러'),
        ('로켓단 미러', '로켓단 미러'),
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
    

# ==================== 원피스 카드 모델 ====================

class OnePieceExpansion(models.Model):
    """원피스 확장팩"""
    code = models.CharField(max_length=10, unique=True, verbose_name="확장팩 코드")
    name = models.CharField(max_length=100, verbose_name="확장팩명")
    release_date = models.DateField(null=True, blank=True, verbose_name="출시일")
    image_url = models.URLField(max_length=500, blank=True, verbose_name="이미지 URL")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    
    class Meta:
        db_table = 'onepiece_expansion'
        verbose_name = '원피스 확장팩'
        verbose_name_plural = '원피스 확장팩 목록'
        ordering = ['-release_date', '-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.code})"


class OnePieceCard(models.Model):
    """원피스 카드"""
    RARITY_CHOICES = [
        ('SEC', 'SEC'),
        ('SL', 'SL'),
        ('SP', 'SP'),
        ('SR', 'SR'),
        ('L', 'L'),
        ('R', 'R'),
        ('UC', 'UC'),
        ('C', 'C'),
        ('P', 'P'),
        # P-, SP- 접두어 레어도
        ('P-SEC', 'P-SEC'),
        ('P-SR', 'P-SR'),
        ('P-L', 'P-L'),
        ('P-R', 'P-R'),
        ('P-UC', 'P-UC'),
        ('P-C', 'P-C'),
        ('SP-SEC', 'SP-SEC'),
        ('SP-SR', 'SP-SR'),
        ('SP-L', 'SP-L'),
        ('SP-R', 'SP-R'),
        ('SP-UC', 'SP-UC'),
        ('SP-C', 'SP-C'),
    ]
    
    expansion = models.ForeignKey(OnePieceExpansion, on_delete=models.CASCADE, related_name='cards', verbose_name="확장팩")
    shop_product_code = models.CharField(max_length=50, unique=True, verbose_name="상품코드")
    card_number = models.CharField(max_length=20, verbose_name="카드번호")
    name = models.CharField(max_length=100, verbose_name="카드명")
    rarity = models.CharField(max_length=20, choices=RARITY_CHOICES, verbose_name="레어도")
    is_manga = models.BooleanField(default=False, verbose_name="망가(슈퍼패러렐)") # 추가
    image_url = models.URLField(max_length=500, blank=True, verbose_name="이미지 URL")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    
    class Meta:
        db_table = 'onepiece_card'
        verbose_name = '원피스 카드'
        verbose_name_plural = '원피스 카드 목록'
        ordering = ['expansion', 'card_number']
    
    def __str__(self):
        return f"{self.name} ({self.card_number}) - {self.expansion.name}"

class OnePieceCardPrice(models.Model):
    """원피스 카드 일반 최저가"""
    card = models.ForeignKey(OnePieceCard, on_delete=models.CASCADE, related_name='prices', verbose_name="카드")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="가격")
    source = models.CharField(max_length=100, verbose_name="판매처")
    collected_at = models.DateTimeField(auto_now_add=True, verbose_name="수집일시")
    
    class Meta:
        db_table = 'onepiece_card_price'
        verbose_name = '원피스 카드 가격'
        verbose_name_plural = '원피스 카드 가격 목록'
        ordering = ['-collected_at']
    
    def __str__(self):
        return f"{self.card.name} - {self.price}원 ({self.collected_at.strftime('%Y-%m-%d')})"


class OnePieceTargetStorePrice(models.Model):
    """원피스 카드 카드킹덤 가격"""
    card = models.ForeignKey(OnePieceCard, on_delete=models.CASCADE, related_name='cardkingdom_prices', verbose_name="카드")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="가격")
    store_name = models.CharField(max_length=100, verbose_name="판매처")
    collected_at = models.DateTimeField(auto_now_add=True, verbose_name="수집일시")
    
    class Meta:
        db_table = 'onepiece_target_store_price'
        verbose_name = '원피스 카드킹덤 가격'
        verbose_name_plural = '원피스 카드킹덤 가격 목록'
        ordering = ['-collected_at']
    
    def __str__(self):
        return f"{self.card.name} - {self.price}원 ({self.store_name})"


# 기존 포켓몬 한글판 모델은 그대로 유지
# Expansion, Card, CardPrice, TargetStorePrice

# ==================== 포켓몬 일본판 모델 ====================

class JapanExpansion(models.Model):
    """포켓몬 일본판 확장팩"""
    code = models.CharField(max_length=20, unique=True, verbose_name="확장팩 코드")
    name = models.CharField(max_length=200, verbose_name="확장팩명")
    release_date = models.DateField(null=True, blank=True, verbose_name="출시일")
    image_url = models.URLField(max_length=500, blank=True, verbose_name="이미지 URL")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    
    class Meta:
        db_table = 'japan_expansion'
        verbose_name = '포켓몬 일본판 확장팩'
        verbose_name_plural = '포켓몬 일본판 확장팩 목록'
        ordering = ['-release_date', '-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.code})"


class JapanCard(models.Model):
    """포켓몬 일본판 카드"""
    RARITY_CHOICES = [
        ('MUR', 'MUR'),
        ('UR', 'UR'),
        ('SSR', 'SSR'),
        ('SAR', 'SAR'),
        ('SR', 'SR'),
        ('HR', 'HR'),
        ('CSR', 'CSR'),
        ('CHR', 'CHR'),
        ('AR', 'AR'),
        ('BWR', 'BWR'),
        ('마스터볼', '마스터볼'),
        ('몬스터볼', '몬스터볼'),
        ('이로치', '이로치'),
        ('미러', '미러'),
        ('RRR', 'RRR'),
        ('RR', 'RR'),
        ('R', 'R'),
        ('U', 'U'),
        ('C', 'C'),
    ]
    
    expansion = models.ForeignKey(JapanExpansion, on_delete=models.CASCADE, related_name='cards', verbose_name="확장팩")
    shop_product_code = models.CharField(max_length=50, unique=True, verbose_name="상품코드")
    card_number = models.CharField(max_length=20, verbose_name="카드번호")
    name = models.CharField(max_length=100, verbose_name="카드명")
    rarity = models.CharField(max_length=20, choices=RARITY_CHOICES, verbose_name="레어도")
    is_mirror = models.BooleanField(default=False, verbose_name="미러")
    mirror_type = models.CharField(max_length=50, blank=True, verbose_name="미러 타입")  # 추가
    image_url = models.URLField(max_length=500, blank=True, verbose_name="이미지 URL")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    
    class Meta:
        db_table = 'japan_card'
        verbose_name = '포켓몬 일본판 카드'
        verbose_name_plural = '포켓몬 일본판 카드 목록'
        ordering = ['expansion', 'card_number']
    
    def __str__(self):
        return f"{self.name} ({self.card_number}) - {self.expansion.name}"

class JapanCardPrice(models.Model):
    """포켓몬 일본판 카드 일반 최저가"""
    card = models.ForeignKey(JapanCard, on_delete=models.CASCADE, related_name='prices', verbose_name="카드")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="가격")
    source = models.CharField(max_length=100, verbose_name="출처")
    collected_at = models.DateTimeField(default=timezone.now, verbose_name="수집일시")
    
    class Meta:
        db_table = 'japan_card_price'
        verbose_name = '포켓몬 일본판 카드 가격'
        verbose_name_plural = '포켓몬 일본판 카드 가격 목록'
        ordering = ['-collected_at']
    
    def __str__(self):
        return f"{self.card.name} - {self.price}원 ({self.collected_at.strftime('%Y-%m-%d')})"


class JapanTargetStorePrice(models.Model):
    """포켓몬 일본판 카드 TCG999 가격"""
    card = models.ForeignKey(JapanCard, on_delete=models.CASCADE, related_name='tcg999_prices', verbose_name="카드")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="가격")
    store_name = models.CharField(max_length=100, verbose_name="판매처")
    collected_at = models.DateTimeField(auto_now_add=True, verbose_name="수집일시")
    
    class Meta:
        db_table = 'japan_target_store_price'
        verbose_name = '포켓몬 일본판 TCG999 가격'
        verbose_name_plural = '포켓몬 일본판 TCG999 가격 목록'
        ordering = ['-collected_at']
    
    def __str__(self):
        return f"{self.card.name} - {self.price}원 ({self.store_name})"