from odoo import fields, models


class WeighbridgeScaleMergeOrder(models.TransientModel):
    _name = "weighbridge.scale.merge.order"
    _description = "Weighbridge Scale Merge Order"

    merge = fields.Boolean(
        help="""
            If checked, the system will merge the selected ticket
            to create PO/SO based on the date specified
        """,
    )

    date = fields.Date(
        help="""
            Date of the PO/SO
        """,
    )

    active_scale_ids = fields.Many2many(
        comodel_name="weighbridge.scale",
        default=lambda self: self._context.get("active_ids", []),
    )

    def action_confirm(self):
        pass
