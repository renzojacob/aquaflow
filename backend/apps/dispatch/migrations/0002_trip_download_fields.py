from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dispatch', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='trip',
            name='downloaded_version',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='trip',
            name='downloaded_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
