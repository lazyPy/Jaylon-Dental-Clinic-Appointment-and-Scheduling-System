# Generated by Django 4.2.15 on 2024-09-08 00:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0009_user_password_reset_token_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='appointment',
            name='attended',
            field=models.BooleanField(default=False),
        ),
    ]
