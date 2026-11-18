# TRABAJO EN GRUPO (TG): ANÁLISIS DE CIBERSEGURIDAD DE COMUNICACIONES INDUSTRIALES
## Evaluación de Seguridad del Protocolo DDS / RTPS (ROS 2) en una Celda Robotizada de Inspección por Visión Artificial

**Titulación:** Grado en Ingeniería Informática Industrial y Robótica (GIIROB) — ETSINF, Universitat Politècnica de València (UPV)  
**Asignatura:** Ciberseguridad Industrial — Curso 2026/27  
**Profesor:** José Vera Pérez  

---

## 1. Descripción del Escenario Industrial (Apartado 4.1)

### 1.1 Contexto del proceso industrial y aplicación en planta real
En la industria manufacturera moderna (automoción, aeroespacial y metalmecánica), el control de calidad dimensional al final de línea se realiza mediante **celdas robotizadas guiadas por visión artificial**. A diferencia de la telemetría lenta hacia la nube (donde predominan protocolos con broker central en TCP como MQTT), la comunicación en tiempo real entre cámaras industriales inteligentes, sensores LiDAR, controladores de brazos robóticos y vehículos de guiado automático (AGVs/AMRs) exige **baja latencia determinista, alto ancho de banda y topología distribuida sin punto único de fallo**.

Por este motivo, el estándar industrial adoptado por **ROS 2 (Robot Operating System 2)** y sistemas críticos de control es **DDS (*Data Distribution Service*)**, estandarizado por el Object Management Group (OMG), que opera sobre el protocolo de transporte **RTPS (*Real-Time Publish-Subscribe*)** directamente sobre **UDP/IP**.

El escenario industrial desplegado reproduce una **celda de inspección dimensional y clasificación robotizada**:

1. Las piezas metálicas mecanizadas (`P-1001`, `P-1002`, ...) avanzan por una cinta transportadora y pasan bajo una **cámara inteligente de visión artificial** (`camera_inspector`), que mide la desviación dimensional o presencia de fisuras superficiales (`defect_mm`) respecto a una tolerancia máxima admisible (`0.50 mm`).
2. La cámara publica en tiempo real el dictamen de cada pieza (`OK` o `DEFECTIVE`) en el bus de datos DDS.
3. El **controlador del brazo robótico clasificador** (`robot_controller`) recibe el mensaje DDS y acciona físicamente el robot hacia uno de dos destinos:
   - **Paletizado (`PALLETIZE_OK`)**: si la pieza cumple la tolerancia (`defect_mm <= max_tolerance_mm`), se deposita en el palé de expedición al cliente.
   - **Contenedor de rechazo (`DIVERT_TO_REJECT`)**: si presenta una fisura o desviación (`defect_mm > max_tolerance_mm`, p. ej. `2.45 mm`), el brazo la desvía a la tolva de descarte (*scrap*).

### 1.2 Dispositivos y aplicaciones participantes
El escenario se ha virtualizado mediante tres contenedores Docker interconectados en una red industrial aislada de Nivel 1/2 del modelo Purdue (`ot_dds_net`, subred `172.28.0.0/24`):

| Contenedor | IP Red OT | Rol en Planta Industrial | Función Técnica en el Escenario DDS |
| :--- | :--- | :--- | :--- |
| `dds_camera_inspector` | `172.28.0.10` | Cámara de Visión (`CAM-VISION-01`) | Nodo publicador DDS (*DataWriter*) que inspecciona una pieza cada 3 s y publica el JSON en el topic `/inspection/piece_status`. |
| `dds_robot_controller` | `172.28.0.20` | Controlador Robot (`ROBOT-ARM-CELL-01`) | Nodo suscriptor DDS (*DataReader*) de `/inspection/piece_status`, servidor de parámetros y publicador en `/robot/actuator_status`. |
| `dds_attacker` | `172.28.0.99` | Equipo intruso en planta | Nodo infiltrado en la subred OT con `tcpdump`/`tshark` y scripts de reconocimiento e inyección DDS/ROS 2. |

### 1.3 Características principales del protocolo DDS / RTPS

* **Modelo Data-Centric Publish-Subscribe (DCPS) sin broker central**: Los nodos (*DomainParticipants*) se comunican directamente *peer-to-peer* dentro de un dominio lógico (`ROS_DOMAIN_ID = 0`). No existe un servidor central como en MQTT.
* **Protocolo de cable RTPS v2.3 (OMG) sobre UDPv4**: Implementado mediante **eProsima Fast-DDS** (`VendorId = 0x010F`). Utiliza serialización binaria **CDR (*Common Data Representation*)** y se apoya en dos subprotocolos automáticos de descubrimiento:
  1. **SPDP (*Simple Participant Discovery Protocol*)**: Cada nodo anuncia periódicamente su identidad (`GUIDPrefix`) y sus direcciones/puertos (*Locators*) enviando paquetes RTPS `DATA(p)` al grupo **UDP Multicast `239.255.0.1:7400`**.
  2. **SEDP (*Simple Endpoint Discovery Protocol*)**: Una vez descubiertos los participantes, intercambian por **UDP Unicast (puerto `7410`)** mensajes `DATA(w)` (*DataWriters*) y `DATA(r)` (*DataReaders*) informando de todos los *topics*, tipos de datos y políticas de calidad de servicio (*QoS*), acompañados de submensajes de fiabilidad `HEARTBEAT` y `ACKNACK`.
* **Transferencia de datos y servicios RPC sobre DDS**: Los datos de proceso viajan en submensajes RTPS `DATA` al puerto **UDP Unicast `7411`**, mientras que los servicios de lectura y modificación de parámetros de ROS 2 se mapean sobre pares de topics DDS de petición/respuesta (`rq/<nodo>/<servicio>Request` y `rr/<nodo>/<servicio>Reply`).

### 1.4 Variables de proceso y operaciones realizadas

| Variable / Parámetro | Canal DDS | Tipo / Valor | Significado en el Proceso | Consecuencia de Manipulación |
| :--- | :--- | :--- | :--- | :--- |
| `piece_id` | Topic `piece_status` | `String` (`P-1001`) | Identificador único de trazabilidad de la pieza. | Pérdida de trazabilidad o inserción de piezas fantasma. |
| `quality_status` | Topic `piece_status` | `String` (`OK`/`DEFECTIVE`) | Dictamen de calidad emitido por la cámara. | Si se fuerza a `OK`, el robot paletiza piezas rotas. |
| `defect_mm` | Topic `piece_status` | `Float` (`0.12` / `2.45 mm`) | Desviación dimensional o fisura medida en la pieza. | Ocultación de defectos críticos (`SURFACE_CRACK`). |
| `max_tolerance_mm` | Parámetro del robot | `Double` (`0.50 mm`) | Umbral máximo de defecto admitido por el robot. | Subirlo a `10.0 mm` anula el filtro de calidad del robot. |
| `arm_speed_pct` | Parámetro del robot | `Integer` (`80 %`) | Velocidad operativa del brazo robótico clasificador. | Forzarlo al `100 %` acelera la fatiga y el riesgo físico. |
| `executed_action` | Topic `actuator_status` | `String` | Acción física ejecutada por el brazo robótico. | Falsificación del estado reportado a supervisión/MES. |

**Esquema de arquitectura y flujos de comunicación DDS/RTPS:**

```text
+-------------------------------------------------------------------------------+
|                      RED INDUSTRIAL OT: 172.28.0.0/24                         |
|                Dominio DDS: ROS_DOMAIN_ID = 0 (RTPS v2.3 / UDPv4)             |
|                                                                               |
|  +-------------------------+                     +-------------------------+  |
|  |  dds_camera_inspector   |                     |  dds_robot_controller   |  |
|  |      172.28.0.10        |                     |      172.28.0.20        |  |
|  |    (CAM-VISION-01)      |                     |  (ROBOT-ARM-CELL-01)    |  |
|  +------------+------------+                     +------------+------------+  |
|               |                                               ^               |
|               | 1. Autodescubrimiento SPDP Multicast          |               |
|               +--------> 239.255.0.1 : UDP 7400 <-------------+               |
|               |                                               |               |
|               | 2. Descubrimiento de Endpoints SEDP (DATA w/r)|               |
|               +<=======> Unicast UDP 7410 <==================>|               |
|               |                                               |               |
|               | 3. Publicación de Inspección (RTPS DATA)      |               |
|               |    Topic: rt/inspection/piece_status          |               |
|               +--------> Unicast UDP 7411 ------------------->|               |
|                                                               ^               |
|  +-------------------------+                                  |               |
|  |      dds_attacker       | 4. Sniffing (T0842) y Tags(T0861)|               |
|  |      172.28.0.99        | 5. Modificar Parámetros (T0836)  |               |
|  | (rogue_maintenance_tool)| 6. Inyección Piezas Falsas (DATA)|               |
|  +-------------------------+----------------------------------+               |
+-------------------------------------------------------------------------------+
```

---

## 2. Despliegue y Análisis del Tráfico de Red (Apartado 4.2)

### 2.1 Despliegue del entorno mediante Docker Compose
El entorno se despliega con `docker compose up --build -d` a partir del archivo `compose.yml`. Para garantizar que la totalidad del tráfico DDS entre contenedores viaje por la pila de red UDP/IP y sea íntegramente auditable con Wireshark (evitando la optimización de memoria compartida *Shared Memory* de Fast-DDS), se ha configurado el perfil `config/fastdds_udp_only.xml` (`useBuiltinTransports=false`, transporte exclusivo `UDPv4`).

Se han generado y entregado dos capturas originales en la carpeta `pcaps/`:

1. **`01_dds_normal_traffic.pcapng`** (331 paquetes): Tráfico de operación nominal y autodescubrimiento RTPS.
2. **`02_dds_attack_traffic.pcapng`** (2036 paquetes): Tráfico durante la ejecución de las técnicas de reconocimiento, modificación remota de parámetros e inyección de piezas falsas.

### 2.2 Direcciones IP, puertos UDP y participantes RTPS identificados
De acuerdo con la especificación OMG RTPS v2.3, para el dominio `ROS_DOMAIN_ID = 0` (`PB = 7400`, `DG = 250`), los puertos UDP observados en las capturas responden exactamente al esquema estándar:

| IP | Participante | `GUIDPrefix` RTPS (12 B) | Puertos UDP | Función en el Protocolo RTPS |
| :--- | :--- | :--- | :--- | :--- |
| `239.255.0.1` | Grupo Multicast | N/A (Destino Multicast) | Destino **`7400`** | Descubrimiento global de participantes (`SPDP` - `DATA(p)`). |
| `172.28.0.10` | `camera_inspector` | `01:0f:f9:14:01:00` `93:d4:00:00:00:00` | Orig. `51973`/`33181` Dest. **`7410`, `7411`** | `7410`: Metatráfico Unicast (`SEDP`). `7411`: Tráfico de usuario (`DATA`). |
| `172.28.0.20` | `robot_controller` | `01:0f:3d:66:01:00` `d4:b6:00:00:00:00` | Orig. `39327` Dest. **`7410`, `7411`** | `7410`: Metatráfico Unicast (`SEDP`). `7411`: Recepción de topics y servicios. |
| `172.28.0.99` | `attacker` | `01:0f:15:18:75:00` `d5:bb:00:00:00:00` | Orig. `40367`/`40390` Dest. **`7410..7415`** | Escucha pasiva, consulta de parámetros y envío de paquetes inyectados. |

*(Nota: Los dos primeros bytes de cada `GUIDPrefix`, `01:0f`, corresponden al `VendorId` oficial asignado por el OMG a **eProsima Fast-DDS**).*

### 2.3 Análisis e interpretación de operaciones representativas en los PCAP

#### Operación 1: Autodescubrimiento de participantes (SPDP) y endpoints (SEDP)
En **`01_dds_normal_traffic.pcapng`** se observa cómo DDS expone automáticamente toda la topología de control sin requerir credenciales:

* **Paquetes `Frame #1`, `Frame #5` y `Frame #6`** (`UDP 239.255.0.1:7400`, `RTPS INFO_TS, DATA(p)`): La cámara (`172.28.0.10`), el robot (`172.28.0.20`) y el nodo en escucha (`172.28.0.99`) anuncian por multicast su `GUIDPrefix` y sus *unicast locators*.
* **Paquete `Frame #35`** (`172.28.0.10:51973 -> 172.28.0.99:7410`, longitud 1482 bytes): Mensaje `RTPS DATA(w)` (*SEDP DataWriter Announcement*) enviado por la cámara junto con submensajes de control `INFO_DST`, `INFO_TS`, `HEARTBEAT` (`Frame #8`) y confirmado mediante `ACKNACK` (`Frame #26`). En el payload CDR de este único paquete se leen en texto claro todos los canales publicados por la cámara (`rt/inspection/piece_status`, `rr/camera_inspector/get_parametersReply`, `rr/camera_inspector/set_parametersReply`, etc.).
* **Paquete `Frame #80`** (`172.28.0.20:39327 -> 172.28.0.99:7410`, longitud 678 bytes): Mensaje `RTPS DATA(r)` (*SEDP DataReader Announcement*) donde el controlador del brazo robótico anuncia públicamente que escucha comandos de modificación de parámetros en `rq/robot_controller/set_parametersRequest` y datos de visión en `rt/inspection/piece_status`.

#### Operación 2: Intercambio cíclico de variables de proceso (Pieza OK vs. Pieza Defectuosa)
En **`01_dds_normal_traffic.pcapng`** se capturan las publicaciones periódicas de la cámara (`172.28.0.10`) en el topic `rt/inspection/piece_status` (puerto destino UDP `7411`):

* **Paquete `Frame #281`** ($t = 1.725\text{ s}$, `172.28.0.10:51973 -> 172.28.0.99:7411`, 322 bytes): Submensaje `RTPS INFO_TS, DATA -> rt/inspection/piece_status`. El volcado hexadecimal/ASCII muestra la cabecera mágica `52 54 50 53 02 03 01 0f` (`RTPS v2.3`) seguida del payload CDR completamente en claro para la pieza válida **`P-1033`**:

```text
0060  00 00 00 01 00 00 d6 00 00 00 7b 22 74 69 6d 65   ..........{"time
0090  22 73 6f 75 72 63 65 5f 6e 6f 64 65 22 3a 20 22   "source_node": "
00a0  43 41 4d 2d 56 49 53 49 4f 4e 2d 30 31 22 2c 20   CAM-VISION-01", 
00b0  22 70 69 65 63 65 5f 69 64 22 3a 20 22 50 2d 31   "piece_id": "P-1
00c0  30 33 33 22 2c 20 22 71 75 61 6c 69 74 79 5f 73   033", "quality_s
00d0  74 61 74 75 73 22 3a 20 22 4f 4b 22 2c 20 22 64   tatus": "OK", "d
00e0  65 66 65 63 74 5f 6d 6d 22 3a 20 30 2e 31 32 2c   efect_mm": 0.12,
0120  63 6f 6d 6d 65 6e 64 65 64 5f 61 63 74 69 6f 6e   commended_action
0130  22 3a 20 22 50 41 4c 4c 45 54 49 5a 45 22 7d 00   ": "PALLETIZE"}.
```

* **Paquete `Frame #315`** ($t = 7.724\text{ s}$, `172.28.0.10:51973 -> 172.28.0.99:7411`, 338 bytes): Publicación de la pieza defectuosa **`P-1035`**, donde se observa en texto plano `"quality_status": "DEFECTIVE"`, `"defect_mm": 2.45`, `"defect_type": "SURFACE_CRACK"` y `"recommended_action": "REJECT_BIN"`.

#### Operación 3: Modificación remota de parámetros e inyección de datos falsos
En **`02_dds_attack_traffic.pcapng`** queda registrada la secuencia completa de manipulación activa desde `172.28.0.99`:

1. **Enumeración y lectura de parámetros del controlador (`Frames #402` y `#636`)**:
   * En **`Frame #402`** ($t = 4.473\text{ s}$, `172.28.0.20:39327 -> 172.28.0.99:7415`), el controlador responde con `DATA -> rr/robot_controller/list_parametersReply`, listando sus parámetros internos (`arm_speed_pct`, `controller_id`, `force_accept_all`, `max_tolerance_mm`).
   * En **`Frame #636`** ($t = 5.545\text{ s}$, `172.28.0.99:38796 -> 172.28.0.20:7411`), el atacante lanza `rq/robot_controller/get_parametersRequest` para leer el valor activo de `max_tolerance_mm` (`0.50 mm`).
2. **Modificación de parámetros críticos de proceso (`Frame #1235`)**:
   * En **`Frame #1235`** ($t = 7.265\text{ s}$, `172.28.0.99:40390 -> 172.28.0.20:7411`, 290 bytes), el atacante envía un paquete `RTPS INFO_DST, INFO_TS, DATA -> rq/robot_controller/set_parametersRequest`. En el volcado hexadecimal del paquete se identifican exactamente los dos parámetros sobrescritos en formato CDR:

```text
0090  00 00 00 01 00 00 02 00 00 00 11 00 00 00 6d 61   ..............ma
00a0  78 5f 74 6f 6c 65 72 61 6e 63 65 5f 6d 6d 00 03   x_tolerance_mm..
00c0  00 00 00 00 00 00 24 40 01 00 00 00 00 00 00 00   ......$@........
00e0  00 00 0e 00 00 00 61 72 6d 5f 73 70 65 65 64 5f   ......arm_speed_
00f0  70 63 74 00 02 00 64 00 00 00 00 00 00 00 00 00   pct...d.........
```

   * `max_tolerance_mm` (tipo `0x03` = `PARAMETER_DOUBLE`) recibe el valor IEEE-754 *little-endian* `00 00 00 00 00 00 24 40` (`0x4024000000000000` = **`10.0 mm`**).
   * `arm_speed_pct` (tipo `0x02` = `PARAMETER_INTEGER`) recibe el entero `0x64` (**`100 %`**).
3. **Inyección de lecturas de visión falsificadas (`Frames #1261`, `#1270` y `#1292`)**:
   * En **`Frame #1261`** ($t = 8.775\text{ s}$, `172.28.0.99:40390 -> 172.28.0.20:7411`, 342 bytes), el atacante publica directamente contra el controlador del robot un mensaje `RTPS DATA -> rt/inspection/piece_status` con `"source_node": "CAM-VISION-01"`, `"piece_id": "P-FAKE-901"`, `"quality_status": "OK"`, `"defect_mm": 0.05` y `"recommended_action": "PALLETIZE"`. El robot lo acepta como si procediera de la cámara legítima.

### 2.4 Ausencia de mecanismos de seguridad por defecto y comparativa con SROS2
El análisis de los paquetes demuestra que una instalación estándar de DDS / ROS 2 carece por defecto de mecanismos criptográficos activados:

1. **Ausencia de confidencialidad (sin cifrado)**: Tanto los nombres de topics/servicios como los valores de proceso (`defect_mm`, `quality_status`, `max_tolerance_mm`) viajan en texto claro dentro de los submensajes `DATA`.
2. **Ausencia de autenticación de origen**: El controlador (`172.28.0.20`) acepta cualquier paquete `DATA` dirigido a `rt/inspection/piece_status` o `rq/robot_controller/set_parametersRequest` sin verificar criptográficamente si el emisor es realmente `172.28.0.10` (`camera_inspector`) o el intruso `172.28.0.99`.
3. **Ausencia de integridad y control de acceso**: Cualquier participante que se una al `ROS_DOMAIN_ID = 0` recibe el catálogo completo de endpoints por `SPDP`/`SEDP` y puede publicar o modificar parámetros.

*(En el repositorio se incluye adicionalmente `compose.secure.yml` y `security/setup_sros2.sh`, que activan el estándar **OMG DDS-SECURITY v1.1 / SROS2** con certificados X.509, ficheros firmados `governance.p7s` y `permissions.p7s`, y cifrado AES-GCM, bloqueando por completo al nodo atacante).*

---

## 3. Investigación de Amenazas mediante MITRE ATT&CK for ICS (Apartado 4.3)

Se han investigado tres técnicas de la matriz **MITRE ATT&CK for ICS** directamente vinculadas con el protocolo DDS/RTPS y la arquitectura de la celda robotizada:

### 3.1 Técnica 1: `T0842` — Network Sniffing (Táctica: *Discovery*)

* **Descripción del comportamiento del atacante**: El adversario captura pasivamente el tráfico que circula por las interfaces de red de la planta industrial para interceptar variables de proceso, topologías de comunicación y mensajes de control sin generar ruido ni alterar inicialmente el servicio.
* **Condiciones necesarias**: Acceso de capa 2/3 al segmento de red OT (`172.28.0.0/24`) —por ejemplo, a través de un puerto Ethernet en planta, una Wi-Fi industrial de AGVs o un equipo de mantenimiento comprometido— y ausencia de cifrado en el protocolo (`ROS_SECURITY_ENABLE=false`).
* **Relación con el protocolo DDS/RTPS y la arquitectura**: En DDS, el descubrimiento `SPDP` se transmite continuamente en difusión **UDP Multicast (`239.255.0.1:7400`)**, por lo que cualquier interfaz conectada a la subred recibe los anuncios de todos los participantes sin siquiera necesitar *ARP spoofing* ni puerto espejo (*SPAN*). Además, al suscribirse pasivamente a un topic, el middleware Fast-DDS del publicador comienza a enviar copia en claro de los paquetes `RTPS DATA` al sniffer.
* **Posibles evidencias de su ejecución**:
  * En red: Cuando el sniffer utiliza un cliente DDS pasivo (`ros2 topic echo`), genera un paquete `DATA(r)` de suscripción desde una IP/GUID desconocido (`172.28.0.99`, `Frame #243` de `01_dds_normal_traffic.pcapng`). Si usa únicamente `tcpdump` pasivo, no emite paquetes para el tráfico multicast `239.255.0.1:7400`.
  * En host: Interfaz de red en modo promiscuo (`PROMISC`) o procesos `tcpdump`/`tshark` activos.
* **Consecuencias potenciales para el proceso industrial**: Exfiltración de métricas de producción, cadencia de línea (1 pieza cada 3 s), tasas de rechazo y conocimiento exacto del formato JSON/CDR necesario para preparar ataques de inyección quirúrgicos.

### 3.2 Técnica 2: `T0861` — Point & Tag Identification (Táctica: *Collection*)

* **Descripción del comportamiento del atacante**: El adversario enumera e identifica los puntos de control, etiquetas (*tags*), topics, servicios y parámetros de los controladores industriales para mapear qué variable digital corresponde a cada actuador o sensor físico.
* **Condiciones necesarias**: Que el protocolo industrial disponga de mecanismos de autodescubrimiento o introspección sin control de acceso (como `SEDP` en DDS o *Browse* en OPC UA).
* **Relación con el protocolo DDS/RTPS y la arquitectura**: A diferencia de Modbus (donde los registros son direcciones numéricas opacas como `40001`), **DDS es autodocumentado**. Durante la fase `SEDP` (`Frames #35` y `#80` de `01_dds_normal_traffic.pcapng`), cada nodo transmite por el puerto `7410` los nombres simbólicos exactos de todos sus topics (`rt/inspection/piece_status`, `rt/robot/actuator_status`) y servicios de parámetros (`rq/robot_controller/list_parametersRequest`). Además, mediante una llamada al servicio `list_parameters` (`Frame #402` de `02_dds_attack_traffic.pcapng`), el atacante obtiene el listado completo de parámetros internos (`max_tolerance_mm`, `arm_speed_pct`, `force_accept_all`).
* **Posibles evidencias de su ejecución**:
  * Tramas RTPS `DATA(p)` procedentes de un `GUIDPrefix` no inventariado (`01:0f:15:18:75:00:d5:bb...`).
  * Peticiones inusuales a los endpoints de introspección `rq/robot_controller/list_parametersRequest` y `rq/robot_controller/get_parametersRequest` (`Frame #636`).
* **Consecuencias potenciales para el proceso industrial**: El atacante obtiene el "mapa completo" del proceso físico sin necesidad de documentación previa ni ingeniería inversa del código del controlador, identificando que `max_tolerance_mm` gobierna el criterio de rechazo y `arm_speed_pct` la velocidad del brazo.

### 3.3 Técnica 3: `T0836` — Modify Parameter (Táctica: *Impair Process Control*)

* **Descripción del comportamiento del atacante**: El adversario modifica parámetros configurables que rigen la lógica de ejecución de un controlador o actuador industrial, desplazando los límites operativos o umbrales de decisión fuera de los márgenes seguros o de calidad.
* **Condiciones necesarias**: Conectividad IP hacia los puertos UDP de usuario del controlador (`7411`) y ausencia de listas de control de acceso criptográficas (*DDS Access Control Plugin* / `permissions.p7s`).
* **Relación con el protocolo DDS/RTPS y la arquitectura**: ROS 2 expone por defecto en cada nodo un servidor de parámetros sobre DDS (`rq/<nodo>/set_parametersRequest`). Cualquier participante en el mismo `ROS_DOMAIN_ID` puede invocar dicho servicio o publicar directamente en el topic `/inspection/piece_status` con su propio `DataWriter`, ya que DDS permite múltiples publicadores concurrentes sobre un mismo topic (*Many-to-Many*).
* **Posibles evidencias de su ejecución**:
  * En red (`02_dds_attack_traffic.pcapng`): Paquete **`Frame #1235`** (`172.28.0.99:40390 -> 172.28.0.20:7411`) con submensaje `DATA -> rq/robot_controller/set_parametersRequest` alterando `max_tolerance_mm` a `10.0` y `arm_speed_pct` a `100`, así como los paquetes **`Frames #1261, #1270 y #1292`** publicando en `rt/inspection/piece_status` desde la IP `.99` mientras el campo `source_node` afirma ser `"CAM-VISION-01"`.
  * En el controlador: Mensajes en el bus `/parameter_events` y alertas en consola (`[CAMBIO DE PARÁMETRO DDS] 'max_tolerance_mm' modificado remotamente a: 10.0`).
* **Consecuencias potenciales para el proceso industrial**: Anulación silenciosa del control de calidad (aceptación de piezas con fisuras críticas de `2.45 mm`), operación mecánica forzada al `100 %` de velocidad y contaminación de lotes enviados a cliente.

### 3.4 Diferenciación entre vulnerabilidades observadas, ataques posibles y comportamientos demostrados

| Categoría Exigida | Elementos Identificados y Justificación Técnica en el Escenario |
| :--- | :--- |
| **1. Vulnerabilidades observadas** (Debilidades del protocolo y configuración) | 1) **Descubrimiento multicast abierto (`SPDP`/`SEDP`)**: anuncio automático en claro de nodos, IPs, puertos y topics en `239.255.0.1:7400` y `UDP 7410` (`Frames #1, #35, #80`). 2) **Payload CDR sin cifrar**: variables de proceso legibles en ASCII (`Frames #281, #315`). 3) **Servicios de parámetros sin autenticación**: el endpoint `set_parametersRequest` acepta órdenes de cualquier IP del dominio DDS. 4) **Múltiples publicadores sin validación de identidad**: cualquier nodo puede publicar en `/inspection/piece_status` suplantando `source_node`. |
| **2. Ataques técnicamente posibles** (Amenazas viables sobre esta arquitectura) | 1) **Denegación de Servicio (DoS - `T0814`)**: inundación de anuncios `SPDP`/`SEDP` falsos para saturar la tabla de descubrimiento de Fast-DDS, o ajuste de `arm_speed_pct = 0` para detener la línea. 2) **Adversary-in-the-Middle (`T0830`)**: envenenamiento ARP entre `.10` y `.20` para descartar o reescribir paquetes UDP `7411`. 3) **Supresión de alarmas (`T0878`)**: suplantación del topic `/robot/actuator_status` hacia un SCADA superior para ocultar que se aceptan piezas defectuosas. |
| **3. Comportamientos demostrados experimentalmente** (Ejecutados en Docker y capturados en PCAP) | 1) **Sniffing y captura de variables en claro (`T0842`)**: captura de `01_dds_normal_traffic.pcapng` con extracción de los JSON de las piezas `P-1033` y `P-1035` (`Frames #281, #315`). 2) **Enumeración activa de nodos, topics y parámetros (`T0861`)**: ejecución de `discover_and_sniff.sh` desde `172.28.0.99`, evidenciada en `Frames #402` y `#636` de `02_dds_attack_traffic.pcapng`. 3) **Modificación remota de parámetros (`T0836`) e inyección de piezas falsas**: ejecución de `attack_inject_piece.py`, alterando `max_tolerance_mm = 10.0 mm` y `arm_speed_pct = 100 %` (`Frame #1235`) e inyectando `P-FAKE-901..903` (`Frames #1261, #1270, #1292`). |

---

## 4. Análisis del Impacto sobre el Proceso Industrial (Apartado 4.4)

### 4.1 Selección y justificación de la amenaza prioritaria
El grupo selecciona como amenaza prioritaria la **manipulación de la integridad del control de calidad mediante `T0836` (*Modify Parameter*) combinada con la inyección de mensajes DDS falsificados en `/inspection/piece_status`**.

**Justificación conjunta de su prioridad:**

1. **Sigilo operativo (*Stealthiness*)**: A diferencia de un ataque de parada de línea (DoS), que activa inmediatamente las alarmas de planta y es corregido por mantenimiento en minutos, alterar `max_tolerance_mm` de `0.50 mm` a `10.0 mm` o inyectar dictámenes `OK` mantiene la celda robótica funcionando con aparente normalidad.
2. **Explotación nativa sin exploits de memoria**: El atacante no necesita vulnerar el sistema operativo ni desbordar buffers; utiliza las primitivas legítimas del protocolo DDS/RTPS (servicios de parámetros y publicación en topics) que vienen abiertas por defecto.
3. **Multiplicador de daño económico y de seguridad (*Safety*)**: Introducir piezas estructuralmente fisuradas (`SURFACE_CRACK`, `2.45 mm`) en palés certificados como válidos traslada el fallo al producto final (p. ej. un componente de dirección o freno en automoción) y además fuerza al brazo robótico a operar al `100 %` de su velocidad nominal.

### 4.2 Desarrollo del escenario hipotético de ataque

1. **Vector de entrada y condiciones necesarias**: Un técnico externo conecta un portátil de diagnóstico (o se compromete un contenedor/gateway IIoT en el borde de la celda) con acceso a la VLAN de la celda robótica (`172.28.0.0/24`), donde el dominio DDS `ROS_DOMAIN_ID = 0` opera sin SROS2.
2. **Fase de reconocimiento silencioso**: El atacante escucha en `239.255.0.1:7400` durante menos de 5 segundos, descubre los participantes `camera_inspector` (`.10`) y `robot_controller` (`.20`), e identifica el topic `/inspection/piece_status` y el parámetro `max_tolerance_mm`.
3. **Fase de manipulación del proceso**:
   * El atacante envía un único paquete UDP de 290 bytes (`Frame #1235`) a `172.28.0.20:7411` invocando `rq/robot_controller/set_parametersRequest`, elevando `max_tolerance_mm` a `10.0 mm` y `arm_speed_pct` al `100 %`.
   * Adicionalmente, inyecta mensajes `DATA` suplantando `"source_node": "CAM-VISION-01"` para forzar ciclos de paletizado adicionales o enmascarar piezas defectuosas.

### 4.3 Evaluación de consecuencias sobre la instalación industrial

* **Integridad de las variables de proceso**: Se corrompe tanto la **consigna interna de decisión** del controlador (`max_tolerance_mm`: `0.50 mm -> 10.0 mm`) como la **variable de entrada del sensor** en el bus DDS (`quality_status = OK`, `defect_mm = 0.05 mm`), rompiendo la confianza entre el sensor de visión y el actuador robótico.
* **Calidad de producción**: Las piezas con defectos graves de fabricación (`defect_mm = 2.45 mm`, fisuras superficiales) dejan de ser rechazadas o son suplantadas, mezclándose físicamente en el palé de piezas conformes. En una fábrica real, esto invalida lotes enteros, provoca rechazos en auditorías de cliente e implica retiradas de mercado (*recalls*).
* **Seguridad del proceso (*Safety*)**:
  * *En la planta*: El incremento no autorizado de `arm_speed_pct` del `80 %` al `100 %` reduce los márgenes de frenado del brazo robótico, incrementa las inercias al manipular piezas pesadas y acelera la fatiga mecánica de reductores y pinzas.
  * *En la cadena de suministro*: Las piezas fisuradas aceptadas como válidas pueden fracturarse en servicio en sistemas críticos posteriores.
* **Disponibilidad y continuidad del servicio**: Aunque la celda no se detiene en el instante del ataque, una vez detectada la contaminación de los palés, la planta se ve obligada a una **parada total de emergencia** para: (1) poner en cuarentena y re-inspeccionar manualmente toda la producción desde el inicio del turno, y (2) auditar, limpiar y reconfigurar los controladores de la celda.

### 4.4 Medidas de detección y protección recomendadas para un despliegue real

1. **Protección criptográfica nativa con OMG DDS-SECURITY v1.1 (SROS2)** *(implementado en `compose.secure.yml`)*:
   * Activar `ROS_SECURITY_ENABLE=true` y `ROS_SECURITY_STRATEGY=Enforce` utilizando una Autoridad de Certificación (CA) X.509 interna (`security/setup_sros2.sh`).
   * **Autenticación (`DDS:Auth:PKI-DH`)**: El controlador del robot rechaza cualquier handshake `SPDP`/`SEDP` de nodos sin certificado válido firmado por la CA (bloqueando a `172.28.0.99`).
   * **Control de acceso (`DDS:Access:Permissions`)**: Mediante `permissions.p7s` firmado en S/MIME, se autoriza exclusivamente al enclave `/camera_inspector` a publicar en `/inspection/piece_status` y se prohíbe la modificación remota de `/robot_controller/set_parameters`.
   * **Cifrado (`DDS:Crypto:AES-GCM-GMAC`)**: Los submensajes `DATA` se cifran y autentican extremo a extremo, impidiendo el sniffing (`T0842`).
2. **Detección en red (IDS Industrial OT)**:
   * Desplegar sondas pasivas (Suricata / Zeek con disector RTPS) que alerten ante: (a) aparición de un paquete `DATA(p)` con una IP o `GUIDPrefix` fuera de la lista blanca (`172.28.0.10` y `172.28.0.20`), (b) aparición de más de un `DataWriter` (`DATA(w)`) para el topic `/inspection/piece_status`, y (c) cualquier tráfico dirigido al endpoint `rq/robot_controller/set_parametersRequest` durante el modo de producción.
3. **Endurecimiento de aplicación y segmentación (IEC 62443)**:
   * Declarar los parámetros críticos (`max_tolerance_mm`, `arm_speed_pct`) con el descriptor `read_only=True` en `rclpy` tras el arranque, o validar en el callback `on_set_parameters_callback` rangos físicos estrictos (`0.10 <= max_tolerance_mm <= 0.50`).

\newpage

## 5. Actividad Voluntaria: Investigación de un Incidente Real (Apartado 5)

**Caso: Malware industrial *Pipedream / InController* (2022) y sabotaje de parámetros en robots industriales**

**1. ¿Qué ocurrió?**  
En abril de 2022, **CISA**, **NSA**, **FBI** y el DoE de EE. UU., junto con **Dragos** y **Mandiant**, publicaron la alerta **AA22-103A** tras descubrir **Pipedream** (**InController**): un *framework* modular de malware industrial del grupo **CHERNOVITE** diseñado para atacar entornos OT/ICS. Sus módulos (*Mousehole*, *DustTunnel*, *LazyCargo* y *BadOmen*) operan desde un equipo infiltrado en la red de planta contra PLCs (Omron Sysmac NJ/NX, Schneider Modicon), servomotores y buses industriales en tres fases: (1) **descubrimiento activo y pasivo de nodos, topologías y etiquetas (*tags*)** en la subred local; (2) **modificación remota de parámetros de servomotores, tolerancias y consignas de movimiento**; y (3) **alteración de la lógica de control o bloqueo de actuadores**. Paralelamente, las investigaciones experimentales de **Trend Micro** (Politecnico di Milano) y **Alias Robotics** sobre **brazos robóticos industriales reales y celdas basadas en ROS/DDS** (**CVE-2019-13566**) demostraron cómo la falta de autenticación en la subred de la celda permite modificar remotamente parámetros de tolerancia y velocidad del robot para introducir micro-defectos deliberados en la producción sin activar alarmas.

**2. ¿Qué consecuencias tuvo?**

* **Intercepción preventiva y alerta global en infraestructuras críticas**: Pipedream fue neutralizado antes de su detonación masiva contra plantas energéticas y de manufactura, motivando una directiva urgente de CISA para segmentar redes de Nivel 1/2 y proteger servicios de configuración sin autenticar.
* **Sabotaje silencioso de calidad y daño mecánico**: En las pruebas de CISA/Dragos sobre servomotores y en los ensayos de Trend Micro sobre brazos robóticos industriales, la modificación remota de parámetros (`T0836`) permitió: (a) **alterar la precisión dimensional introduciendo piezas defectuosas en lotes certificados**, y (b) **forzar velocidades fuera de rango** hasta degradar los reductores mecánicos o comprometer la seguridad física (*Safety*).

**3. Similitudes con el escenario DDS / RTPS estudiado**  
Aunque Pipedream ataca protocolos como OPC UA, Modbus, CODESYS y FINS UDP y nuestro escenario emplea **DDS / RTPS (ROS 2)**, **el procedimiento táctico del atacante (*Kill Chain* MITRE ATT&CK for ICS) es idéntico en cada etapa**:

| Fase MITRE ATT&CK | Procedimiento en *Pipedream* y ataques a robots (Trend Micro) | Equivalencia en nuestro escenario DDS (`02_dds_attack_traffic.pcapng`) |
| :--- | :--- | :--- |
| **1. Sniffing (`T0842`)** | Infiltración en subred OT Nivel 1/2 e interceptación en claro. | Contenedor `dds_attacker` (`172.28.0.99`) capturando `RTPS DATA` (`Frames #281, #315`). |
| **2. Tags (`T0861`)** | Enumeración automática de nodos y parámetros sin credenciales. | Autodescubrimiento `SPDP`/`SEDP` (`Frames #35, #80`) y `list_parameters` (`Frame #402`). |
| **3. Modify Param (`T0836`)** | Sobrescritura remota de parámetros de servomotores y tolerancias. | `Frame #1235` (`set_parametersRequest`: `max_tolerance_mm=10.0`, `arm_speed_pct=100%`) y `Frames #1261–1292`. |

**4. Fuentes consultadas**

1. **CISA, NSA, FBI & DOE (2022)**. *Alert (AA22-103A): APT Cyber Tools Targeting ICS/SCADA Devices*. [cisa.gov/news-events/cybersecurity-advisories/aa22-103a](https://www.cisa.gov/news-events/cybersecurity-advisories/aa22-103a)
2. **Dragos Inc. (2022)**. *PIPEDREAM: CHERNOVITE’s Emerging Malware Targeting Industrial Control Systems*. [dragos.com/blog/chernovite-pipedream-malware-targeting-industrial-control-systems](https://www.dragos.com/blog/chernovite-pipedream-malware-targeting-industrial-control-systems/)
3. **Mandiant (2022)**. *INCONTROLLER: New State-Sponsored Cyber Attack Tools Target Multiple ICS*. [cloud.google.com/blog/topics/threat-intelligence/incontroller-state-sponsored-ics-tool](https://cloud.google.com/blog/topics/threat-intelligence/incontroller-state-sponsored-ics-tool)
4. **Quarta, D. et al. — Trend Micro & Politecnico di Milano (2017)**. *An Experimental Security Analysis of an Industrial Robot Controller (IEEE S&P)*. [ieeexplore.ieee.org/document/7958582](https://ieeexplore.ieee.org/document/7958582)
