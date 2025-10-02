from odoo import _, api, fields, models
from odoo.exceptions import UserError

DELIVERY_TYPE = [("shipment", "Shipment"), ("acceptance", "Acceptance")]


class WeighbridgeScaleUpdateUnload(models.TransientModel):
    _name = "weighbridge.scale.update.unload"
    _description = "Weighbridge Scale Update Unload"

    def default_unload(self):
        active_ids = self.env.context.get("active_ids")

        weighbridge_scale = self.env["weighbridge.scale"].browse(active_ids)

        self._validate_unload(weighbridge_scale)

        return weighbridge_scale

    def _validate_unload(self, weighbridge_scale):
        if len(weighbridge_scale) > 1:
            raise UserError(_("You can only update one unload data at a time."))

    delivery_type = fields.Selection(
        selection=DELIVERY_TYPE,
        default=lambda self: self.default_unload().delivery_type,
    )
    unload_in = fields.Float(default=lambda self: self.default_unload().unload_in)
    unload_out = fields.Float(default=lambda self: self.default_unload().unload_out)
    additional_unload = fields.Float(default=0.0)
    net_unload = fields.Float(default=lambda self: self.default_unload().net_unload)
    net_unload_after = fields.Float(
        compute="_compute_netto_unload_qty", store=True, readonly=True
    )
    unload_date = fields.Datetime(default=fields.Datetime.now(), required=True)

    def _prepare_unload(self):
        return {
            "unload_in": self.unload_in,
            "unload_out": self.unload_out,
            "unload_date": self.unload_date,
            "additional_unload": self.additional_unload,
        }

    def action_update_unload(self):
        weighbridge_scale = self.default_unload()
        if weighbridge_scale.state in ["splitted", "cancel"]:
            raise UserError(
                _("You can't update unload data in splitted or cancelled state.")
            )
        else:
            weighbridge_scale.write(self._prepare_unload())

    @api.onchange("unload_in", "unload_out")
    def _onchange_netto_unload_qty(self):
        for rec in self:
            if rec.unload_in and rec.unload_out:
                rec.net_unload = abs(rec.unload_in - rec.unload_out)

    @api.depends("net_unload", "additional_unload")
    def _compute_netto_unload_qty(self):
        for rec in self:
            rec.net_unload_after = rec.net_unload - rec.additional_unload
