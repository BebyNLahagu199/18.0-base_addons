from odoo import models


class WeighbridgeQualityType(models.Model):
    _inherit = "weighbridge.quality.type"

    def get_quality_type(self, company=None, params=False):
        res = []
        domain = []
        if params == "penalty":
            domain.append(("categories", "in", ["deduction", "quality"]))
        elif params == "return":
            domain.append(("categories", "=", "return"))
        elif params == "fraction":
            domain.append(("categories", "=", "fraction"))
        data = self.sudo().search(domain)
        if data:
            calculation_uom = {
                "percentage": "%",
                "per_qty": "kg",
                "per_unit": "unit",
            }
            for rec in data:
                res.append(
                    {
                        "id": rec.id,
                        "name": rec.name,
                        "categories": rec.categories,
                        "calculation_type": calculation_uom[rec.calculation_type],
                        "remark": rec.remark,
                    }
                )

        return res
