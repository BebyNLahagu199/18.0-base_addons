from odoo import _, fields, models


class EstatePickingUnload(models.TransientModel):
    _name = "estate.picking.wizard.unload"
    _description = "Update Unload"

    picking_id = fields.Many2one(
        "estate.picking",
        help="Picking for this activity",
    )
    net_unload = fields.Float()
    additional_weight = fields.Float(
        help="Additional weight for the unload",
    )
    unload_date = fields.Datetime(default=fields.Datetime.now)

    def action_update_unload(self):
        self.picking_id.write(
            {
                "unload_weight": self.net_unload,
                "date_done": self.unload_date,
                "additional_weight": self.additional_weight,
            }
        )
        self.picking_id.message_post(
            body=_(
                "Unload updated by %(user_name)s with net unload: %(net_unload)s "
                "and additional weight: %(additional_weight)s"
            )
            % {
                "user_name": self.env.user.name,
                "net_unload": self.net_unload,
                "additional_weight": self.additional_weight,
            }
        )
        self.picking_id.action_compute_average_weight()
