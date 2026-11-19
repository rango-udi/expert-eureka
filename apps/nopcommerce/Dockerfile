FROM mcr.microsoft.com/dotnet/aspnet:10.0-noble AS app
RUN apt-get update && apt-get install -y --no-install-recommends curl unzip libgdiplus libtiff6 fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN curl --fail --location --retry 3 'https://github.com/nopSolutions/nopCommerce/releases/download/release-5.00.1/nopCommerce_5.00.1_NoSource_linux_x64.zip' -o /tmp/nop.zip \
    && echo '0d810fe641a1661409fe16550a47cac5003834fc1a9876b4c87346d93dd1e6e0  /tmp/nop.zip' | sha256sum -c - \
    && unzip -q /tmp/nop.zip -d /app && rm /tmp/nop.zip
ENV ASPNETCORE_URLS=http://+:8080
EXPOSE 8080
ENTRYPOINT ["dotnet", "Nop.Web.dll"]
