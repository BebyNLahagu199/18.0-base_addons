from odoo import fields, models


class EstateHarvest(models.Model):
    _inherit = "estate.harvest"

    picking_id = fields.Many2one(
        "estate.picking",
        string="Picking",
        help="Picking for this activity",
    )
    exclude_from_bjr = fields.Boolean(
        string="Exclude from BJR",
        help="If checked, this activity will not be included in BJR",
    )

    restan_log_id = fields.One2many(
        "estate.restan.log", "harvest_id", string="Restan Logs"
    )
