# pricehub/migrations/0016_apikey.py
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pricehub', '0015_card_selling_price'),
    ]

    operations = [
        migrations.CreateModel(
            name='APIKey',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100, verbose_name='클라이언트명')),
                ('key', models.CharField(max_length=64, unique=True, verbose_name='API Key')),
                ('is_active', models.BooleanField(default=True, verbose_name='활성 여부')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('last_used_at', models.DateTimeField(blank=True, null=True, verbose_name='마지막 사용')),
            ],
            options={'db_table': 'api_key', 'verbose_name': 'API Key', 'verbose_name_plural': 'API Key 목록'},
        ),
    ]
