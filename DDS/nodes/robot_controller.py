#!/usr/bin/env python3
import json
from datetime import datetime, timezone

import rclpy
from rcl_interfaces.msg import SetParametersResult
from rclpy.node import Node
from std_msgs.msg import String


class RobotControllerNode(Node):
    def __init__(self):
        super().__init__("robot_controller")

        # Parámetros operativos del controlador (vulnerables a T0836 Modify Parameter si no hay SROS2)
        self.declare_parameter("controller_id", "ROBOT-ARM-CELL-01")
        self.declare_parameter("max_tolerance_mm", 0.50)
        self.declare_parameter("arm_speed_pct", 80)
        self.declare_parameter("force_accept_all", False)

        self.add_on_set_parameters_callback(self.on_parameter_changed)

        self.subscription = self.create_subscription(
            String,
            "/inspection/piece_status",
            self.on_inspection_message,
            10,
        )
        self.telemetry_pub = self.create_publisher(String, "/robot/actuator_status", 10)

        self.accepted_count = 0
        self.rejected_count = 0

        self.get_logger().info(
            "=== CONTROLADOR DE BRAZO ROBÓTICO INICIADO (Suscrito a /inspection/piece_status) ==="
        )

    def on_parameter_changed(self, params):
        for param in params:
            self.get_logger().warning(
                f"[CAMBIO DE PARÁMETRO DDS] '{param.name}' modificado remotamente a: {param.value}"
            )
        return SetParametersResult(successful=True)

    def on_inspection_message(self, msg: String):
        try:
            data = json.loads(msg.data)
        except json.JSONDecodeError:
            self.get_logger().error(f"Payload JSON inválido recibido: {msg.data}")
            return

        piece_id = data.get("piece_id", "UNKNOWN")
        source_node = data.get("source_node", "UNKNOWN")
        quality_status = data.get("quality_status", "UNKNOWN")
        defect_mm = float(data.get("defect_mm", 0.0))

        max_tolerance = float(self.get_parameter("max_tolerance_mm").value)
        arm_speed = int(self.get_parameter("arm_speed_pct").value)
        force_accept = bool(self.get_parameter("force_accept_all").value)

        # Lógica de decisión del controlador del brazo robótico
        if force_accept:
            executed_action = "PALLETIZE_FORCED"
            self.accepted_count += 1
            self.get_logger().warning(
                f"⚠️ [MODO FORZADO ACTIVO] Pieza {piece_id} (defecto={defect_mm}mm) "
                f"ACEPTADA Y PALETIZADA por override de parámetro!"
            )
        elif quality_status == "OK" and defect_mm <= max_tolerance:
            executed_action = "PALLETIZE_OK"
            self.accepted_count += 1
            self.get_logger().info(
                f"✅ [ROBOT -> PALÉ] Pieza {piece_id} de {source_node} válida "
                f"({defect_mm:.2f}mm <= {max_tolerance:.2f}mm) | Vel={arm_speed}% | "
                f"Total OK={self.accepted_count}, NOK={self.rejected_count}"
            )
        else:
            executed_action = "DIVERT_TO_REJECT"
            self.rejected_count += 1
            self.get_logger().info(
                f"❌ [ROBOT -> RECHAZO] Pieza {piece_id} DEFECTUOSA ({defect_mm:.2f}mm) "
                f"desviada a contenedor de descarte | "
                f"Total OK={self.accepted_count}, NOK={self.rejected_count}"
            )

        # Publicar estado de actuación del robot por DDS
        telemetry = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "controller_id": str(self.get_parameter("controller_id").value),
            "piece_id": piece_id,
            "reported_by": source_node,
            "defect_mm": defect_mm,
            "active_tolerance_mm": max_tolerance,
            "arm_speed_pct": arm_speed,
            "executed_action": executed_action,
            "totals": {
                "accepted": self.accepted_count,
                "rejected": self.rejected_count,
            },
        }
        out_msg = String()
        out_msg.data = json.dumps(telemetry)
        self.telemetry_pub.publish(out_msg)


def main(args=None):
    rclpy.init(args=args)
    node = RobotControllerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
