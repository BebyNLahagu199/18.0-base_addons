import base64
import json

from odoo import api, fields, models


class EstateInherit(models.Model):
    _inherit = "estate.estate"

    name = fields.Char()
    geo_location = fields.Binary(attachment=True)

    @api.constrains("geo_location")
    def _check_geo_location_is_json(self):
        for record in self:
            if record.geo_location:
                content = base64.b64decode(record.geo_location)
                json.loads(content)


class InheritEstateOperation(models.Model):
    _inherit = "estate.upkeep.labour"

    latitude = fields.Float(
        compute="_compute_get_latitude_longitude",
        store=False,
        readonly=True,
        digits=(10, 6),
    )
    longitude = fields.Float(
        compute="_compute_get_latitude_longitude",
        store=False,
        readonly=True,
        digits=(10, 6),
    )

    def _compute_get_latitude_longitude(self):
        for rec in self:
            if rec.location_id:
                rec.latitude = rec.location_id.location_latitude
                rec.longitude = rec.location_id.location_longitude
            else:
                rec.latitude = 0.0
                rec.longitude = 0.0


class EstateHarvestInherit(models.Model):
    _inherit = "estate.harvest"

    latitude = fields.Float(
        compute="_compute_get_latitude_longitude",
        store=False,
        readonly=True,
        digits=(10, 6),
    )
    longitude = fields.Float(
        compute="_compute_get_latitude_longitude",
        store=False,
        readonly=True,
        digits=(10, 6),
    )

    def _compute_get_latitude_longitude(self):
        for rec in self:
            if rec.block_id:
                rec.latitude = rec.block_id.location_latitude
                rec.longitude = rec.block_id.location_longitude
            else:
                rec.latitude = 0.0
                rec.longitude = 0.0
