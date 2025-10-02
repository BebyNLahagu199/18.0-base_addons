from odoo import api, models


class WeighbridgeScaleReport(models.AbstractModel):
    _name = "report.wi_base_weighbridge.report_weighbridge_scale"
    _description = "Weighbridge Scale Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env["weighbridge.scale"].browse(docids)
        return {"doc_ids": docids, "doc_model": "weighbridge.scale", "docs": docs}
