"""Create a private local wallet ledger; no external payment credentials are stored."""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [migrations.CreateModel(name="WalletMovement", fields=[
        ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
        ("reference", models.CharField(max_length=64, unique=True)),
        ("kind", models.CharField(max_length=16)),
        ("amount_minor", models.BigIntegerField()),
        ("currency", models.CharField(default="USD", max_length=3)),
        ("status", models.CharField(default="posted", max_length=16)),
        ("description", models.CharField(max_length=200)),
        ("method", models.CharField(max_length=64)),
        ("occurred_at", models.DateTimeField()),
        ("owner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
    ], options={"ordering": ("-occurred_at", "-pk")})]
