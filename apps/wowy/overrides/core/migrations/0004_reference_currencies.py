"""Keep native site currency choices aligned with the local fixture profiles."""
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0003_remove_sitesettings_stripe_public_key_and_more")]
    operations = [migrations.AlterField(model_name="sitesettings", name="currency",
                  field=models.CharField(choices=[("USD", "US Dollar"), ("EUR", "Euro"), ("BDT", "Bangladeshi Taka")],
                                         default="USD", max_length=3))]
