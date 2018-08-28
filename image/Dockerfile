FROM debian:latest
LABEL maintainer="kontakt@maximeveit.de"

# Install fusiondirctory-schema and insert schema with the official script
RUN DEBIAN_FRONTEND=noninteractive apt-get update && apt-get install -yq --no-install-recommends python3 unison
#    && apt-get install -yq --no-install-recommends fusiondirectory-plugin-systems fusiondirectory-plugin-systems-schema

# Cleanup
RUN apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN mkdir -p /volumes/sync

# Set entrypoint
ADD scripts/* /opt/
ENTRYPOINT ["/opt/startup.py"]


