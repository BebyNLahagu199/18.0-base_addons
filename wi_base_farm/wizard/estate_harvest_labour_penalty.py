from odoo import fields, models


class EstateHarvestLabourPenaltyLines(models.TransientModel):
    _name = "estate.harvest.labour.penalty.lines"
    _description = "Harvest Labour Penalty Lines"

    penalty_id = fields.Many2one("estate.activity.penalty", required=True)
    qty = fields.Integer(
        required=True,
    )
    harvest = fields.Many2one("harvest.labour.lines")
