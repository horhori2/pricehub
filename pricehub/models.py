# pricehub/models.py
import hashlib
import secrets
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

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
        verbose_name = '포켓몬 한글판 확장팩'
        verbose_name_plural = '포켓몬 한글판 확장팩 목록'
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
        ('K', 'K'),
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
    is_favorite = models.BooleanField(default=False, verbose_name='즐겨찾기', db_index=True)
    is_teukil = models.BooleanField(default=False, verbose_name='특일', db_index=True)
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='생성일시'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='수정일시'
    )
    selling_price = models.PositiveIntegerField(
        default=0,
        verbose_name='판매가',
        help_text='관리자가 설정한 최종 판매가 (0=미설정)'
    )
    modified_price = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True,
        verbose_name='수정 가격 (일괄 설정 임시값)',
    )
    latest_raw_data = models.JSONField(
        null=True,
        blank=True,
        verbose_name='최신 수집 raw_data 캐시',
        help_text='가격 수집 시 자동 업데이트. bulk_price 조회에 사용.'
    )
    latest_market_price = models.PositiveIntegerField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name='최신 시장 최저가 캐시',
        help_text='가격 수집 시 자동 업데이트(경쟁사 최저가, 자기 매장 제외). '
                   '카드마다 가격 히스토리를 서브쿼리로 뒤지지 않도록 하는 캐시 컬럼 — '
                   '목록 정렬·저가 경고 판정에 사용.'
    )

    class Meta:
        db_table = 'card'
        verbose_name = '포켓몬 한글판 카드'
        verbose_name_plural = '포켓몬 한글판 카드 목록'
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
    raw_data = models.JSONField(default=dict)
    collected_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='수집시간'
    )

    class Meta:
        db_table = 'card_price'
        verbose_name = '포켓몬 한글판 가격'
        verbose_name_plural = '포켓몬 한글판 가격 목록'
        ordering = ['-collected_at']
        indexes = [
            models.Index(fields=['card', '-collected_at']),
            models.Index(fields=['collected_at']),
        ]

    def __str__(self):
        return f"{self.card.name} - {self.price}원 ({self.collected_at.strftime('%Y-%m-%d %H:%M')})"
    

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
        verbose_name = '원피스 한글판 확장팩'
        verbose_name_plural = '원피스 한글판 확장팩 목록'
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
        ('MANGA', 'MANGA'),
        ('P-SEC', 'P-SEC'),
        ('P-SR', 'P-SR'),
        ('P-L', 'P-L'),
        ('P-R', 'P-R'),
        ('P-UC', 'P-UC'),
        ('P-C', 'P-C'),
        ('D', 'D'),
        ('P-D', 'P-D'),
    ]

    expansion = models.ForeignKey(OnePieceExpansion, on_delete=models.CASCADE, related_name='cards', verbose_name="확장팩")
    shop_product_code = models.CharField(max_length=50, unique=True, verbose_name="상품코드")
    card_number = models.CharField(max_length=20, verbose_name="카드번호")
    name = models.CharField(max_length=100, verbose_name="카드명")
    rarity = models.CharField(max_length=20, choices=RARITY_CHOICES, verbose_name="레어도")
    image_url = models.URLField(max_length=500, blank=True, verbose_name="이미지 URL")
    is_favorite = models.BooleanField(default=False, verbose_name='즐겨찾기', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    selling_price = models.PositiveIntegerField(
        default=0,
        verbose_name='판매가',
        help_text='관리자가 설정한 최종 판매가 (0=미설정)'
    )
    modified_price = models.PositiveIntegerField(
    default=0,
    verbose_name='수정 가격 (일괄 설정 임시값)',
    help_text='일괄 설정 실행 시 임시 저장. 하락 시 작업자 확인 후 반영.',
    )
    latest_raw_data = models.JSONField(
        null=True,
        blank=True,
        verbose_name='최신 수집 raw_data 캐시',
        help_text='가격 수집 시 자동 업데이트. bulk_price 조회에 사용.'
    )
    latest_market_price = models.PositiveIntegerField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name='최신 시장 최저가 캐시',
        help_text='가격 수집 시 자동 업데이트(경쟁사 최저가, 자기 매장 제외). '
                   '카드마다 가격 히스토리를 서브쿼리로 뒤지지 않도록 하는 캐시 컬럼 — '
                   '목록 정렬·저가 경고 판정에 사용.'
    )
    class Meta:
        db_table = 'onepiece_card'
        verbose_name = '원피스 한글판 카드'
        verbose_name_plural = '원피스 한글판 카드 목록'
        ordering = ['expansion', 'card_number']
    
    def __str__(self):
        return f"{self.name} ({self.card_number}) - {self.expansion.name}"
    
    @staticmethod
    def normalize_rarity(rarity: str) -> str:
        """SP-* 레어도를 전부 'SP'로 정규화"""
        if rarity and rarity.startswith('SP-'):
            return 'SP'
        return rarity

    def save(self, *args, **kwargs):
        self.rarity = self.normalize_rarity(self.rarity)
        super().save(*args, **kwargs)

class OnePieceCardPrice(models.Model):
    """원피스 카드 일반 최저가"""
    card = models.ForeignKey(OnePieceCard, on_delete=models.CASCADE, related_name='prices', verbose_name="카드")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="가격")
    source = models.CharField(max_length=100, verbose_name="판매처")
    raw_data = models.JSONField(default=dict, verbose_name='네이버 API 원본 JSON')
    collected_at = models.DateTimeField(auto_now_add=True, verbose_name="수집일시")
    
    class Meta:
        db_table = 'onepiece_card_price'
        verbose_name = '원피스 한글판 가격'
        verbose_name_plural = '원피스 한글판 가격 목록'
        ordering = ['-collected_at']
    
    def __str__(self):
        return f"{self.card.name} - {self.price}원 ({self.collected_at.strftime('%Y-%m-%d')})"


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

    selling_price = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name='판매가',
        help_text='관리자가 설정한 최종 판매가'
    )
    
    class Meta:
        db_table = 'japan_card'
        verbose_name = '포켓몬 일본판 카드'
        verbose_name_plural = '포켓몬 일본판 카드 목록'
        ordering = ['expansion', 'card_number']
    
    def __str__(self):
        return f"{self.name} ({self.card_number}) - {self.expansion.name}"

class JapanCardPrice(models.Model):
    card = models.ForeignKey(JapanCard, on_delete=models.CASCADE, related_name='prices')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    source = models.CharField(max_length=50)  # 유유테이, 카드러쉬
    condition = models.CharField(max_length=10, default='S', blank=True)  # S, A-, B, C 등
    collected_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'japan_card_price'
        verbose_name = '포켓몬 일본판 가격'
        verbose_name_plural = '포켓몬 일본판 가격 목록'
        ordering = ['-collected_at']
        indexes = [
            models.Index(fields=['card', 'source', 'condition', '-collected_at']),
        ]

    def __str__(self):
        condition_display = f"[{self.condition}]" if self.condition != 'S' else ""
        return f"{self.card.name} - {self.price}엔 {condition_display} ({self.source})"

    

# ==================== 디지몬 카드 모델 ====================

class DigimonExpansion(models.Model):
    """디지몬 한글판 확장팩"""
    code = models.CharField(max_length=20, unique=True, verbose_name="확장팩 코드")
    name = models.CharField(max_length=100, verbose_name="확장팩명")
    category_id = models.IntegerField(unique=True, verbose_name="카테고리 ID", help_text="digimoncard.co.kr 카테고리 ID")
    release_date = models.DateField(null=True, blank=True, verbose_name="출시일")
    image_url = models.URLField(max_length=500, blank=True, verbose_name="이미지 URL")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")

    class Meta:
        db_table = 'digimon_expansion'
        verbose_name = '디지몬 한글판 확장팩'
        verbose_name_plural = '디지몬 한글판 확장팩 목록'
        ordering = ['-release_date', '-created_at']

    def __str__(self):
        return f"{self.name} ({self.code})"


class DigimonCard(models.Model):
    """디지몬 한글판 카드"""
    RARITY_CHOICES = [
        ('SEC', 'SEC'),
        ('SR', 'SR'),
        ('R', 'R'),
        ('U', 'U'),
        ('C', 'C'),
        ('P', 'P'),
        ('PR', 'PR'),
        ('L', 'L'),
        ('DR', 'DR'),
        ('AC', 'AC'),
    ]

    expansion = models.ForeignKey(DigimonExpansion, on_delete=models.CASCADE, related_name='cards', verbose_name="확장팩")
    shop_product_code = models.CharField(max_length=50, unique=True, verbose_name="상품코드")
    card_number = models.CharField(max_length=20, verbose_name="카드번호")
    name = models.CharField(max_length=100, verbose_name="카드명")
    rarity = models.CharField(max_length=20, choices=RARITY_CHOICES, verbose_name="레어도")
    card_type = models.CharField(max_length=20, blank=True, verbose_name="카드타입")
    card_level = models.CharField(max_length=10, blank=True, verbose_name="카드레벨")
    is_parallel = models.BooleanField(default=False, verbose_name="패러렐")
    is_scarce = models.BooleanField(default=False, verbose_name="희소")
    is_special = models.BooleanField(default=False, verbose_name="스페셜")
    image_url = models.URLField(max_length=500, blank=True, verbose_name="이미지 URL")
    is_favorite = models.BooleanField(default=False, verbose_name='즐겨찾기', db_index=True)
    selling_price = models.PositiveIntegerField(
        default=0,
        verbose_name='판매가',
        help_text='관리자가 설정한 최종 판매가 (0=미설정)'
    )
    modified_price = models.PositiveIntegerField(
        default=0,
        verbose_name='수정 가격 (일괄 설정 임시값)',
        help_text='일괄 설정 실행 시 임시 저장. 하락 시 작업자 확인 후 반영.',
    )
    latest_raw_data = models.JSONField(
        null=True,
        blank=True,
        verbose_name='최신 수집 raw_data 캐시',
        help_text='가격 수집 시 자동 업데이트. bulk_price 조회에 사용.'
    )
    latest_market_price = models.PositiveIntegerField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name='최신 시장 최저가 캐시',
        help_text='가격 수집 시 자동 업데이트(경쟁사 최저가, 자기 매장 제외). '
                   '카드마다 가격 히스토리를 서브쿼리로 뒤지지 않도록 하는 캐시 컬럼 — '
                   '목록 정렬·저가 경고 판정에 사용.'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")

    class Meta:
        db_table = 'digimon_card'
        verbose_name = '디지몬 한글판 카드'
        verbose_name_plural = '디지몬 한글판 카드 목록'
        ordering = ['expansion', 'card_number']

    def __str__(self):
        tags = []
        if self.is_parallel:
            tags.append('패러렐')
        if self.is_scarce:
            tags.append('희소')
        if self.is_special:
            tags.append('스페셜')
        tag_str = f" [{', '.join(tags)}]" if tags else ''
        return f"{self.name} ({self.card_number}) - {self.expansion.name}{tag_str}"


class DigimonCardPrice(models.Model):
    """디지몬 한글판 가격"""
    card = models.ForeignKey(DigimonCard, on_delete=models.CASCADE, related_name='prices', verbose_name="카드")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="가격")
    source = models.CharField(max_length=100, verbose_name="판매처")
    raw_data = models.JSONField(default=dict, verbose_name='네이버 API 원본 JSON')
    collected_at = models.DateTimeField(auto_now_add=True, verbose_name="수집일시")

    class Meta:
        db_table = 'digimon_card_price'
        verbose_name = '디지몬 한글판 가격'
        verbose_name_plural = '디지몬 한글판 가격 목록'
        ordering = ['-collected_at']

    def __str__(self):
        return f"{self.card.name} - {self.price}원 ({self.collected_at.strftime('%Y-%m-%d')})"


# ==================== API KEY 발급 - 외부 프로그램 접근 허용 ====================
class APIKey(models.Model):
    """
    외부 클라이언트용 API Key.

    DB에는 원본 키가 아니라 SHA-256 해시만 저장된다 (key 필드).
    DB가 유출돼도 저장된 값만으로는 원본 키를 복원할 수 없다.

    발급:
        python manage.py shell
        >>> from pricehub.models import APIKey
        >>> instance, raw_key = APIKey.objects.create_key(name='카드관리프로그램')
        >>> raw_key  # 이 시점에만 확인 가능 — 다시 조회 불가능하니 클라이언트에 바로 전달할 것
    """
    name = models.CharField(max_length=100, verbose_name='클라이언트명', help_text='예: 카드관리프로그램')
    key = models.CharField(max_length=64, unique=True, verbose_name='API Key 해시 (SHA-256)')
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

    @staticmethod
    def hash_key(raw_key: str) -> str:
        return hashlib.sha256(raw_key.encode()).hexdigest()

    @classmethod
    def create_key(cls, name: str) -> tuple:
        """
        새 API Key 발급.
        Returns: (APIKey instance, raw_key)
        raw_key는 이 시점에만 확인 가능 — DB에는 해시만 저장된다.
        """
        raw_key = secrets.token_urlsafe(32)
        instance = cls.objects.create(name=name, key=cls.hash_key(raw_key))
        return instance, raw_key


# ==================== 매입리스트 관리 ====================
# 포켓몬/원피스/디지몬 등 게임별로 "매입리스트"를 만들고,
# 개별 카드를 담아 판매가와 별도로 매입가를 결정한다.
# 여러 카드 모델(Card, JapanCard, OnePieceCard, DigimonCard)을
# 하나의 항목 모델로 다루기 위해 GenericForeignKey를 사용한다.

def round_to_100(value):
    """100원 단위로 반올림 (예: 149 -> 100, 150 -> 200)"""
    return int((value + 50) // 100) * 100


class PurchaseList(models.Model):
    """매입리스트 — 게임별로 관리하는 카드 매입 목록"""

    GAME_TYPE_CHOICES = [
        ('pokemon_kr', '포켓몬 한글판'),
        ('pokemon_jp', '포켓몬 일본판'),
        ('onepiece_kr', '원피스 한글판'),
        ('digimon_kr', '디지몬 한글판'),
    ]

    name = models.CharField(
        max_length=200,
        verbose_name='매입리스트명',
        help_text='예: 2026년 7월 매입'
    )
    game_type = models.CharField(
        max_length=20,
        choices=GAME_TYPE_CHOICES,
        db_index=True,
        verbose_name='게임 구분'
    )
    description = models.TextField(blank=True, verbose_name='설명')
    default_purchase_ratio = models.DecimalField(
        max_digits=5, decimal_places=2, default=50,
        verbose_name='기본 매입가 비율(%)',
        help_text='카드를 추가할 때 추천 매입가를 계산하는 기본 비율. 보통 판매가의 50%.'
    )
    is_active = models.BooleanField(default=True, verbose_name='활성 여부')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')

    class Meta:
        db_table = 'purchase_list'
        verbose_name = '매입리스트'
        verbose_name_plural = '매입리스트 목록'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_game_type_display()}] {self.name}"


class PurchaseListItem(models.Model):
    """매입리스트에 담긴 개별 카드 + 매입가 결정 정보"""

    purchase_list = models.ForeignKey(
        PurchaseList, on_delete=models.CASCADE,
        related_name='items', verbose_name='매입리스트'
    )

    # 여러 카드 모델(Card / JapanCard / OnePieceCard / DigimonCard)을
    # 하나의 항목 모델에서 다루기 위한 GenericForeignKey
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, verbose_name='카드 종류')
    object_id = models.PositiveIntegerField(verbose_name='카드 ID')
    card = GenericForeignKey('content_type', 'object_id')

    selling_price_snapshot = models.PositiveIntegerField(
        default=0, verbose_name='추가 시점 판매가'
    )
    purchase_ratio = models.DecimalField(
        max_digits=5, decimal_places=2, default=50,
        verbose_name='적용 매입가 비율(%)'
    )
    recommended_purchase_price = models.PositiveIntegerField(
        default=0, verbose_name='추천 매입가',
        help_text='판매가 × 매입가 비율로 자동 계산됨'
    )
    purchase_price = models.PositiveIntegerField(
        null=True, blank=True, verbose_name='확정 매입가',
        help_text='가격 관리자가 최종 결정한 매입가. 비어있으면 미확정(추천가만 있는 상태).'
    )
    memo = models.CharField(max_length=200, blank=True, verbose_name='메모')

    added_at = models.DateTimeField(auto_now_add=True, verbose_name='추가일시')
    decided_at = models.DateTimeField(null=True, blank=True, verbose_name='매입가 확정일시')

    class Meta:
        db_table = 'purchase_list_item'
        verbose_name = '매입리스트 항목'
        verbose_name_plural = '매입리스트 항목 목록'
        ordering = ['-added_at']
        unique_together = [['purchase_list', 'content_type', 'object_id']]
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
        ]

    def __str__(self):
        return f"{self.purchase_list.name} - card#{self.object_id}"

    def compute_recommended_price(self):
        ratio = self.purchase_ratio if self.purchase_ratio is not None else 50
        base = self.selling_price_snapshot or 0
        raw = base * float(ratio) / 100
        return round_to_100(raw)

    @property
    def is_decided(self):
        return self.purchase_price is not None

    @property
    def final_purchase_price(self):
        """확정 매입가가 없으면 추천가를 잠정값으로 제공 (외부 API용)"""
        return self.purchase_price if self.purchase_price is not None else self.recommended_purchase_price

    @property
    def cached_card(self):
        """
        N+1 방지를 위해 purchase_config.attach_cards() 가 미리 채워둔
        _card_cache 가 있으면 그걸 쓰고, 없으면 GenericForeignKey로 직접 조회.
        """
        if hasattr(self, '_card_cache'):
            return self._card_cache
        return self.card

    def save(self, *args, **kwargs):
        self.recommended_purchase_price = self.compute_recommended_price()
        super().save(*args, **kwargs)


class RarityPurchasePrice(models.Model):
    """
    레어도별 일괄 매입 고정가 — 매입리스트에 개별 등록 안 된 카드에 적용.

    인기 카드만 PurchaseListItem으로 개별 등록해 매입가를 정하고, 나머지
    카드는 레어도에 맞는 이 고정가를 화면에 즉석으로 보여준다 — 별도 행을
    만들지 않음. 시장가와 무관하게 레어도만으로 정해지는 고정 금액이며,
    게임 종류 전체에 공통 적용(매입리스트별로 따로 두지 않음).
    """
    GAME_TYPE_CHOICES = PurchaseList.GAME_TYPE_CHOICES

    game_type = models.CharField(
        max_length=20,
        choices=GAME_TYPE_CHOICES,
        db_index=True,
        verbose_name='게임 구분'
    )
    rarity = models.CharField(max_length=50, verbose_name='레어도')
    price = models.PositiveIntegerField(
        default=0,
        verbose_name='매입 고정가',
        help_text='이 레어도의 카드를 개별 등록 없이 매입할 때 적용할 고정 금액(원)'
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')

    class Meta:
        db_table = 'rarity_purchase_price'
        verbose_name = '레어도별 매입 고정가'
        verbose_name_plural = '레어도별 매입 고정가 목록'
        ordering = ['game_type', 'rarity']
        unique_together = [['game_type', 'rarity']]

    def __str__(self):
        return f"[{self.get_game_type_display()}] {self.rarity} — {self.price}원"