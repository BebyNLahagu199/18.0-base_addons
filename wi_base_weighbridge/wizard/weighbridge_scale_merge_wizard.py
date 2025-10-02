from datetime import date

from odoo import _, fields, models
from odoo.exceptions import UserError


class WeighbridgeScaleMerge(models.TransientModel):
    _name = "weighbridge.scale.merge"
    _description = "Weighbridge Scale Merge"

    def _get_selected_data(self):
        active_ids = self.env.context.get("active_ids")
        weighbridge_scale = self.env["weighbridge.scale"].browse(active_ids)
        quality_control = self.env["weighbridge.quality.control"].search(
            [("weighbridge_scale_id", "in", active_ids)]
        )
        qc_penalty = self.env["weighbridge.quality.control.penalty"].search(
            [("quality_control_id", "in", quality_control.ids)]
        )
        qc_return = self.env["weighbridge.quality.control.return"].search(
            [("quality_control_id", "in", quality_control.ids)]
        )
        self._check_validity(weighbridge_scale)

        return {
            "weighbridge_scale": weighbridge_scale,
            "quality_control": quality_control,
            "qc_penalty": qc_penalty,
            "qc_return": qc_return,
        }

    def _check_validity(self, weighbridge_scale):
        partner = weighbridge_scale[0].partner_id
        product = weighbridge_scale[0].product_id
        weighbridge = weighbridge_scale[0].weighbridge_id
        if len(weighbridge_scale) < 2:
            raise UserError(
                _("You need to choose more than one scale at a time to do merge")
            )
        if any(wb.state != "draft" for wb in weighbridge_scale):
            raise UserError(_("You can only merge scale in draft state"))
        if any(wb.partner_id != partner for wb in weighbridge_scale):
            raise UserError(_("You can only merge scale with same partner"))
        if any(wb.product_id != product for wb in weighbridge_scale):
            raise UserError(_("You can only merge scale with same product"))
        if any(wb.weighbridge_id != weighbridge for wb in weighbridge_scale):
            raise UserError(_("You can only merge scale with same weighbridge"))

    weighbridge_scale_id = fields.Many2one(
        comodel_name="weighbridge.scale",
        string="Weighbridge Scale",
        domain="[('id', 'in', active_scale_ids)]",
        required=True,
    )

    active_scale_ids = fields.Many2many(
        comodel_name="weighbridge.scale",
        default=lambda self: self.env.context.get("active_ids"),
    )

    date = fields.Date(
        default=date.today(),
    )

    def action_merge_scale(self):
        data = self._get_selected_data()

        new_wb_scale = self._prepare_new_scale(data["weighbridge_scale"])
        if data["quality_control"]:
            new_wb_qc = self._prepare_new_qc(data["quality_control"], new_wb_scale)
            self._prepare_new_penalty(data["qc_penalty"], new_wb_qc)
            self._prepare_new_return(data["qc_return"], new_wb_qc)

        merged_ids = data["weighbridge_scale"].ids
        merged_ids.append(new_wb_scale.id)

        if new_wb_scale:
            data["weighbridge_scale"].write(
                {
                    "state": "merged",
                    "merged_to": new_wb_scale.id,
                }
            )
        if data["quality_control"] and new_wb_qc:
            data["quality_control"].write(
                {
                    "state": "merged",
                    "merged_to": new_wb_qc.id,
                }
            )
        return self._open_new_scale(merged_ids)

    def _prepare_new_scale(self, weighbridge_scale):
        merge_to = self.weighbridge_scale_id

        new_scale = merge_to.copy()
        new_scale.write(
            {
                "date": self.date,
                "source_ids": [(6, 0, weighbridge_scale.ids)],
                "delivery_number": ", ".join(
                    weighbridge_scale.mapped("delivery_number")
                ),
                "quantity": sum(weighbridge_scale.mapped("quantity")),
                "weight_in": sum(weighbridge_scale.mapped("weight_in")),
                "weight_out": sum(weighbridge_scale.mapped("weight_out")),
                "gross_quality_control": sum(
                    weighbridge_scale.mapped("gross_quality_control")
                ),
                "unload_in": sum(weighbridge_scale.mapped("unload_in")),
                "unload_out": sum(weighbridge_scale.mapped("unload_out")),
            }
        )

        return new_scale

    def _prepare_new_penalty(self, penalties, quality_control):
        penalty_type = penalties.mapped("penalty_id")
        for penalty in penalty_type:
            penalty_qty = penalties.filtered(lambda x: x.penalty_id == penalty).mapped(
                "penalty_qty"
            )
            self.env["weighbridge.quality.control.penalty"].create(
                {
                    "quality_control_id": quality_control.id,
                    "penalty_id": penalty.id,
                    "penalty_qty": sum(penalty_qty),
                }
            )

    def _prepare_new_return(self, returns, quality_control):
        return_type = returns.mapped("return_id")
        for retur in return_type:
            return_qty = returns.filtered(lambda x: x.return_id == retur).mapped(
                "return_qty"
            )
            self.env["weighbridge.quality.control.return"].create(
                {
                    "quality_control_id": quality_control.id,
                    "return_id": retur.id,
                    "return_qty": sum(return_qty),
                }
            )

    def _prepare_new_qc(self, quality_control, new_wb_scale):
        new_qc = quality_control[0].copy()
        new_qc.write(
            {
                "delivery_number": ", ".join(
                    quality_control.mapped("weighbridge_scale_id.delivery_number")
                ),
                "date": self.date,
                "source_ids": [(6, 0, quality_control.ids)],
                "weighbridge_scale_id": new_wb_scale.id,
            }
        )

        return new_qc

    def _open_new_scale(self, new_scale):
        return {
            "name": _("Merged Weighbridge Scale"),
            "type": "ir.actions.act_window",
            "res_model": "weighbridge.scale",
            "view_mode": "tree,form",
            "domain": [("id", "in", new_scale)],
        }
