
ARG OPENMODELICA_IMAGE
ARG PYTHON_VERSION

FROM ${OPENMODELICA_IMAGE}

LABEL maintainer "ijknabla <ijknabla@gmail.com>"

RUN mv /etc/apt/sources.list.d/openmodelica.list /etc/apt/sources.list.d/openmodelica.list.bak \
    && apt update \
    && env DEBIAN_FRONTEND=noninteractive apt install -qy ca-certificates sudo tzdata \
    && apt clean \
    && rm -rf /var/lib/apt/lists/* \
    && mv /etc/apt/sources.list.d/openmodelica.list.bak /etc/apt/sources.list.d/openmodelica.list

RUN apt update \
    && apt install -qy  build-essential libssl-dev zlib1g-dev \
                        libbz2-dev libreadline-dev libsqlite3-dev curl \
                        libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev \
#     && wget https://www.python.org/ftp/python/3.10.13/Python-3.10.13.tgz -O - | tar zxvf - -C /usr/src \
#     && (cd /usr/src/Python-3.10.13/ && ./configure --enable-optimizations && make altinstall) \
    && apt clean \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m user
