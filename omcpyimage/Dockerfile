
ARG OPENMODELICA_IMAGE

FROM ${OPENMODELICA_IMAGE}

LABEL maintainer "ijknabla <ijknabla@gmail.com>"

RUN mv /etc/apt/sources.list.d/openmodelica.list /etc/apt/sources.list.d/openmodelica.list.bak \
    && apt update \
    && apt install -qy ca-certificates sudo \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && mv /etc/apt/sources.list.d/openmodelica.list.bak /etc/apt/sources.list.d/openmodelica.list

RUN useradd -m user
