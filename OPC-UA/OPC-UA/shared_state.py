import threading
#Crea el diccionario que compartirán los 3 hilos
shared_data = {
    "counter": 0,
    "random": 0.0,
    "senoidal": 0.0
}
data_lock = threading.Lock()