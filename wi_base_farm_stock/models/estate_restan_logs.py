from datetime import date

from odoo import _, fields, models


class EstateRestanRecord(models.Model):
    _name = "estate.restan.log"
    _description = "Estate Restan Record"

    name = fields.Char(required=True, default=lambda self: _("New"))
    restan_date = fields.Date(string="Date", required=True)
    afdeling_id = fields.Many2one(
        "estate.estate",
        string="Afdeling",
        required=True,
        domain="[('location_type', '=', 'afdeling')]",
    )
    block_id = fields.Many2one("estate.block", string="Block", required=True)
    harvest_product_id = fields.Many2one(
        "product.product",
        string="Harvest Product",
        required=True,
        domain="[('farm_data','=',True)]",
    )
    other_product_id = fields.Many2one(
        "product.product",
        string="Other Harvest Product",
        required=True,
        domain="[('farm_data','=',True)]",
    )
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)
    harvest_qty = fields.Float(string="Harvest Quantity", required=True)
    other_hrvst_qty = fields.Float(string="Other Harvest Quantity", required=True)
    harvest_uom_id = fields.Many2one(
        "uom.uom",
    )
    other_hrvst_uom_id = fields.Many2one(
        "uom.uom",
    )
    harvest_id = fields.Many2one(
        "estate.harvest",
        string="Harvest",
        ondelete="cascade",
        required=True,
    )

    def restan_cron_job(self):
        self.check_harvest_activity()

    def check_harvest_activity(self):
        harvest_activity = self.env["estate.harvest"].search(
            [
                ("picking_id", "=", False),
                ("operation_date", "<", date.today()),
                ("block_id", "!=", False),
                ("restan_log_id", "=", False),
            ]
        )
        for harvest in harvest_activity:
            self.create_restan_log(harvest)

    def create_restan_log(self, harvest):
        restan_log = self.env["estate.restan.log"].create(
            {
                "name": self.env["ir.sequence"].next_by_code("estate.restan.log.name")
                or _("New"),
                "restan_date": harvest.operation_date,
                "afdeling_id": harvest.afdeling_id.id,
                "block_id": harvest.block_id.id,
                "harvest_product_id": harvest.harvest_main_product_id.id,
                "other_product_id": harvest.harvest_other_product_id.id,
                "company_id": harvest.company_id.id,
                "harvest_qty": harvest.harvest_qty_unit,
                "other_hrvst_qty": harvest.other_harvest_qty,
                "harvest_uom_id": harvest.harvest_uom_id.id,
                "other_hrvst_uom_id": harvest.other_harvest_uom_id.id,
                "harvest_id": harvest.id,
            }
        )
        return restan_log
