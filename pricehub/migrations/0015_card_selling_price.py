# pricehub/migrations/0015_card_selling_price.py
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pricehub', '0014_cardprice_raw_data'),
    ]

    operations = [
        migrations.AddField(
            model_name='card',
            name='selling_price',
            field=models.PositiveIntegerField(
                null=True,
                blank=True,
                verbose_name='판매가',
                help_text='관리자가 설정한 최종 판매가'
            ),
        ),
    ]