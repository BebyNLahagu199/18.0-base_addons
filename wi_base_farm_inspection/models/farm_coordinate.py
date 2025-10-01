from odoo import fields, models


class FarmCoordinate(models.Model):
    _name = "farm.coordinate"
    _description = "Farm Coordinate"

    sequence = fields.Integer()
    latitude = fields.Float(digits=(10, 6))
    longitude = fields.Float(digits=(10, 6))
    date = fields.Datetime()
    state = fields.Selection(
        [("inc", "Include"), ("not_include", "Not Include")],
    )

    speed = fields.Float(digits=(10, 6))
    accuracy = fields.Float(digits=(10, 6))

    inspection_id = fields.Many2one("farm.inspection", "Inspection")
