from odoo import _, fields, models


class WeighbridgeScale(models.Model):
    _inherit = "weighbridge.scale"

    auto_generated = fields.Boolean(
        string="Auto Generated Document", copy=False, default=False
    )
    auto_scale_id = fields.Many2one(
        "weighbridge.scale",
        string="Source scale Document",
        readonly=True,
        copy=False,
        index="btree_not_null",
    )

    def action_post(self):
        wb_map = {}
        res = super().action_post()
        for wb in self:
            company_sudo = (
                self.env["res.company"]
                .sudo()
                ._find_company_from_partner(wb.partner_id.id)
            )
            if (
                company_sudo
                and company_sudo.wb_rule_type == "weighbridge_scale"
                and not wb.auto_generated
            ):
                wb_map.setdefault(company_sudo, self.env["weighbridge.scale"])
                wb_map[company_sudo] += wb
        for company_sudo, wb in wb_map.items():
            context = dict(
                self.env.context,
                default_company_id=company_sudo.id,
                default_auto_generated=True,
                default_auto_shore_id=wb.id,
                default_weight_in=wb.weight_out,
                default_weight_out=wb.weight_in,
                default_partner_id=wb.company_id.partner_id.id,
                default_weighbridge_id=wb._get_default_weighbridge(company_sudo).id,
            )
            new_wb = (
                wb.with_user(company_sudo.wb_intercompany_user_id.id)
                .with_context(**context)
                .with_company(company_sudo.id)
                .copy()
            )
            new_wb.send_message(new_wb, wb)
            new_wb._duplicate_quality_control_data(wb.quality_control_ids, new_wb)
            wb.send_message(wb, new_wb)
            wb.write(
                {
                    "auto_scale_id": new_wb.id,
                }
            )
        return res

    def action_cancel(self):
        res = super().action_cancel()
        for wb in self:
            if wb.auto_scale_id:
                message = _(
                    "Automatically cancelled from %(wb_name)s "
                    "of company %(company_name)s."
                ) % {
                    "wb_name": wb.name,
                    "company_name": wb.company_id.name,
                }

                company_sudo = (
                    self.env["res.company"]
                    .sudo()
                    ._find_company_from_partner(wb.partner_id.id)
                )
                wb.auto_scale_id.with_company(company_sudo.id).action_cancel()
                wb.auto_scale_id.with_company(company_sudo.id).message_post(
                    body=message
                )
        return res

    def _get_default_weighbridge(self, company):
        return (
            self.env["weighbridge.weighbridge"]
            .with_user(company.wb_intercompany_user_id.id)
            .with_company(company)
            .search([(("company_id", "=", company.id))], limit=1)
        )

    def send_message(self, new_bs, origin_bs):
        msg = _(
            "Automatically generated from %(origin)s of company %(company)s.",
            origin=origin_bs.name,
            company=origin_bs.company_id.name,
        )
        new_bs.message_post(body=msg)

    def _duplicate_quality_control_data(self, datas, scale):
        for data in datas:
            self.env["weighbridge.quality.control"].create(
                {
                    "name": data.name,
                    "date": data.date,
                    "delivery_number": data.delivery_number,
                    "weighbridge_scale_id": scale.id,
                    "penalty_ids": self._duplicate_penalty_info(data.penalty_ids),
                }
            )

    def _duplicate_penalty_info(self, data):
        penalty_info = []
        for penalty in data:
            penalty_info.append(
                (
                    0,
                    0,
                    {
                        "penalty_id": penalty.penalty_id.id,
                        "penalty_qty": penalty.penalty_qty,
                    },
                )
            )
        return penalty_info

    def _prepare_sounding_line(self, bs, sounding):
        return {
            "shore_calculation_id": bs.id,
            "shore_line_condition": sounding.shore_line_condition,
            "tanker_id": bs.tanker_id.id,
            "product_id": bs.product_id.id,
            "measuring_table": bs.tanker_id.measuring_table,
            "height": sounding.height,
            "temperature": sounding.temperature,
            "volume": sounding.volume,
            "density": sounding.density,
            "determination": sounding.determination,
            "adjustment_qty": sounding.adjustment_qty,
            "manual_qty": sounding.manual_qty,
            "result_qty": sounding.result_qty,
        }
