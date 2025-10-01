from odoo import api, fields, models


class HrJobInherit(models.Model):
    _inherit = "hr.job"

    farm_data = fields.Boolean(related="department_id.farm_data", store=True)


class HrDepartment(models.Model):
    _inherit = "hr.department"

    farm_data = fields.Boolean(
        compute="_compute_farm_data", store=True, readonly=False, recursive=True
    )

    @api.depends("parent_id", "parent_id.farm_data")
    def _compute_farm_data(self):
        for rec in self:
            if rec.parent_id:
                rec.farm_data = rec.parent_id.farm_data
            else:
                rec.farm_data = False
