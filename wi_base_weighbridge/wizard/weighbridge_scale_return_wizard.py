from datetime import date
from itertools import zip_longest

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class WeighbridgeScaleReturn(models.TransientModel):
    _name = "weighbridge.scale.return"
    _description = "Weighbridge Scale Return"

    scale_ids = fields.Many2many(
        "weighbridge.scale",
        "weighbridge_scale_return_ticket",
        "return_id",
        "scale_id",
        string="Weighbridge Scale",
        domain="[('state','in',('posted','locked'))]",
    )
    new_scale_ids = fields.Many2many(
        "weighbridge.scale",
        "weighbridge_scale_return_ticket_new",
        "return_id",
        "scale_id",
        string="New Weighbridge Scale",
    )
    date = fields.Date(default=date.today())
    reason = fields.Text()
    return_method = fields.Selection(
        [("partial", "Partial"), ("full", "Full")],
        default="full",
    )
    return_scales = fields.One2many(
        "weighbridge.scale.return.line",
        "wizard_id",
        compute="_compute_return_scales",
        readonly=False,
        store=True,
    )

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        scale_ids = (
            self.env["weighbridge.scale"].browse(self.env.context["active_ids"])
            if self.env.context.get("active_model") == "weighbridge.scale"
            else self.env["weighbridge.scale"]
        )

        if any(scale.state not in ["posted", "locked"] for scale in scale_ids):
            raise UserError(_("You can only return posted or locked ticket."))
        if "scale_ids" in fields:
            res["scale_ids"] = [(6, 0, scale_ids.ids)]
        if "refund_method" in fields:
            res["refund_method"] = (len(scale_ids) > 1) and "full" or "partial"
        return res

    def _prepare_field_to_update(self, weighbridge_scale):
        return {
            "source_id": weighbridge_scale.scale_id.id,
            "driver_name": weighbridge_scale.driver_name,
            "licence_plate": weighbridge_scale.licence_plate,
            "weight_in": weighbridge_scale.weight_in,
            "weight_out": weighbridge_scale.weight_out,
            "shrinkage": weighbridge_scale.shrinkage,
            "date": self.date,
            "remark": self.reason,
            "is_return": True,
            "unload_in": weighbridge_scale.scale_id.weight_in
            if self.return_method == "full"
            else weighbridge_scale.weight_out,
            "unload_out": weighbridge_scale.scale_id.weight_out
            if self.return_method == "full"
            else weighbridge_scale.weight_in,
        }

    def action_return_scale(self):
        self.ensure_one()
        lines = self.return_scales
        scales = self.scale_ids

        # create default values for new scale
        default_values_list = []
        for scale in lines:
            to_update_field = self._prepare_field_to_update(scale)
            scale_data = scale.scale_id.copy_data(to_update_field)
            default_values_list.append(scale_data)

        batches = [
            [True],  # New Scale
            [False],  # source Scale
        ]

        for scale, default_vals in zip_longest(scales, default_values_list):
            batches[0].append(default_vals)
            batches[1].append(scale)

        scale_to_redirect = self.env["weighbridge.scale"]
        for is_new, records in batches:
            if is_new:
                new_scale = self.env["weighbridge.scale"].create(records)
                scale_to_redirect |= new_scale
                link_ticket = new_scale.source_id._get_html_link()

                message_body = _("Return Scale Ticket from " + link_ticket)
                new_scale.message_post(body=message_body)
                if self.return_method == "full":
                    new_scale.action_post()
            else:
                records.message_post(body=_("Scale has been returned."))

        self.new_scale_ids = scale_to_redirect

        # create action
        action = {
            "name": _("Return Weighbridge Scale"),
            "type": "ir.actions.act_window",
            "res_model": "weighbridge.scale",
        }
        if len(scale_to_redirect) == 1:
            action.update(
                {
                    "view_mode": "form",
                    "res_id": scale_to_redirect.id,
                }
            )
        else:
            action.update(
                {
                    "view_mode": "tree,form",
                    "domain": [("id", "in", scale_to_redirect.ids)],
                }
            )
        return action

    @api.depends("return_method", "scale_ids")
    def _compute_return_scales(self):
        for wizard in self:
            return_scales = [(5,)]
            for scale in wizard.scale_ids:
                line_fields = [
                    f for f in self.env["weighbridge.scale.return.line"]._fields.keys()
                ]
                scale_return_data = dict(
                    self.env["weighbridge.scale.return.line"].default_get(line_fields)
                )
                scale_return_data.update(wizard._prepare_scale_return_data(scale))
                return_scales.append((0, 0, scale_return_data))
            wizard.return_scales = return_scales

    def _prepare_scale_return_data(self, weighbridge_scale):
        return {
            "scale_id": weighbridge_scale.id,
            "driver_name": weighbridge_scale.driver_name,
            "licence_plate": weighbridge_scale.licence_plate,
            "weight_in": weighbridge_scale.weight_out,
            "weight_out": weighbridge_scale.weight_in,
            "shrinkage": weighbridge_scale.shrinkage,
        }


class WeighbridgeScaleReturnLine(models.TransientModel):
    _name = "weighbridge.scale.return.line"
    _description = "Weighbridge Scale Return Ticket"

    wizard_id = fields.Many2one(
        "weighbridge.scale.return", string="Weighbridge Scale Return"
    )
    scale_id = fields.Many2one("weighbridge.scale", string="Weighbridge Scale")
    vehicle_in = fields.Datetime(
        string="Vehicle Time In", default=fields.datetime.now()
    )
    vehicle_out = fields.Datetime(
        string="Vehicle Time Out", default=fields.datetime.now()
    )
    driver_name = fields.Char(string="Driver")
    licence_plate = fields.Char(string="License Plate")
    weight_in = fields.Float(help="Weight of transportation when arriving.")
    weight_out = fields.Float(help="Weight of transportation when leaving.")
    shrinkage = fields.Float(help="Shrinkage of transportation.")
    gross_weight = fields.Float(
        help="Gross weight before shrinkage.",
        compute="_compute_weight",
    )
    net_weight = fields.Float(
        help="Net weight after shrinkage.",
        compute="_compute_weight",
    )

    @api.depends("weight_in", "weight_out", "shrinkage")
    def _compute_weight(self):
        for record in self:
            record.gross_weight = abs(record.weight_in - record.weight_out)
            record.net_weight = record.gross_weight - record.shrinkage

    @api.onchange("weight_in", "weight_out")
    def _onchange_weight(self):
        for record in self:
            gross = abs(record.weight_in - record.weight_out)
            if record.wizard_id.return_method == "full":
                record.shrinkage = abs(
                    gross - record.scale_id.net_after_quality_control
                )
