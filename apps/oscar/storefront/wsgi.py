"""Create the Django application and serve only generated product media locally."""

import os
from django.core.wsgi import get_wsgi_application
from django.conf import settings
from whitenoise import WhiteNoise

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "storefront.settings")
application = WhiteNoise(get_wsgi_application(), autorefresh=True)
application.add_files(str(settings.MEDIA_ROOT), prefix="media/")
