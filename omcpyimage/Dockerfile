
ARG OPENMODELICA_IMAGE

FROM ${OPENMODELICA_IMAGE}

LABEL maintainer "ijknabla <ijknabla@gmail.com>"

RUN apt-get update \
    && apt-get upgrade -qy \
    && apt-get dist-upgrade -qy \
    && apt-get install -qy sudo \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m user
