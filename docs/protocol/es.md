## Protocolo Bustime
### versión 1.0

El protocolo está diseñado para transmitir datos sobre la ubicación del transporte público.

El protocolo es gratuito y se publica bajo licencia abierta.


Protocolo: HTTPS (servidor web)

Formato: archivo CSV

Tiempo de actualización: una vez cada 10 segundos

Ejemplo: https://example.com/api/bustime.csv

Campos: número único de dispositivo, hora, longitud, latitud, matrícula, nombre de la ruta,
velocidad km/h, accesibilidad para sillas de ruedas


Example:
```
12345678,2023-03-11 17:32:42,6.123331,49.815273,LSZ6201,25,24,1
12345679,2023-03-11 17:32:42,6.123381,49.815270,LSZ6283,1,12,0
```
