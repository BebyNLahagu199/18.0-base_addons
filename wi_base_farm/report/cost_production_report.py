from odoo import api, models


class CostProductionSummaryReport(models.AbstractModel):
    _name = "report.wi_base_farm.report_cost_production"
    _description = "Cost Production Summary Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        if data and data.get("summary"):
            return {
                "datas": data["summary"],
                "date": data["date"],
                "estate": data["estate"],
                "currency": self.env.company.currency_id,
            }
