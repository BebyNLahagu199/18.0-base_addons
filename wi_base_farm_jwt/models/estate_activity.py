from odoo import models


class EstateActivityPenalty(models.Model):
    _inherit = "estate.activity.penalty"

    def get_api_domain(self):
        return [("active", "=", True)]

    def get_penalty_data(self, company=None):
        res = []
        domain = self.get_api_domain()
        if company:
            domain.append(("company_id", "=", company))
        data = self.sudo().with_company(company).search(domain)
        if data:
            for penalty in data:
                res.append(self._prepare_data_penalty(penalty))
        return res

    def _prepare_data_penalty(self, data):
        return {
            "id": data.id,
            "name": data.name,
            "code": data.code,
        }


class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    def get_api_domain(self):
        return [
            (
                "root_plan_id",
                "=",
                self.env.ref("wi_base_farm.analytic_plan_activities").id,
            ),
            ("active", "=", True),
        ]

    def get_activity_data(self, company=None):
        res = []
        domain = self.get_api_domain()
        if company:
            domain.append(("company_id", "=", company))
        data = self.sudo().with_company(company).search(domain)
        if data:
            for activity in data:
                res.append(self._prepare_data_activity(activity))
        return res

    def _prepare_data_activity(self, data):
        return {
            "id": data.id,
            "name": data.name,
            "code": data.code or "",
            "operation_type_id": data.operation_type_id.id or 0,
            "operation_type_name": data.operation_type_id.name
            if data.operation_type_id
            else "",
            "uom_id": data.uom_id.id if data.uom_id else 0,
            "uom_name": data.uom_id.name if data.uom_id else "",
        }
