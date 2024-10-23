ARG OM_MAJOR
ARG OM_MINOR
ARG OM_PATCH
ARG PY_MAJOR
ARG PY_MINOR
ARG PY_PATCH


FROM ubuntu:22.04 AS openmodelica

ARG OM_MAJOR
ARG OM_MINOR
ARG OM_PATCH
ENV VERSION=${OM_MAJOR}.${OM_MINOR}.${OM_PATCH}

# https://github.com/OpenModelica/OpenModelica/blob/master/OMCompiler/README.Linux.md#11-debianubuntu
RUN \
    apt-get update \
    && apt-get install -y ca-certificates curl gnupg lsb-release \
    && curl -fsSL http://build.openmodelica.org/apt/openmodelica.asc | gpg --dearmor -o /usr/share/keyrings/openmodelica-keyring.gpg \
    && for deb in deb deb-src; do echo \
    "$deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/openmodelica-keyring.gpg] https://build.openmodelica.org/apt $(lsb_release -cs) release" \
    >> /etc/apt/sources.list.d/openmodelica.list; done
RUN \
    apt update \
    && apt build-dep -y openmodelica
RUN \
    apt update \
    && apt install -y git \
    && git clone --recursive -b v${VERSION} https://github.com/OpenModelica/OpenModelica.git source \
    && find source/OMCompiler/ -name '*.mo' | xargs sed -i 's/System\.userIsRoot()/false/g'
RUN \
    cmake -S source -B build \
    -DOM_USE_CCACHE=OFF -DCMAKE_BUILD_TYPE=MinSizeRel \
    -DOM_ENABLE_GUI_CLIENTS=OFF -DOM_OMC_ENABLE_CPP_RUNTIME=OFF \
    -DCMINPACK_BUILD_SHARED_LIBS=ON \
    -DCMAKE_INSTALL_PREFIX=/build/install \
    && make -C build -j4 install
RUN \
    mkdir /artifact \
    && cp -r /build/install /artifact/usr


FROM ubuntu:22.04 AS python

ARG PY_MAJOR
ARG PY_MINOR
ARG PY_PATCH
ENV VERSION=${PY_MAJOR}.${PY_MINOR}.${PY_PATCH}
ENV DEBIAN_FRONTEND=noninteractive

RUN \
    apt-get update \
    && apt-get install -y \
    build-essential libssl-dev zlib1g-dev \
    libbz2-dev libreadline-dev libsqlite3-dev curl git \
    libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev
RUN \
    mkdir /source \
    && curl -fsSL https://www.python.org/ftp/python/${VERSION}/Python-${VERSION}.tgz | tar zxf - -C/source --strip-components=1 \
    && cd /source \
    && ./configure --enable-optimizations --without-static-libpython --prefix /build/install \
    && make -j4 \
    && make install
RUN \
    mkdir /artifact \
    && cp -r /build/install /artifact/usr \
    && find /artifact/ -type l | xargs rm
