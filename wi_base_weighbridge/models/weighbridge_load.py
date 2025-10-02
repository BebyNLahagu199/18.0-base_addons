from odoo import fields, models


class WeighbridgeLoad(models.Model):
    _name = "weighbridge.load"
    _description = "Weighbridge Load"

    type_id = fields.Many2one(
        comodel_name="factory.quality.type",
        string="Name",
        required=True,
    )

    partner = fields.Float(
        default=0.0,
    )

    company = fields.Float(
        default=0.0,
    )

    scale_id = fields.Many2one(
        comodel_name="weighbridge.scale",
        string="Weighbridge Scale",
    )
