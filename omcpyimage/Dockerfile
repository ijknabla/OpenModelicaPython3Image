
ARG OPENMODELICA_IMAGE
ARG PYTHON_VERSION

FROM ${OPENMODELICA_IMAGE}

LABEL maintainer "ijknabla <ijknabla@gmail.com>"

RUN mv /etc/apt/sources.list.d/openmodelica.list /etc/apt/sources.list.d/openmodelica.list.bak \
    && apt update \
    && apt install -qy ca-certificates sudo \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && mv /etc/apt/sources.list.d/openmodelica.list.bak /etc/apt/sources.list.d/openmodelica.list

RUN wget https://www.python.org/ftp/python/3.10.13/Python-3.10.13.tgz -O - | tar zxvf - -C /usr/src \
    && /usr/src/Python-3.10.13/configure --enable-optimizations

RUN useradd -m user
