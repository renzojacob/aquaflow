from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('station', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='servicearea',
            name='barangays',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
