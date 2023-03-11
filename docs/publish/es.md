# Cómo publicar datos de transporte público en tiempo real

## Arquitectura
Bustime funciona utilizando los datos GPS de los vehículos. Estos datos se procesan en el servidor y se envían en tiempo real a los clientes conectados: los usuarios de la web y de las aplicaciones.

El sistema de actualización Bustime admite varias formas de obtener datos sobre la ubicación del transporte público. Dependiendo de las condiciones técnicas se puede elegir la opción más adecuada.

1. El servidor Busti.me descarga periódicamente el archivo mediante un enlace HTTPS externo (cada 10 segundos). Protocolos soportados: Bustime, GTFS-RT.

2. Si no hay manera de alojar el archivo en Internet, es posible hacer peticiones POST a https://busti.me/api/upload/.

## Información de envío

Los formatos de archivo anteriores implican información de despacho - el vínculo entre el número único del dispositivo transmisor y el nombre de la ruta, que el vehículo está ejecutando actualmente.

Si la ciudad no dispone de un sistema de despacho, puede introducir manualmente la información en la tabla a través de busti.me. Esta sección del sitio sólo está disponible para los transportistas y contiene la siguiente información
- ID de la unidad
- matrícula del vehículo
- ruta actual realizada
- última actividad del dispositivo

## Recopilar datos GPS directamente de los transmisores
Los vehículos de transporte público suelen estar ya equipados con transmisores GPS y los datos se agregan y almacenan en servidores. Si los datos no se almacenan correctamente, podemos recibirlos directamente de los transmisores GPS. Protocolos compatibles: Arnavi, Galileo, GPS101, SAT-LITE, Vialon IPS, Vialon NIS (SOAP / Olympstroy), EGTS (ERA-GLONASS).

## Recogida de datos GPS a través de la aplicación Bustime
Si el transporte público no está equipado con transmisores GPS, puede utilizar cualquier teléfono o tableta con navegador o la aplicación Bustime para transmitir los datos. El conductor debe registrarse, activar el modo conductor y seleccionar la ruta que está realizando en ese momento. El dispositivo móvil obtendrá la localización GPS y la transmitirá a través de Internet móvil a los servidores de Bustime cada 10 segundos.

Con este método de transmisión, no hay necesidad de información de despacho, porque el conductor elige la ruta por sí mismo.

## Retransmisión
Bustime puede retransmitir los datos entrantes a través de los protocolos Websocket y Bustime. Permitirá publicar datos vía API para otros desarrolladores sin carga adicional en los servidores de la empresa de transporte.

## Responsable de la transmisión de datos
La organización que presta directamente el servicio de transporte o el departamento de transporte de la ciudad.
