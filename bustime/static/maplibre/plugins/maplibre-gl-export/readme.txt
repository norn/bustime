https://github.com/watergis/maplibre-gl-export
This module adds control which can export PDF and images

Example:
<script src="/static/maplibre/plugins/maplibre-gl-export/maplibre-gl-export.js"></script>
<link rel="stylesheet" href="/static/maplibre/plugins/maplibre-gl-export/maplibre-gl-export.css" type="text/css">

<script>
  map.addControl(new MaplibreExportControl({
      PageSize: Size.A3,
      PageOrientation: PageOrientation.Portrait,
      Format: Format.PNG,
      DPI: DPI[96],
      Crosshair: true,
      PrintableArea: true,
      Local: 'en'
  }), 'top-right');
</script>
