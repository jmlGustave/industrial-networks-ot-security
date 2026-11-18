FROM ros:humble-ros-core

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    tcpdump \
    tshark \
    iproute2 \
    iputils-ping \
    net-tools \
    openssl \
    python3-cryptography \
    python3-lxml \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app


COPY config/ /app/config/
COPY nodes/ /app/nodes/
COPY attacker/ /app/attacker/
COPY security/ /app/security/

RUN chmod +x /app/attacker/*.sh /app/security/*.sh || true

ENV RMW_IMPLEMENTATION=rmw_fastrtps_cpp
ENV FASTRTPS_DEFAULT_PROFILES_FILE=/app/config/fastdds_udp_only.xml
ENV ROS_DOMAIN_ID=0
ENV PYTHONUNBUFFERED=1
