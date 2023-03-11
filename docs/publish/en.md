# How to publish public transport data in real time

## Architecture
Bustime works using GPS data from vehicles. This data is processed on the server and sent out in real time to connected clients - users of the site and applications.

The Bustime update system supports several ways of obtaining data on the location of public transport. Depending on the technical conditions you can choose the most suitable option.

1. Busti.me server periodically downloads file by an external HTTPS link (every 10 seconds). Supported protocols: Bustime, GTFS-RT.

2. If there is no way to host the file on Internet, it is possible to make POST requests to https://busti.me/api/upload/.

## Dispatch information

The previous file formats imply dispatch information - the link between the unique number of the transmitting device and the name of the route, which the vehicle is currently running.

If the city does not have a dispatch system, you can manually enter information into the table via busti.me. This section of the site is only available to carriers and contains the following information:
- unit ID
- vehicle's registration number
- current route taken
- the last activity of the device

## Collect GPS data directly from transmitters
Public transport vehicles are usually already equipped with GPS transmitters and the data is being aggregated and stored on servers. If the data is not stored correctly, then we can receive it directly from GPS transmitters. Supported protocols: Arnavi, Galileo, GPS101, SAT-LITE, Vialon IPS, Vialon NIS (SOAP / Olympstroy), EGTS (ERA-GLONASS).

## GPS data collection via Bustime application
If public transport is not equipped with GPS transmitters, then you can use any phone or tablet with browser or Bustime app to transmit data. Driver should sign up, activate driver mode, and select the route you are currently taking. Mobile device will get GPS location and transmit them via mobile internet to Bustime servers every 10 seconds.

With this method of transmission, there is no need for dispatch information, because the driver chooses the route by himself.

## Retransmission
Bustime can retransmit incoming data via the Websocket and Bustime protocols. It will allow to publish data via API for other developers without additional load on the transport company's servers.

## Responsible for data transmission:
The organization directly providing the transportation service or the city transportation department.
