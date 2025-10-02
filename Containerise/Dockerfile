FROM ubuntu:jammy

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
  && apt-get install -y python3-pip libpq-dev python3-dev libmysqlclient-dev python3-requests \
    git wget bzip2 curl unzip \
    build-essential unixodbc unixodbc-dev pkg-config

RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh && \
    bash miniconda.sh -b -p /opt/conda && \
    rm miniconda.sh

ENV PATH=/opt/conda/bin:$PATH

RUN conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main && \
    conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r

COPY environment.yml /tmp/environment.yml
RUN conda env create -f /tmp/environment.yml && conda clean -afy

RUN mkdir /home/repliq

ADD ../. /home/repliq/

WORKDIR /home/repliq

EXPOSE 8888/tcp

ENV MLFLOW_TRACKING_URI="http://127.0.0.1:5000"

ENTRYPOINT ["conda", "run", "-n", "ml_env", "/bin/bash", "-c"]