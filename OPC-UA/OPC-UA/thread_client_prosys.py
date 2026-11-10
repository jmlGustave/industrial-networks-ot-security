import asyncio
from asyncua import Client  
import logging 
import time 

from config import PROSYS_URL
from shared_state import shared_data, data_lock
from config import PROSYS_URL, SAMPLE_RATE_SEC

async def client_logic_async():
    # Configura la URL del servidor Prosys
    url = PROSYS_URL
    # Inicia el cliente
    async with Client(url=url) as cliente:    
    # Busca los nodos que necesitas
        nodo_counter = cliente.get_node("ns=3;i=1001")
        nodo_random = cliente.get_node("ns=3;i=1002")
        nodo_senoidal = cliente.get_node("ns=3;i=1003")
        # Bucle infinito para leer datos
        while True:
            # Lee los valores de los nodos
            val_c = await nodo_counter.read_value()
            val_r = await nodo_random.read_value()
            val_s = await nodo_senoidal.read_value() 
            with data_lock: 
                shared_data["counter"] = val_c
                shared_data["random"] = val_r
                shared_data["senoidal"] = val_s
            # Depuracion
            print(f"LEIDO: {val_c}, {val_r}, {val_s}")
            # Tecnica de sobre muestreo
            await asyncio.sleep(SAMPLE_RATE_SEC * 0.8)
# Función de Arranque 
def run_client_thread():
    logging.basicConfig(level=logging.WARNING)
    # Capturar de errores de conexión
    try:
        asyncio.run(client_logic_async())
    except Exception as e:
        print(f"Error en el cliente: {e}")
    except KeyboardInterrupt:
        print("Cliente detenido.")
# Bloque de Prueba 
if __name__ == "__main__":
    print("Iniciando cliente en modo de prueba")
    run_client_thread()