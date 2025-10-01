from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    def _get_default_area_uom_id(self):
        uom = self.env.ref("wi_base_farm.product_uom_hectare", raise_if_not_found=False)
        return uom.id if uom else False

    area_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        default=_get_default_area_uom_id,
        string="UoM",
    )

    required_operation_validation = fields.Boolean(
        "Required Validation",
        help="If checked, the system will require validation for every operation",
    )


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"
    _check_company_auto = True

    module_wi_base_farm_stock = fields.Boolean(
        "Picking Operation",
        help="Activate this module to manage picking operation in farm",
    )

    module_wi_base_farm_weighbridge = fields.Boolean(
        "Weighbridge",
        help="Activate this module to manage weighbridge in farm",
    )

    module_wi_base_web_maps_farm = fields.Boolean(
        "Map View",
        help="Activate maps view for farm",
    )

    group_planning_operation = fields.Boolean(
        "Planning Operation",
        default=True,
        implied_group="wi_base_farm.farm_planning_operation",
    )

    required_operation_validation = fields.Boolean(
        related="company_id.required_operation_validation",
        string="Required Validation",
        readonly=False,
    )

    area_uom_id = fields.Many2one(
        related="company_id.area_uom_id",
        string="UoM",
        readonly=False,
    )
