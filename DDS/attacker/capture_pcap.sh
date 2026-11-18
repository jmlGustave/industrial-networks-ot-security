#!/usr/bin/env bash


set -e
source /opt/ros/humble/setup.bash

MODE="${1:-normal}"
DURATION="${2:-15}"
OUT_DIR="/pcaps"
mkdir -p "${OUT_DIR}"

if [ "${MODE}" = "normal" ]; then
    PCAP_FILE="${OUT_DIR}/01_dds_normal_traffic.pcapng"
    echo "[CAPTURA] Grabando tráfico DDS/RTPS normal durante ${DURATION}s en ${PCAP_FILE}..."
    # Suscripción pasiva en segundo plano para forzar envío RTPS DATA hacia este nodo además de multicast SPDP
    ros2 topic echo /inspection/piece_status > /dev/null 2>&1 &
    ECHO_PID=$!
    tcpdump -i eth0 -nn -w "${PCAP_FILE}" "udp" &
    TCPDUMP_PID=$!
    sleep "${DURATION}"
    kill -INT "${TCPDUMP_PID}" 2>/dev/null || true
    kill "${ECHO_PID}" 2>/dev/null || true
    wait "${TCPDUMP_PID}" 2>/dev/null || true
    echo "[OK] Captura guardada en ${PCAP_FILE}"
elif [ "${MODE}" = "attack" ]; then
    PCAP_FILE="${OUT_DIR}/02_dds_attack_traffic.pcapng"
    echo "[CAPTURA] Grabando tráfico DDS/RTPS con ATAQUE (T0861 + T0836) en ${PCAP_FILE}..."
    ros2 topic echo /inspection/piece_status > /dev/null 2>&1 &
    ECHO_PID=$!
    tcpdump -i eth0 -nn -w "${PCAP_FILE}" "udp" &
    TCPDUMP_PID=$!
    sleep 3
    bash /app/attacker/discover_and_sniff.sh
    sleep 4
    kill -INT "${TCPDUMP_PID}" 2>/dev/null || true
    kill "${ECHO_PID}" 2>/dev/null || true
    wait "${TCPDUMP_PID}" 2>/dev/null || true
    echo "[OK] Captura de ataque guardada en ${PCAP_FILE}"
else
    echo "Uso: $0 [normal|attack] [segundos]"
    exit 1
fi
