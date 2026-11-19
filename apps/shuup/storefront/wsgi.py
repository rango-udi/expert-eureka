"""Create the Django application and serve only generated product media locally."""

import os
from django.core.wsgi import get_wsgi_application
from django.conf import settings
from whitenoise import WhiteNoise

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "storefront.settings")
def create_application(django_application):
    """Index collected static once while keeping native uploads discoverable at runtime."""
    media_application = WhiteNoise(django_application, autorefresh=True)
    media_application.add_files(str(settings.MEDIA_ROOT), prefix="media/")

    def route_media(environ, start_response):
        """Limit live filesystem checks to media requests; never cache business responses."""
        if environ.get("PATH_INFO", "").startswith(settings.MEDIA_URL):
            return media_application(environ, start_response)
        return django_application(environ, start_response)

    result = WhiteNoise(route_media, autorefresh=False)
    result.add_files(str(settings.STATIC_ROOT), prefix="static/")
    return result


application = create_application(get_wsgi_application())
