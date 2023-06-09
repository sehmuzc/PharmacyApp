# Generated by Django 4.2.dev20221028064633 on 2023-03-18 16:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pharmacy', '0004_alter_prescription_doctor_alter_prescription_patient'),
    ]

    operations = [
        migrations.AddField(
            model_name='medicine',
            name='description',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='medicine',
            name='manufacturer',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='medicine',
            name='price',
            field=models.DecimalField(decimal_places=2, default=100, max_digits=6),
            preserve_default=False,
        ),
    ]
