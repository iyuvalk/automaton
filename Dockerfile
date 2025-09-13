FROM python:2.7

RUN sed -i 's|deb.debian.org|archive.debian.org|g' /etc/apt/sources.list && \
    sed -i '/security.debian.org/d' /etc/apt/sources.list && \ 
    apt-get update && \
    apt-get install -y at && \
    rm -rf /var/lib/apt/lists/*

ADD . . 
