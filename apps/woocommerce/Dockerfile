FROM wordpress:7.1.4-php8.3-apache AS app
RUN apt-get update && apt-get install -y --no-install-recommends curl unzip \
    && rm -rf /var/lib/apt/lists/* \
    && curl --fail --location --retry 3 'https://github.com/woocommerce/woocommerce/releases/download/11.3.0/woocommerce.zip' -o /tmp/woocommerce.zip \
    && echo '8fa4965ca8b42d3dcebad771c1e70792e8b0c685b5a9187438c0dfda9cfdf9bb  /tmp/woocommerce.zip' | sha256sum -c - \
    && unzip -q /tmp/woocommerce.zip -d /usr/src/wordpress/wp-content/plugins && rm /tmp/woocommerce.zip
COPY theme/ /usr/src/wordpress/wp-content/themes/fuzcake/
RUN printf 'memory_limit=256M\nopcache.memory_consumption=64\n' > /usr/local/etc/php/conf.d/fuzcake.ini \
    && printf '<IfModule mpm_prefork_module>\nStartServers 1\nMinSpareServers 1\nMaxSpareServers 1\nMaxRequestWorkers 2\nMaxConnectionsPerChild 100\n</IfModule>\n' > /etc/apache2/conf-available/fuzcake.conf \
    && a2enconf fuzcake
EXPOSE 80
