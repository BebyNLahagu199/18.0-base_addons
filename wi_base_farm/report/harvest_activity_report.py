from odoo import api, models


class HarvestActivityReport(models.AbstractModel):
    _name = "report.wi_base_farm.report_harvest_operation"
    _description = "Harvest Activity Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env["estate.operation"].browse(docids)
        ret = {}
        ret["tot_data"] = {}
        ret["upkeep"] = {}
        for doc in docs:
            harvest_activity = doc.estate_harvest_ids
            total_count = self._count_total(harvest_activity)
            ret["tot_data"][f"{doc.id}"] = total_count
            upkeep_activity = doc.labour_line_ids
            total_count = self._get_upkeep_data(upkeep_activity)
            ret["upkeep"][f"{doc.id}"] = total_count
        ret["doc_ids"] = docids
        ret["doc_model"] = "estate.operation"
        ret["docs"] = docs
        return ret

    def _count_total(self, harvest_obj):
        counted_tot = {}
        counted_tot["h_qty"] = sum(harvest_obj.mapped("harvest_qty_unit"))
        counted_tot["h_qty_w"] = sum(harvest_obj.mapped("harvest_qty_weight"))
        counted_tot["o_qty"] = sum(harvest_obj.mapped("other_harvest_qty"))
        counted_tot["o_h_stock_qty"] = sum(
            harvest_obj.mapped("other_harvest_stock_qty")
        )
        counted_tot["h_qtyx_w"] = sum(harvest_obj.mapped("base_extra_weight"))
        counted_tot["h_premix_w"] = sum(harvest_obj.mapped("premi_base_extra"))
        counted_tot["h_att_premi"] = sum(harvest_obj.mapped("attendance_premi"))
        counted_tot["o_premi_tot"] = sum(harvest_obj.mapped("other_harvest_premi"))
        counted_tot["premi_tot"] = sum(harvest_obj.mapped("total_premi"))
        counted_tot["d_wages"] = sum(harvest_obj.mapped("daily_wages"))
        counted_tot["penalty_tot"] = sum(harvest_obj.mapped("penalty_total"))
        counted_tot["wages_tot_in_penalty"] = sum(
            harvest_obj.mapped("total_include_penalty")
        )
        return counted_tot

    def _get_upkeep_data(self, upkeep_obj):
        localdict = {
            "qty": sum(upkeep_obj.mapped("quantity")),
            "hk": sum(upkeep_obj.mapped("num_of_days")),
            "wage": sum(
                upkeep_obj.filtered(lambda x: x.calculation == "daily_salary").mapped(
                    "total_amount"
                )
            ),
            "premi": sum(
                upkeep_obj.filtered(lambda x: x.calculation == "premi").mapped(
                    "total_amount"
                )
            ),
            "total": sum(upkeep_obj.mapped("total_amount")),
        }
        return localdict
