# Bustime - public trasport online
Checkout [busti.me](https://busti.me/) for live example.

Python/Django app process and visualize public transport vehicle positions using GPS coordinates.
This collection of programs are able to detect current nearest stop, vehicle direction,
real-time timetable, sleeping state (not moved for a long time), zombie state (broken vehicles).

## Supported transport types:
* bus
* trolleybus
* tramway
* inter-city bus
* shuttle bus

## Features
* high optimization for rapid server replies
* websocket real-time updates
* modern HTML5 standard compliance
* simplified version for older devices and browsers (even with no JS)
* OpenStreetmap support
* Rainsys system updates only changed information (broadcasted via websocket)
* "MultiBus" technology allows to track all vehicles of selected route

## How to install
1. Install Ubuntu 14.04 LTS (tested)
2. Make virtualenv and install pip packages from ```docs/pips/pips.freeze```
3. Initialize Django environment
4. Fill in city, bus, bus stop and route tables
5. Generate list of stops for JS at ```utils/nbusstops-export.py```
6. Edit zbusupd.py according to active cities
7. Install supervisor and daemons from the ```addons``` list
8. Run

Optionally you could install:
* [Semantic UI](http://semantic-ui.com/) (CSS framework)
* [r.js optimizer](http://requirejs.org/docs/optimization.html) (compile collection of JS in one file)
* [GeoLite2](http://dev.maxmind.com/geoip/geoip2/geolite2/) (for user's city detection by IP address)

Scripts for building CSS and JS: 99-release-*.sh

#### License
Published under [MIT](LICENSE) license.

