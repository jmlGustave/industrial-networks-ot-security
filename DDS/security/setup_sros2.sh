#!/usr/bin/env bash
# Genera la infraestructura PKI (Certificados X.509, Governance y Permissions S/MIME)
# para DDS Security (OMG DDS-SECURITY v1.1) mediante SROS2.
set -e

source /opt/ros/humble/setup.bash

KEYSTORE_DIR="/keystore"

if [ -f "${KEYSTORE_DIR}/enclaves/camera_inspector/cert.pem" ] && [ -f "${KEYSTORE_DIR}/enclaves/robot_controller/cert.pem" ]; then
    echo "[SROS2] Keystore X.509 ya existe en ${KEYSTORE_DIR}."
    exit 0
fi

echo "[SROS2] Creando Keystore CA (Autoridad de Certificación X.509) en ${KEYSTORE_DIR}..."
rm -rf "${KEYSTORE_DIR:?}"/*
ros2 security create_keystore "${KEYSTORE_DIR}"

echo "[SROS2] Generando certificado X.509 y permisos firmados para /camera_inspector..."
ros2 security create_enclave "${KEYSTORE_DIR}" /camera_inspector

echo "[SROS2] Generando certificado X.509 y permisos firmados para /robot_controller..."
ros2 security create_enclave "${KEYSTORE_DIR}" /robot_controller

echo "[SROS2] Keystore DDS Security generado correctamente (el nodo atacante NO tiene certificado)."
