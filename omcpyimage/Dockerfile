# syntax=docker/dockerfile:1
ARG BUILD_IMAGE="ubuntu:22.04"
ARG OPENMODELICA_IMAGE="openmodelica/openmodelica:v1.22.0-minimal"

FROM ${BUILD_IMAGE}
LABEL maintainer "ijknabla <ijknabla@gmail.com>"

RUN apt update && env DEBIAN_FRONTEND=noninteractive apt install -qy \
        tzdata
RUN apt update && apt install -qy \
        build-essential libssl-dev zlib1g-dev \
        libbz2-dev libreadline-dev libsqlite3-dev curl \
        libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev

ARG PYTHON_VERSION="3.10.13"
RUN curl https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tgz -o - | tar zxvf - -C /usr/src
RUN (cd /usr/src/Python-${PYTHON_VERSION}/ && ./configure --enable-optimizations)
RUN make -C/usr/src/Python-${PYTHON_VERSION}/ -j4
RUN make -C/usr/src/Python-${PYTHON_VERSION}/ altinstall

FROM ${OPENMODELICA_IMAGE}
LABEL maintainer "ijknabla <ijknabla@gmail.com>"

RUN mv /etc/apt/sources.list.d/openmodelica.list /etc/apt/sources.list.d/openmodelica.list.bak \
    && apt update \
    && env DEBIAN_FRONTEND=noninteractive apt install -qy \
        tzdata \
    && apt install -qy \
        ca-certificates sudo \
        libssl-dev zlib1g-dev \
        libbz2-dev libreadline-dev libsqlite3-dev curl \
        libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev \
    && apt clean \
    && rm -rf /var/lib/apt/lists/* \
    && mv /etc/apt/sources.list.d/openmodelica.list.bak /etc/apt/sources.list.d/openmodelica.list

COPY --from=0 /usr/local /usr/local
