"""
Card 모델에 is_favorite 필드 추가
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pricehub', '0024_migrate_manga_rarity_remove_is_manga'),  # ← 실제 마지막 마이그레이션 번호로 변경
    ]

    operations = [
        migrations.AddField(
            model_name='card',
            name='is_favorite',
            field=models.BooleanField(
                default=False,
                verbose_name='즐겨찾기',
                db_index=True,
            ),
        ),
        migrations.AddField(
            model_name='onepiececard',
            name='is_favorite',
            field=models.BooleanField(
                default=False,
                verbose_name='즐겨찾기',
                db_index=True,
            ),
        ),
    ]
