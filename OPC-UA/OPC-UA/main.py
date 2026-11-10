import threading 
import time      
from thread_client_prosys import run_client_thread
from thread_server_python import run_server_thread
from thread_bridge_udp import run_udp_thread

if __name__ == "__main__":
    
    print("Iniciando aplicacion")

    # Crea los 3 objetos Hilo

    t1 = threading.Thread(target=run_client_thread, name="ClienteProsys", daemon = True)
    t2 = threading.Thread(target=run_server_thread, name="ServidorPython", daemon = True)
    t3 = threading.Thread(target=run_udp_thread, name="PuenteUDP", daemon = True)

    # Inicia los hilos

    t1.start()
    t2.start()
    t3.start()
    
    print("Hilos iniciados.")
    
    # Bucle infinito para mantener vivo el hilo principal
    try:
        while True:
            print(f"El estado activo de los hilos es: {threading.active_count()}")
            time.sleep(5.0)
    except KeyboardInterrupt:
        print("Cerrando la aplicacion")