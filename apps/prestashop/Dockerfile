FROM prestashop/prestashop:9.2.1-6.1-classic-8.3-apache AS app
RUN printf 'memory_limit=512M\nmax_execution_time=600\nopcache.memory_consumption=64\n' > /usr/local/etc/php/conf.d/fuzcake.ini \
    && printf '<IfModule mpm_prefork_module>\nStartServers 1\nMinSpareServers 1\nMaxSpareServers 1\nMaxRequestWorkers 2\nMaxConnectionsPerChild 100\n</IfModule>\n' > /etc/apache2/conf-available/fuzcake.conf \
    && a2enconf fuzcake
EXPOSE 80
