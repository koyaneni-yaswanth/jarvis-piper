FROM ubuntu:26.04

ENV DEBIAN_FRONTEND=noninteractive
ENV ROS_DISTRO=lyrical

# Install base dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    python3-pip \
    python3-dev \
    python3-numpy \
    python3-yaml \
    libopencv-dev \
    python3-opencv \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY pyproject.toml /workspace/
COPY python/ /workspace/python/
COPY configs/ /workspace/configs/
COPY scripts/ /workspace/scripts/
COPY docker/entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh /workspace/scripts/*.sh && \
    pip3 install --no-cache-dir --break-system-packages -e .

ENTRYPOINT ["/entrypoint.sh"]
CMD ["jarvis-piper", "doctor"]
