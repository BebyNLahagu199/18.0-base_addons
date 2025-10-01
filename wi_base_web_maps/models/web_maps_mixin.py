from collections import defaultdict

from odoo import api, fields, models
from odoo.tools import config


class WebMapsMixin(models.AbstractModel):
    _name = "web.maps.mixin"
    _description = "Web Maps"

    contact_address_complete = fields.Char(
        compute="_compute_complete_address", store=True
    )

    street = fields.Char()
    street2 = fields.Char()
    zip = fields.Char(change_default=True)
    city = fields.Char()
    state_id = fields.Many2one(
        "res.country.state",
        string="State",
        ondelete="restrict",
        domain="[('country_id', '=?', country_id)]",
    )
    country_id = fields.Many2one("res.country", string="Country", ondelete="restrict")
    location_latitude = fields.Float(string="Geo Latitude", digits=(10, 7))
    location_longitude = fields.Float(string="Geo Longitude", digits=(10, 7))
    coordinate = fields.Char(
        compute="_compute_coordinate",
        inverse="_inverse_coordinate",
        help="Fill in the format Latitude,Longitude",
    )
    date_localization = fields.Date(string="Geolocation Date")

    @api.depends("location_latitude", "location_longitude")
    def _compute_coordinate(self):
        for record in self:
            record.coordinate = (
                str(record.location_latitude) + "," + str(record.location_longitude)
            )

    def _inverse_coordinate(self):
        for record in self:
            if record.coordinate:
                record.location_latitude = record.coordinate.split(",")[0]
                record.location_longitude = record.coordinate.split(",")[1]

    def write(self, vals):
        # Reset latitude/longitude in case we modify the address without
        # updating the related geolocation fields
        if any(
            field in vals
            for field in ["street", "zip", "city", "state_id", "country_id"]
        ) and not all(
            "location_%s" % field in vals for field in ["latitude", "longitude"]
        ):
            vals.update(
                {
                    "location_latitude": 0.0,
                    "location_longitude": 0.0,
                }
            )
        return super().write(vals)

    @api.model
    def _geo_localize(self, street="", zips="", city="", state="", country=""):
        geo_obj = self.env["base.geocoder"]
        search = geo_obj.geo_query_address(
            street=street, zip=zips, city=city, state=state, country=country
        )
        result = geo_obj.geo_find(search, force_country=country)
        if result is None:
            search = geo_obj.geo_query_address(city=city, state=state, country=country)
            result = geo_obj.geo_find(search, force_country=country)
        return result

    def update_coordinate(self):
        if not self._context.get("force_geo_localize") and (
            self._context.get("import_file")
            or any(
                config[key] for key in ["test_enable", "test_file", "init", "update"]
            )
        ):
            return False
        for location in self.with_context(lang="en_US"):
            result = self._geo_localize(
                location.street,
                location.zip,
                location.city,
                location.state_id.name,
                location.country_id.name,
            )

            if result:
                location.write(
                    {
                        "location_latitude": result[0],
                        "location_longitude": result[1],
                        "date_localization": fields.Date.context_today(location),
                    }
                )
        return True

    @api.model
    def update_latitude_longitude(self, locations):
        locations_data = defaultdict(list)

        for location in locations:
            if (
                "id" in location
                and "location_latitude" in location
                and "location_longitude" in location
            ):
                locations_data[
                    (location["location_latitude"], location["location_longitude"])
                ].append(location["id"])

        for values, location_ids in locations_data.items():
            # NOTE this should be done in sudo to
            # avoid crashing as soon as the view is used
            self.browse(location_ids).sudo().write(
                {
                    "location_latitude": values[0],
                    "location_longitude": values[1],
                    "date_localization": fields.Date.today(),
                }
            )

        return {}

    @api.onchange("street", "zip", "city", "state_id", "country_id")
    def _delete_coordinates(self):
        self.location_latitude = False
        self.location_longitude = False

    @api.depends("street", "zip", "city", "country_id")
    def _compute_complete_address(self):
        for record in self:
            record.contact_address_complete = ""
            if record.street:
                record.contact_address_complete += record.street + ", "
            if record.zip:
                record.contact_address_complete += record.zip + " "
            if record.city:
                record.contact_address_complete += record.city + ", "
            if record.state_id:
                record.contact_address_complete += record.state_id.name + ", "
            if record.country_id:
                record.contact_address_complete += record.country_id.name
            record.contact_address_complete = (
                record.contact_address_complete.strip().strip(",")
            )
