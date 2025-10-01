-  Models To use the maps view, the models need to inherit
   ``web.maps.mixin`` model or at least the location field is in the
   model that had inherit ``web.maps.mixin`` model.

-  Views

   -  To use the maps view, just simply define the view just like define
      form, tree, kanban, etc.

   -  Tag to use for the maps view: ``<maps><field /></maps>``

      Attribute for ``maps`` tag:

      1. ``location``: field in the model that had inherit to
         ``web.maps.mixin``.
      2. ``limit``: the number of how many records to show on maps,
         default: 10.
      3. ``panel_title``: the text to show on the panel.
      4. ``routing``: boolean, to either allow routing or not. When
         routing is enabled, the last record is set as the destination.
      5. ``hide_title``: boolean, to either hide the title on the panel
         or not.
      6. ``hide_address``: boolean, to either hide the address on the
         popup when the marker is clicked or not.
      7. ``hide_name``: boolean, to either hide the name on the popup
         when the marker is clicked or not.
      8. ``default_order``: field to used for ordering the list on the
         sidepanel.

      Attribute for ``field`` tag:

      1. ``name``: field name of the model.
      2. ``string``: display text. Note: this tag is used to show value
         on the popup when the marker is clicked.

-  The maps view is created using ``Leaflet`` library and rendered using
   ``OpenStreetMap`` when there's no token set in the settings
   configuration. When the token is set, the maps view is rendered using
   ``MapBox`` instead.

-  When the maps view is loaded, the order of the file loaded is as
   following:

   -  maps_view.js
   -  maps_arch_parser.js
   -  maps_controller.js
   -  maps_model.js
   -  maps_renderer.js
