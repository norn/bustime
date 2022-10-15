# Bustime - public trasport online

Python/django app process and visualize public transport vehicle positions using GPS coordinates.

Checkout [busti.me](https://busti.me/) for example.

## Features
* high optimization for rapid server replies
* websocket real-time updates
* modern HTML5 standard compliance
* simplified version for older devices and browsers (even with no JS)
* Rainsys system updates only changed information (broadcasted via websocket)
* "MultiBus" technology allows to track all vehicles of selected route

## How to install
1. Install Linux OS (tested with Ubuntu 14.04 LTS)
2. Make virtualenv and install pip packages from ```docs/pips/pips.freeze```
3. Initialize Django environment
4. Fill in city, bus, bus stop and route tables
5. Generate list of stops for JS at ```utils/nbusstops-export.py```
6. Edit zbusupd.py according to active cities
7. Install supervisor and daemons from the ```addons``` list
8. Run

Optionally you could install:
* [Semantic UI](http://semantic-ui.com/)
* [r.js optimizer](http://requirejs.org/docs/optimization.html)
* [GeoLite2 for user's city detection by IP address](http://dev.maxmind.com/geoip/geoip2/geolite2/)

Scripts for building CSS and JS: 99-release-*.sh

#### License
Published under [MIT](LICENSE) license.

