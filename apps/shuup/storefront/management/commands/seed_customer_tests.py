"""Prepare the explicitly documented fictional customer without changing existing access."""
from pathlib import Path
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from shuup.core.models import Shop
from test_design.specification import load_specification
from scripts.customer_inputs import validate_test_data
from storefront.management.commands.seed_demo import seed_customer_addresses


class Command(BaseCommand):
    """Create only the dedicated active test fixture; preserve unrelated accounts."""
    help = 'Prepare the public fictional customer declared in CUSTOMER_DESIGN.yaml.'

    @transaction.atomic
    def handle(self, *args, **options):
        """Refuse collisions or mismatched credentials instead of resetting an account."""
        model = load_specification(Path(__file__).resolve().parents[3] / 'tests/data/CUSTOMER_DESIGN.yaml')
        validate_test_data(model)
        from scripts.customer_extensions import extension_cases
        extension_cases(model)
        accounts = [model['test_data']['existing_customer']] + model.get('extensions', {}).get('accounts', [])
        for data in accounts:
            users = get_user_model().objects
            user = users.filter(username=data['username']).first()
            if user is None:
                if users.filter(email__iexact=data['email']).exists():
                    raise CommandError('The customer test email is already assigned; existing accounts were preserved.')
                user = users.create_user(username=data['username'], email=data['email'], password=data['password'],
                                         first_name=data['first_name'], last_name=data['last_name'], is_active=True)
            elif (user.email != data['email'] or not user.check_password(data['password']) or not user.is_active
                  or user.is_staff or user.is_superuser):
                raise CommandError('The customer test account differs from the reviewed fixture; existing access was preserved. Choose another explicit fixture or restore the matching test data.')
        shop = Shop.objects.first()
        if shop is None:
            raise CommandError('Initialize the local store before preparing customer test accounts.')
        for data in accounts:
            seed_customer_addresses(users.get(username=data['username']), shop)
        self.stdout.write('The documented customer test account is ready; no passwords were printed.')
