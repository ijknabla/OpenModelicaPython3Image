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
    apt update \
    && apt install -y --no-install-recommends \
    git ca-certificates \
    autoconf cmake make \
    gcc g++ gfortran-11 default-jre \
    libcurl4-openssl-dev uuid-dev libexpat1-dev \
    libblas-dev liblapack-dev \
    && git clone --recursive -b v${VERSION} https://github.com/OpenModelica/OpenModelica.git source \
    && find source/OMCompiler/ -name '*.mo' | xargs sed -i 's/System\.userIsRoot()/false/g' \
    && cmake -S source -B build \
    -DOM_USE_CCACHE=OFF -DCMAKE_BUILD_TYPE=MinSizeRel \
    -DCMAKE_Fortran_COMPILER=gfortran-11 \
    -DOM_ENABLE_GUI_CLIENTS=OFF -DOM_OMC_ENABLE_CPP_RUNTIME=OFF \
    -DCMINPACK_BUILD_SHARED_LIBS=ON \
    -DCMAKE_INSTALL_PREFIX=/artifact/usr/ \
    && make -C build -j4 install \
    && rm -rf source build \
    && apt purge -y \
    git ca-certificates \
    autoconf cmake make \
    gcc g++ gfortran-11 default-jre \
    libcurl4-openssl-dev uuid-dev libexpat1-dev \
    libblas-dev liblapack-dev \
    && rm -rf /var/lib/apt/lists/*


FROM ubuntu:22.04 AS python

ARG PY_MAJOR
ARG PY_MINOR
ARG PY_PATCH
ENV VERSION=${PY_MAJOR}.${PY_MINOR}.${PY_PATCH}
ENV DEBIAN_FRONTEND=noninteractive

RUN \
    apt update \
    && apt install -y --no-install-recommends \
    ca-certificates clang \
    libssl-dev zlib1g-dev \
    libbz2-dev libreadline-dev libsqlite3-dev curl git \
    libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev \
    && mkdir /source \
    && curl -fsSL https://www.python.org/ftp/python/${VERSION}/Python-${VERSION}.tgz | tar zxf - -C/source --strip-components=1 \
    && cd /source \
    && ./configure --enable-optimizations --without-static-libpython --prefix /artifact/usr \
    && make -j4 \
    && make install \
    && rm -rf /source \
    && find /artifact/usr -type l | xargs rm \
    && apt purge -y \
    ca-certificates clang \
    libssl-dev zlib1g-dev \
    libbz2-dev libreadline-dev libsqlite3-dev curl git \
    libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev \
    && rm -rf /var/lib/apt/lists/*


FROM ubuntu:22.04 AS final

ARG PY_MAJOR
ARG PY_MINOR
ENV PY_SHORT_VERSION=${PY_MAJOR}.${PY_MINOR}
ENV DEBIAN_FRONTEND=noninteractive

COPY --from=python /artifact/usr/ /usr/
RUN \
    apt update \
    && apt install -y --no-install-recommends \
    ca-certificates \
    make gcc g++ \
    libgfortran-11-dev \
    libcurl4 libblas-dev liblapack-dev \
    libssl3 zlib1g \
    libbz2-1.0 libreadline8 libsqlite3-0 git \
    libncursesw6 tk libxml2 libxmlsec1 libffi8 liblzma5 \
    && if which 2to3-${PY_SHORT_VERSION} > /dev/null; \
        then update-alternatives --install /usr/bin/2to3   2to3   /usr/bin/2to3-${PY_SHORT_VERSION}  10; fi \
    &&       update-alternatives --install /usr/bin/idle   idle   /usr/bin/idle${PY_SHORT_VERSION}   10  \
    &&       update-alternatives --install /usr/bin/pip    pip    /usr/bin/pip${PY_SHORT_VERSION}    10  \
    &&       update-alternatives --install /usr/bin/pydoc  pydoc  /usr/bin/pydoc${PY_SHORT_VERSION}  10  \
    &&       update-alternatives --install /usr/bin/python python /usr/bin/python${PY_SHORT_VERSION} 10  \
    && ln -s / /artifact \
    && rm -rf /var/lib/apt/lists/*
COPY --from=openmodelica /artifact/usr/ /usr/
