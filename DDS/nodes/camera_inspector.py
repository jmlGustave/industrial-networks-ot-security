#!/usr/bin/env python3
"""
Nodo Industrial 1: Cámara de Inspección por Visión Artificial (camera_inspector)
IP en red OT: 172.28.0.10
Protocolo: DDS / RTPS (ROS 2 Humble - eProsima Fast-DDS sobre UDPv4)

Función en planta:
Inspecciona dimensionalmente las piezas metálicas que avanzan por la cinta
transportadora hacia la celda robótica de paletizado y publica el resultado
en tiempo real en el topic DDS `/inspection/piece_status`.
"""

import json
import time
from datetime import datetime, timezone

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class CameraInspectorNode(Node):
    def __init__(self):
        super().__init__("camera_inspector")

        # Parámetros de proceso expuestos por DDS (servicios de parámetros ROS 2)
        self.declare_parameter("inspector_id", "CAM-VISION-01")
        self.declare_parameter("max_tolerance_mm", 0.50)
        self.declare_parameter("inspection_period_sec", 3.0)

        self.publisher_ = self.create_publisher(String, "/inspection/piece_status", 10)
        self.piece_counter = 1000

        period = self.get_parameter("inspection_period_sec").value
        self.timer = self.create_timer(period, self.inspect_next_piece)

        self.get_logger().info(
            "=== CÁMARA DE VISIÓN ARTIFICIAL INICIADA (Topic: /inspection/piece_status) ==="
        )

    def inspect_next_piece(self):
        self.piece_counter += 1
        piece_id = f"P-{self.piece_counter}"
        tolerance = float(self.get_parameter("max_tolerance_mm").value)
        inspector_id = str(self.get_parameter("inspector_id").value)

        # Cada 3ª pieza simulamos un defecto crítico de fabricación (fisura / desviación 2.45 mm)
        if self.piece_counter % 3 == 0:
            defect_mm = 2.45
            defect_type = "SURFACE_CRACK"
        else:
            defect_mm = 0.12
            defect_type = "NONE"

        is_ok = defect_mm <= tolerance
        quality_status = "OK" if is_ok else "DEFECTIVE"
        action = "PALLETIZE" if is_ok else "REJECT_BIN"

        payload = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source_node": inspector_id,
            "piece_id": piece_id,
            "quality_status": quality_status,
            "defect_mm": defect_mm,
            "tolerance_mm": tolerance,
            "defect_type": defect_type,
            "recommended_action": action,
        }

        msg = String()
        msg.data = json.dumps(payload)
        self.publisher_.publish(msg)

        self.get_logger().info(
            f"[INSPECCIÓN] Pieza={piece_id} | Estado={quality_status} "
            f"(defecto={defect_mm:.2f}mm, máx={tolerance:.2f}mm) -> {action}"
        )


def main(args=None):
    rclpy.init(args=args)
    node = CameraInspectorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
