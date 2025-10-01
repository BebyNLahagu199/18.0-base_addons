from odoo import Command, _, api, fields, models
from odoo.tools.mail import html2plaintext, is_html_empty

PICKING_STATE = [
    ("draft", "Draft"),
    ("confirm", "Confirmed"),
    ("done", "Done"),
    ("locked", "Locked"),
    ("cancel", "Cancelled"),
]


class EstatePicking(models.Model):
    _name = "estate.picking"
    _description = "Estate Picking"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(required=True, default="New", copy=False, readonly=True)
    scheduled_date = fields.Date(
        default=fields.Date.today,
        required=True,
    )
    date_done = fields.Date()
    origin = fields.Char(string="Source Document")
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
    )
    partner_id = fields.Many2one(
        "res.partner", string="Partner", domain="[('farm_data','=',True)]"
    )
    state = fields.Selection(
        selection=PICKING_STATE,
        string="Status",
        default="draft",
        required=True,
        copy=False,
    )
    user_id = fields.Many2one(
        "res.users",
        string="Responsible",
        default=lambda self: self.env.user,
    )
    priority = fields.Selection(
        [("0", "Normal"), ("1", "Urgent")], default="0", index=True
    )
    driver = fields.Char()
    vehicle = fields.Char(string="Plate Number")
    gross_weight = fields.Float()
    net_weight = fields.Float()
    tare_weight = fields.Float()
    loader_ids = fields.Many2many("hr.employee", string="Loader")
    note = fields.Html()
    harvest_ids = fields.One2many(
        "estate.harvest",
        "picking_id",
        string="Harvest Ticket",
        copy=False,
    )
    move_ids = fields.One2many(
        "stock.move",
        "estate_picking_id",
        string="Stock Moves",
        copy=True,
        store=True,
        compute="_compute_move_ids",
    )

    total_harvest_qty = fields.Float(
        string="Total Fruit Qty",
        compute="_compute_total_harvest_qty",
        store=True,
    )

    total_other_harvest_qty = fields.Float(
        compute="_compute_total_harvest_qty",
        store=True,
    )

    total_harvest_stock = fields.Float(compute="_compute_total_harvest_qty", store=True)
    total_other_harvest_stock = fields.Float(
        compute="_compute_total_harvest_qty", store=True
    )

    unload_weight = fields.Float(
        help="Net weight of the unload",
    )
    additional_weight = fields.Float(
        help="Additional weight for the unload",
    )

    estate_ids = fields.Many2many(
        "estate.estate",
        string="Estate",
        compute="_compute_estate_ids",
        store=True,
    )
    exclude_from_bjr = fields.Boolean(copy=False)

    @api.depends("harvest_ids")
    def _compute_estate_ids(self):
        for rec in self:
            rec.estate_ids = rec.harvest_ids.mapped("block_id.estate_id")

    @api.depends(
        "harvest_ids",
        "harvest_ids.harvest_qty_unit",
        "harvest_ids.other_harvest_qty",
        "harvest_ids.harvest_qty_weight",
        "harvest_ids.other_harvest_stock_qty",
    )
    def _compute_total_harvest_qty(self):
        for rec in self:
            rec.total_harvest_qty = sum(rec.harvest_ids.mapped("harvest_qty_unit"))
            rec.total_other_harvest_qty = sum(
                rec.harvest_ids.mapped("other_harvest_qty")
            )
            rec.total_harvest_stock = sum(rec.harvest_ids.mapped("harvest_qty_weight"))
            rec.total_other_harvest_stock = sum(
                rec.harvest_ids.mapped("other_harvest_stock_qty")
            )

    @api.depends("harvest_ids", "partner_id", "unload_weight")
    def _compute_move_ids(self):
        for rec in self:
            rec.move_ids = [Command.clear()]
            if rec.harvest_ids:
                rec.move_ids = rec._prepare_move_values()

    def _prepare_move_values(self):
        move_values = []
        for harvest in self.harvest_ids:
            product = harvest.harvest_main_product_id
            description = (
                html2plaintext(product.description)
                if not is_html_empty(product.description)
                else product.name
            )
            source_location = harvest.estate_operation_id.afdeling_id.stock_location_id
            destination_location = (
                self.partner_id.property_stock_customer
                if self.partner_id
                else self.env.ref("stock.stock_location_customers")
            )
            move_values.append(
                Command.create(
                    {
                        "name": _("Delivery Orders: %s", harvest.name),
                        "description_picking": description,
                        "product_id": product.id,
                        "product_uom": product.uom_id.id,
                        "product_uom_qty": harvest.harvest_qty_weight
                        + harvest.other_harvest_stock_qty,
                        "location_id": source_location.id,
                        "location_dest_id": destination_location.id,
                        "estate_picking_id": self.id,
                        "picked": True,
                    }
                )
            )
        return move_values

    def action_confirm(self):
        self._check_company()
        # call `_action_confirm` on every draft move
        self.move_ids.filtered(lambda move: move.state == "draft")._action_confirm()
        self.write({"state": "confirm"})
        return True

    def action_draft(self):
        self.write({"state": "draft"})

    def action_done(self):
        # if len(self.move_ids) > 1:
        #     raise UserError(
        #         _(
        #             "You can only update one unload data at a time. \n "
        #             "Please Contact Administrator to fix this issue."
        #         )
        #     )
        if all(not move.picked for move in self.move_ids):
            self.move_ids.picked = True
        self.move_ids.product_uom_qty = self.unload_weight
        self.move_ids.quantity = self.unload_weight
        self.move_ids._action_done(cancel_backorder=False)

        self.write({"state": "done"})
        return True

    def action_update_unload(self):
        return {
            "name": _("Update Unload"),
            "type": "ir.actions.act_window",
            "res_model": "estate.picking.wizard.unload",
            "view_mode": "form",
            "view_id": False,
            "target": "new",
            "context": {
                "default_picking_id": self.id,
                "default_net_unload": self.unload_weight,
                "default_additional_weight": self.additional_weight,
            },
        }

    def action_compute_average_weight(self):
        # Get the operation date and afdeling IDs
        operation_date = self.harvest_ids.mapped("estate_operation_id.operation_date")
        afdeling_ids = self.estate_ids.ids

        for date in operation_date:
            # Filter operations based on operation date and afdeling IDs
            operation_ids = (
                self.env["estate.operation"]
                .sudo()
                .search(
                    [
                        ("operation_date", "=", date),
                        ("afdeling_id", "in", afdeling_ids),
                    ]
                )
            )

            # Get harvest and picking IDs from filtered operations
            harvest_ids = operation_ids.mapped("estate_harvest_ids").filtered(
                lambda h: not h.picking_id.exclude_from_bjr
            )
            picking_ids = harvest_ids.mapped("picking_id")

            # Compute harvest average weight
            self._compute_harvest_average_weight(picking_ids, harvest_ids, date)

            # Compute harvest average weight for excluded pickings if any
            exclude_picking_ids = picking_ids.filtered(lambda x: x.exclude_from_bjr)
            if exclude_picking_ids:
                exclude_harvest_ids = exclude_picking_ids.mapped("harvest_ids")
                self._compute_harvest_average_weight(
                    exclude_picking_ids, exclude_harvest_ids, date, excluded=False
                )

    def _compute_harvest_average_weight(
        self, picking_ids, harvest_ids, operation_date, excluded=True
    ):
        block_data = {
            x.id: {
                "main_product_id": x.estate_id.harvest_product_id.id,
                "other_product_id": x.estate_id.harvest_other_product_id.id,
                "total_weight": 0,
                "total_qty": 0,
                "brondolan_weight": 0,
                "brondolan_qty": 0,
            }
            for x in picking_ids.mapped("harvest_ids.block_id")
        }
        for picking in picking_ids:
            scale_weight = picking.unload_weight + picking.additional_weight
            total_tbs = picking.total_harvest_qty
            total_brondolan = picking.total_other_harvest_qty
            bjr, bjr_brondolan = 0, 0

            if total_tbs > 0 and total_brondolan == 0:
                bjr = scale_weight / total_tbs
            elif total_tbs == 0 and total_brondolan > 0:
                bjr_brondolan = scale_weight / total_brondolan
            elif total_tbs > 0 and total_brondolan > 0:
                brondolan_weight = sum(
                    harvest._compute_other_harvest_stock()
                    for harvest in picking.harvest_ids.filtered(
                        lambda x: x.other_harvest_qty > 0
                    )
                )
                bjr_brondolan = brondolan_weight / total_brondolan
                bjr = (scale_weight - brondolan_weight) / total_tbs

            block_data = self._get_block_bjr(
                bjr, bjr_brondolan, picking, block_data, operation_date
            )

        for block_id, data in block_data.items():
            bjr_block, brondolan_block = self._compute_average_weight(
                data, block_id, operation_date
            )

            # Menulis rata-rata berat panen ke panen yang sesuai
            harvest_ids.filtered(lambda x: x.block_id.id == block_id).write(
                {
                    "avg_weight": bjr_block,
                    "other_avg_weight": brondolan_block,
                    "exclude_from_bjr": excluded,
                }
            )
        # self._compute_move_ids()

    def _compute_average_weight(self, data, block_id, operation_date):
        bjr_block = (
            data["total_weight"] / data["total_qty"] if data["total_qty"] > 0 else 0
        )
        brondolan_block = (
            data["brondolan_weight"] / data["brondolan_qty"]
            if data["brondolan_qty"] > 0
            else 0
        )

        harvest_average_logs = self.env["estate.bjr"]
        logs = harvest_average_logs.search(
            [
                ("harvesting_date", "=", operation_date),
                ("block_id", "=", block_id),
            ]
        )
        if not logs:
            self._create_bjr(data, block_id, operation_date, bjr_block, brondolan_block)
        else:
            for product_field, product_name in [
                ("main_product_id", "total"),
                ("other_product_id", "brondolan"),
            ]:
                # Filter logs based on product and date
                logs.filtered(lambda x: x.product_id.id == data[product_field]).write(
                    {
                        "harvest_qty": data[f"{product_name}_qty"],
                        "harvest_uom_qty": data[f"{product_name}_weight"],
                        "bjr": bjr_block
                        if product_field == "main_product_id"
                        else brondolan_block,
                    }
                )
        return bjr_block, brondolan_block

    def _create_bjr(self, data, block_id, operation_date, bjr_block, brondolan_block):
        vals_list = []
        for product_field in ["main_product_id", "other_product_id"]:
            harvest_qty = (
                data["total_qty"]
                if product_field == "main_product_id"
                else data["brondolan_qty"]
            )
            harvest_uom_qty = (
                data["total_weight"]
                if product_field == "main_product_id"
                else data["brondolan_weight"]
            )
            if harvest_qty > 0 or harvest_uom_qty > 0:
                vals_list.append(
                    {
                        "product_id": data[product_field],
                        "harvesting_date": operation_date,
                        "block_id": block_id,
                        "harvest_qty": harvest_qty,
                        "harvest_uom_qty": harvest_uom_qty,
                        "bjr": bjr_block
                        if product_field == "main_product_id"
                        else brondolan_block,
                        "description": "Automatic Generate by System based on Harvest",
                    }
                )

        self.env["estate.bjr"].create(vals_list)

    def _get_block_bjr(self, bjr, bjr_brondolan, picking, block_data, operation_date):
        harvest_ids = picking.mapped("harvest_ids").filtered(
            lambda x: x.operation_date == operation_date
        )
        block_ids = harvest_ids.mapped("block_id")
        for block in block_ids:
            data = harvest_ids.filtered(lambda x: x.block_id == block)
            total_tbs = sum(data.mapped("harvest_qty_unit"))
            total_brondolan = sum(data.mapped("other_harvest_qty"))
            tbs_weight = total_tbs * bjr
            brondolan_weight = total_brondolan * bjr_brondolan
            block_data[block.id]["total_weight"] += tbs_weight
            block_data[block.id]["total_qty"] += total_tbs
            block_data[block.id]["brondolan_weight"] += brondolan_weight
            block_data[block.id]["brondolan_qty"] += total_brondolan
        return block_data

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "estate.picking.seq"
                )
        return super().create(vals_list)
