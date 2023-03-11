## Bustime protocol
### version 1.0

The protocol is intended for transmitting data about the public transport vehicle locations.

The protocol is free and published under an open license.


Protocol: HTTPS (web-server)

Format: CSV file

Update time: once in 10 seconds

Example: https://example.com/api/bustime.csv

Fields: unique device number, time, longitude, latitude, license plate, name of the route, speed km/h, wheelchair accessibility


Example:
```
12345678,2023-03-11 17:32:42,6.123331,49.815273,LSZ6201,25,24,1
12345679,2023-03-11 17:32:42,6.123381,49.815270,LSZ6283,1,12,0
```
