from odoo import _, fields, models
from odoo.exceptions import UserError


class WeighbridgeScaleSplit(models.TransientModel):
    _name = "weighbridge.scale.split"
    _description = "Weighbridge Scale Split"

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
        self._check_validity(active_ids, weighbridge_scale)

        return {
            "weighbridge_scale": weighbridge_scale,
            "quality_control": quality_control,
            "qc_penalty": qc_penalty,
            "qc_return": qc_return,
        }

    def _check_validity(self, active_ids, weighbridge_scale):
        if len(active_ids) > 1:
            raise UserError(_("You can only split one scale at a time"))
        if weighbridge_scale[0].state != "draft":
            raise UserError(_("You can only split scale in draft state"))

    name = fields.Char(
        default=lambda self: self._get_selected_data()["weighbridge_scale"].name
    )

    netto = fields.Float(
        default=lambda self: self._get_selected_data()[
            "weighbridge_scale"
        ].net_after_quality_control,
    )

    quantity = fields.Float(
        default=lambda self: self._get_selected_data()["weighbridge_scale"].quantity,
    )

    def action_split_scale(self):
        data = self._get_selected_data()

        new_wb_scale = self._prepare_new_scale(data["weighbridge_scale"])
        if data["quality_control"]:
            new_wb_qc = self._prepare_new_qc(data["quality_control"], new_wb_scale)
            self._prepare_new_penalty(data["qc_penalty"], new_wb_qc)
            self._prepare_new_return(data["qc_return"], new_wb_qc)

        splitted_ids = [data["weighbridge_scale"].id]

        for record in new_wb_scale.values():
            splitted_ids.append(record.id)

        if new_wb_scale:
            data["weighbridge_scale"].write({"state": "splitted"})
            data["quality_control"].write({"state": "splitted"})
            return self._open_new_scale(splitted_ids)

    def _prepare_new_penalty(self, penalties, quality_control):
        for qc in quality_control.values():
            for penalty in penalties:
                new_penalty = penalty.copy()
                new_penalty.write(
                    {
                        "quality_control_id": qc.id,
                        "penalty_id": penalty.penalty_id.id,
                        "penalty_qty": penalty.penalty_qty,
                    }
                )

    def _prepare_new_return(self, returns, quality_control):
        for qc in quality_control.values():
            for retur in returns:
                new_retur = retur.copy()
                new_retur.write(
                    {
                        "quality_control_id": qc.id,
                        "return_id": retur.return_id.id,
                        "return_qty": retur.return_qty / 2,
                    }
                )

    def _prepare_new_qc(self, quality_control, wb_scale):
        first_qc = quality_control.copy()
        first_qc.write(
            {
                "name": quality_control.name + "-1",
                "source_id": quality_control.id,
                "delivery_number": quality_control.delivery_number,
                "weighbridge_scale_id": wb_scale["first_scale"].id,
            }
        )

        second_qc = quality_control.copy()
        second_qc.write(
            {
                "name": quality_control.name + "-2",
                "source_id": quality_control.id,
                "delivery_number": quality_control.delivery_number,
                "weighbridge_scale_id": wb_scale["second_scale"].id,
            }
        )

        return {
            "first_qc": first_qc,
            "second_qc": second_qc,
        }

    def _prepare_new_scale(self, weighbridge_scale):
        original_netto = weighbridge_scale.net_after_quality_control
        original_quantity = weighbridge_scale.quantity

        if self.netto >= original_netto or (
            self.quantity >= original_quantity and self.quantity > 0
        ):
            raise UserError(
                _(
                    "You cannot split the scale with the same "
                    "or bigger value than the original scale."
                )
            )

        first_scale = weighbridge_scale.copy()
        first_scale.write(
            {
                "name": weighbridge_scale.name + "-1",
                "source_id": weighbridge_scale.id,
                "gross_quality_control": weighbridge_scale.gross_quality_control / 2,
                "quantity": self.quantity,
                "weight_in": weighbridge_scale.weight_out
                + self.netto
                / original_netto
                * weighbridge_scale.total_quality_control_qty
                + self.netto
                if weighbridge_scale.delivery_type == "acceptance"
                else weighbridge_scale.weight_in,
                "weight_out": weighbridge_scale.weight_in
                + self.netto
                / original_netto
                * weighbridge_scale.total_quality_control_qty
                + self.netto
                if weighbridge_scale.delivery_type == "shipment"
                else weighbridge_scale.weight_out,
                "delivery_number": weighbridge_scale.delivery_number,
            }
        )

        second_scale = weighbridge_scale.copy()
        second_scale.write(
            {
                "name": weighbridge_scale.name + "-2",
                "source_id": weighbridge_scale.id,
                "gross_quality_control": weighbridge_scale.gross_quality_control / 2,
                "quantity": original_quantity - self.quantity,
                "weight_in": weighbridge_scale.weight_out
                + (
                    weighbridge_scale.total_quality_control_qty
                    - self.netto
                    / original_netto
                    * weighbridge_scale.total_quality_control_qty
                )
                + (original_netto - self.netto)
                if weighbridge_scale.delivery_type == "acceptance"
                else weighbridge_scale.weight_in,
                "weight_out": weighbridge_scale.weight_in
                + (
                    weighbridge_scale.total_quality_control_qty
                    - self.netto
                    / original_netto
                    * weighbridge_scale.total_quality_control_qty
                )
                + (original_netto - self.netto)
                if weighbridge_scale.delivery_type == "shipment"
                else weighbridge_scale.weight_out,
                "delivery_number": weighbridge_scale.delivery_number,
            }
        )

        return {
            "first_scale": first_scale,
            "second_scale": second_scale,
        }

    def _open_new_scale(self, new_scale):
        return {
            "name": _("Splitted Weighbridge Scale"),
            "type": "ir.actions.act_window",
            "res_model": "weighbridge.scale",
            "view_mode": "tree,form",
            "domain": [("id", "in", new_scale)],
        }
