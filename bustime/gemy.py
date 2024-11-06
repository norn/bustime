#!/usr/bin/python
from __future__ import absolute_import
from __future__ import print_function
import datetime

class kml_render:
    """
    Very simple KML renderer written in case of urgent
    """
    def __init__(self):
        self.data = []
        self.header = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://earth.google.com/kml/2.1">
<Document><name>points.kml</name>
        <Style id="bus-stop-style">
                <IconStyle>
                        <scale>0.6</scale>
                        <Icon>
                                <href>http://bustime.loc/static/img/uico_busstop.png</href>
                        </Icon>
                        <hotSpot x="0" y="0" xunits="pixels" yunits="pixels"/>
                </IconStyle>
    <LineStyle>
      <color>fff58776</color>
      <width>3</width>
    </LineStyle></Style>

        <Style id="bus-style">
                <IconStyle>
                        <scale>1</scale>
                        <Icon><href>http://bustime.loc/static/img/bus_front.png</href></Icon>
                        <hotSpot x="0" y="0" xunits="pixels" yunits="pixels"/>
                </IconStyle>
        </Style>
         <Folder>
                <name>track</name>
         <open>1</open>"""
        self.footer = "</Folder></Document></kml>"
        self.point_templ = """
    <Placemark>
    <name>%s</name>
    <description>%s</description>
<styleUrl>#%s</styleUrl>
 <Point><coordinates>%f,%f</coordinates></Point>
 </Placemark>
"""
    def add_pnt(self,z):
        self.data.append(z)
    def write_xml(self):
        self.accum = []
        self.accum.append(self.header)
        # draws icons
        for i in (self.data):
                self.accum.append(self.point_templ % (i.name, i.description, i.style, i.lon, i.lat))
        self.accum.append(self.footer)
        return self.accum
    class ggpoint:
        def __init__ (self, style="bus-stop-style", name=None, description=None, lon=None, lat=None):
            self.style=style
            self.name=name
            self.description=description
            self.lon=lon
            self.lat=lat

if __name__ == "__main__":
    kml = kml_render()
    kml.add_pnt(kml.ggpoint("bus-style", "nameXX", "descr", 92.9216, 56.0326))
    for i in kml.write_xml():
        print(i)