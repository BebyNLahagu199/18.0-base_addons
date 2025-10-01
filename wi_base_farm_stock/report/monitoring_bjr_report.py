from odoo import api, models


class MonitoringBjrSummaryReport(models.AbstractModel):
    _name = "report.wi_base_farm_stock.report_monitoring_bjr"
    _description = "Monitoring BJR Summary Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        if data and data.get("summary"):
            return {
                "records": data["summary"],
                "date": data["date"],
                "estate": data["estate"],
                "product": data["product"],
            }
