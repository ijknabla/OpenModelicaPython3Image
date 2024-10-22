FROM ubuntu:22.04 AS openmodelica-v1.24.0-build

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
COPY omc_patch.py /
RUN \
    apt update \
    && apt install -y git \
    && git clone --recursive -b v1.24.0 https://github.com/OpenModelica/OpenModelica.git source \
    && find source -type f -name '*.mo' | xargs python3 /omc_patch.py
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


FROM ubuntu:22.04 AS python-3.12.7-build

SHELL ["/bin/bash", "-c"]
ENV DEBIAN_FRONTEND=noninteractive
RUN \
    apt-get update \
    && apt-get install -y \
    build-essential libssl-dev zlib1g-dev \
    libbz2-dev libreadline-dev libsqlite3-dev curl git \
    libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev
RUN \
    curl -fsSL https://www.python.org/ftp/python/3.12.7/Python-3.12.7.tgz | tar zxf - \
    && pushd /Python-3.12.7 \
    && ./configure --enable-optimizations --without-static-libpython --prefix /build/install \
    && make -j4 \
    && make install \
    && popd
RUN \
    mkdir -p /artifact/usr


FROM ubuntu:22.04

COPY --from=openmodelica-v1.24.0-build /artifact/usr/ /usr/
COPY --from=python-3.12.7-build        /artifact/usr/ /usr/
ENV DEBIAN_FRONTEND=noninteractive
RUN \
    apt update \
    && apt install -y \
    make clang libgfortran-12-dev libcurl4 libblas-dev liblapack-dev \
    libssl3 zlib1g \
    libbz2-1.0 libreadline8 libsqlite3-0 git \
    libncursesw6 tk libxml2 libxmlsec1 libffi8 liblzma5
