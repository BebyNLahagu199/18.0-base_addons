from lxml.builder import E

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountAnalyticPlan(models.Model):
    _inherit = "account.analytic.plan"

    operation_type_id = fields.Many2one("estate.operation.type")

    def unlink(self):
        not_allowed = [
            self.env.ref("wi_base_farm.analytic_plan_activities").id,
            self.env.ref("wi_base_farm.analytic_plan_block").id,
        ]
        for record in self:
            if record.id in not_allowed:
                raise UserError(_("You cannot delete this plan."))
        return super().unlink()


class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    uom_id = fields.Many2one(
        "uom.uom", string="Unit of Measure", default=lambda self: self._default_uom()
    )

    operation_type_id = fields.Many2one(related="plan_id.operation_type_id")

    @api.model
    def _default_uom(self):
        return self.env.ref("uom.product_uom_unit").id


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    operation_type_id = fields.Many2one("estate.operation.type")

    def _get_view(self, view_id=None, view_type=None, **options):
        arch, view = super()._get_view(view_id, view_type, **options)

        report_view_id = [
            self.env.ref("wi_base_farm.blocks_cost_view_pivot").id,
            self.env.ref("wi_base_farm.blocks_cost_view_graph").id,
        ]
        block_column = self.env.ref("wi_base_farm.analytic_plan_block")._column_name()

        account_node = next(iter(arch.xpath("//field[@name='amount']")), None)
        if account_node is not None and view_id in report_view_id:
            account_node.addnext(E.field(name=block_column, type="row"))

        return arch, view
