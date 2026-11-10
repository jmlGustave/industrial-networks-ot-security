import asyncio
from asyncua import Server  
import logging

from config import PYTHON_SERVER_URL, SAMPLE_RATE_SEC
from shared_state import shared_data, data_lock
async def server_logic_async():
    # Inicializa el objeto Servidor
    server =Server()
    await server.init()
    await asyncio.sleep(5.0)   
    # Configura el endpoint (la URL)
    server.set_endpoint(PYTHON_SERVER_URL)
    # Configura el espacio de nombres
    uri = "http://localhost/MiPuenteNamespace"
    idx = await server.register_namespace(uri)
    # Crea un objeto carpeta las variables 
    mi_objeto = await server.nodes.objects.add_object(idx, "MiPuenteObjeto")
    # Añade la variable Senoidal que Ignition leerá
    var_senoidal = await mi_objeto.add_variable(idx,"Senoidal", 0.0)
    await var_senoidal.set_writable()
    # Inicia el servidor
    async with server:
        while True:
            # Adquiere el semáforo para leer de forma segura
            with data_lock:
                valor_actual = shared_data["senoidal"]
            # Escribe el valor en la variable Senoidal
            await var_senoidal.write_value(valor_actual)
            # Depurar
            print(f"Servidor: valor 'Senoidal' actualizado a {valor_actual}")
            await asyncio.sleep(SAMPLE_RATE_SEC)

# Función de Arranque 
def run_server_thread():
    logging.basicConfig(level=logging.INFO)
    # Ejecuta el bucle de eventos asíncrono
    try:
        asyncio.run(server_logic_async())
    except:
        print("\nServidor detenido.")

# Prueba
if __name__ == "__main__":
    print(f"Iniciando servidor en {PYTHON_SERVER_URL}")
    run_server_thread()