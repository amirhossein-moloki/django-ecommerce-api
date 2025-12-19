# Generated manually
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('orders', '0005_merge_20241215_0001'),
    ]

    operations = [
        migrations.CreateModel(
            name='PaymentTransaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('track_id', models.CharField(db_index=True, max_length=100)),
                ('event_type', models.CharField(choices=[('initiate', 'Initiate'), ('verify', 'Verify'), ('callback', 'Callback')], max_length=20)),
                ('status', models.CharField(choices=[('received', 'Received'), ('processed', 'Processed'), ('failed', 'Failed'), ('skipped', 'Skipped'), ('rejected', 'Rejected')], max_length=20)),
                ('amount', models.PositiveBigIntegerField(blank=True, null=True)),
                ('result_code', models.CharField(blank=True, max_length=20)),
                ('ref_id', models.CharField(blank=True, max_length=120)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('signature', models.CharField(blank=True, max_length=128)),
                ('message', models.TextField(blank=True)),
                ('raw_payload', models.JSONField(blank=True, default=dict)),
                ('gateway_response', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('order', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='payment_transactions', to='orders.order')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='paymenttransaction',
            index=models.Index(fields=['event_type', 'status'], name='payment_pay_event_t_e88b95_idx'),
        ),
        migrations.AddIndex(
            model_name='paymenttransaction',
            index=models.Index(fields=['order', 'created_at'], name='payment_pay_order_i_205932_idx'),
        ),
    ]
