from odoo import fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    estate_picking_id = fields.Many2one(
        "estate.picking",
        string="Picking",
        help="Picking for this activity",
    )

    def _update_candidate_moves_list(self, candidate_moves_set):
        res = super()._update_candidate_moves_list(candidate_moves_set)
        for picking in self.mapped("estate_picking_id"):
            candidate_moves_set.add(picking.move_ids)
        return res
