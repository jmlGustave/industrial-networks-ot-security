import socket
import json
from config import UDP_IP, UDP_PORT
from shared_state import shared_data, data_lock # Importar monitor

def run_udp_thread():
    target_address = (UDP_IP, UDP_PORT)
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print(f"Puente UDP (Consumidor) esperando en {UDP_IP}:{UDP_PORT}")

    try:
        while True:
            # ZONA CRÍTICA: Esperar señal y leer
            with data_lock:
                valor_c = shared_data["counter"]
                valor_r = shared_data["random"]

            # Procesamiento fuera del bloqueo (Eficiencia Nivel 2)
            payload = {"counter": valor_c, "random": valor_r}
            json_string = json.dumps(payload)
            data_bytes = json_string.encode('utf-8')
            udp_socket.sendto(data_bytes, target_address)
            
            print(f"UDP Enviado (Sincronizado): {json_string}")

    except Exception as e:
        print(f"\nError Puente UDP: {e}")
    finally:
        udp_socket.close()
# Prueba        
if __name__ == "__main__":
    print("Iniciando puente UDP en modo de prueba")