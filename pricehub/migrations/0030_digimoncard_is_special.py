from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pricehub', '0029_digimon_models'),
    ]

    operations = [
        migrations.AddField(
            model_name='digimoncard',
            name='is_special',
            field=models.BooleanField(default=False, verbose_name='스페셜'),
        ),
    ]
