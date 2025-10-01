from itertools import zip_longest

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class EstateEstate(models.Model):
    _name = "estate.estate"
    _description = "Estate"
    _inherit = ["mail.thread", "mail.activity.mixin", "qr.code.mixin"]
    _order = "display_name"

    def _default_warehouse_id(self):
        return self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    color = fields.Integer(string="Color Index")
    note = fields.Text()
    display_name = fields.Char(compute="_compute_display_name", store=True, index=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Default Contact",
        copy=False,
    )
    parent_id = fields.Many2one(
        comodel_name="estate.estate",
        string="Parent Estate",
        index=True,
    )
    child_ids = fields.One2many(
        comodel_name="estate.estate",
        inverse_name="parent_id",
        string="Afdeling",
        domain=[("active", "=", True)],
    )
    block_ids = fields.One2many(
        comodel_name="estate.block",
        inverse_name="estate_id",
        string="Block",
        domain=[("active", "=", True)],
    )
    location_type = fields.Selection(
        selection=[
            ("estate", "Estate"),
            ("afdeling", "Afdeling"),
        ],
        default="afdeling",
        store=True,
    )

    # Address Section
    street = fields.Char()
    street2 = fields.Char()
    zip_code = fields.Char(change_default=True)
    city = fields.Char()
    state_id = fields.Many2one(
        "res.country.state",
        string="State",
        ondelete="restrict",
        domain="[('country_id', '=?', country_id)]",
    )
    country_id = fields.Many2one("res.country", string="Country", ondelete="restrict")
    currency_id = fields.Many2one(
        related="company_id.currency_id", string="Currency", readonly=True
    )
    country_flag = fields.Char(related="country_id.image_url", readonly=True)

    # Inventory Section
    warehouse_id = fields.Many2one(
        "stock.warehouse",
        default=_default_warehouse_id,
        check_company=True,
        string="Warehouse",
        tracking=True,
        help="All operation will use this warehouse as default",
    )

    harvest_product_id = fields.Many2one(
        "product.product",
        string="Harvest Product",
        domain="[('farm_data', '=', True)]",
        help="Product used for Harvesting",
    )

    harvest_product_uom_id = fields.Many2one(
        "uom.uom",
        domain="[('category_id', '=', harvest_product_uom_category_id)]",
        help="Unit of Measure for Harvest Product",
    )

    harvest_product_uom_category_id = fields.Many2one(
        related="harvest_product_id.uom_id.category_id",
        string="Harvest Product UOM Category",
        readonly=True,
    )

    harvest_other_product_id = fields.Many2one(
        "product.product",
        string="Other Harvest Product",
        domain="[('farm_data', '=', True)]",
        help="Product used for Harvesting",
    )

    harvest_other_product_uom_id = fields.Many2one(
        "uom.uom",
        domain="[('category_id', '=', harvest_other_product_uom_category_id)]",
        help="Unit of Measure for Harvest Product",
    )

    harvest_other_product_uom_category_id = fields.Many2one(
        "uom.category",
        string="Other Harvest Product UOM Category",
        related="harvest_other_product_id.uom_id.category_id",
        readonly=True,
    )

    harvest_location_id = fields.Many2one(
        "stock.location",
        "Harvest Location",
        compute="_compute_locations",
        store=True,
        check_company=True,
        readonly=False,
        required=True,
        precompute=True,
        domain="[('usage', '=', 'production'), '|', "
        "('company_id', '=', False), "
        "('company_id', '=', allowed_company_ids[0])]",
        help="Harvested Product will come from this location.",
    )

    stock_location_id = fields.Many2one(
        "stock.location",
        "Stock Location",
        compute="_compute_locations",
        store=True,
        check_company=True,
        readonly=False,
        required=True,
        precompute=True,
        domain="[('usage','=','internal')]",
    )

    premi_ids = fields.One2many(
        comodel_name="estate.premi.config",
        inverse_name="estate_id",
        string="Premi",
    )

    premi_quality_ids = fields.One2many(
        comodel_name="estate.premi.quality.config",
        inverse_name="estate_id",
        string="Premi Quality",
    )

    planned_optimal = fields.Float(
        help="Planned Optimal for Harvesting",
    )
    planned_maximum = fields.Float(
        help="Planned Maximum for Harvesting",
    )
    premi_optimal = fields.Monetary(
        help="Premi for Optimal Harvesting",
    )
    premi_maximum = fields.Monetary(
        help="Premi for Maximum Harvesting",
    )

    # from Ui view
    area_uom_id = fields.Many2one(
        related="company_id.area_uom_id",
    )

    # Summary Section
    total_area = fields.Float(
        help="Total Area for this Estate",
        compute="_compute_estate_summary",
        recursive=True,
        store=True,
    )

    total_harvest_uom_qty = fields.Float(
        string="Harvest UoM Quantity",
        compute="_compute_estate_summary",
        recursive=True,
        help="Overall Harvest Quantity, based on the last month",
        digits="Product Unit of Measure",
        store=True,
    )

    total_harvest_qty = fields.Float(
        string="Harvest Quantity",
        compute="_compute_estate_summary",
        recursive=True,
        help="Overall Harvest Quantity, based on the last month",
        digits="Product Unit of Measure",
        store=True,
    )

    average_weight = fields.Float(
        compute="_compute_estate_summary",
        recursive=True,
        store=True,
        help="Overall Average Weight, based on the last month",
        digits="Product Unit of Measure",
    )

    total_tree_qty = fields.Integer(
        string="Total Tree Quantity",
        help="Total Tree Quantity for this Estate",
        compute="_compute_estate_summary",
        recursive=True,
        store=True,
    )

    _sql_constraints = [
        ("code_unique", "unique(code)", "Code must be unique!"),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        no_partner_vals_list = [
            vals
            for vals in vals_list
            if vals.get("name") and not vals.get("partner_id")
        ]
        if no_partner_vals_list:
            partners = self.env["res.partner"].create(
                [
                    {
                        "name": "%s, %s"
                        % (self.browse(vals["parent_id"]).display_name, vals["name"])
                        if vals["parent_id"]
                        else vals["name"],
                        "parent_id": self.env["res.company"]
                        .search([("id", "=", vals["company_id"])])
                        .partner_id.id,
                        "country_id": vals["company_id"],
                    }
                    for vals in no_partner_vals_list
                ]
            )
            partners.flush_model()
            for vals, partner in zip_longest(no_partner_vals_list, partners):
                vals["partner_id"] = partner.id
        return super().create(vals_list)

    @api.depends(
        "block_ids",
        "block_ids.total_area",
        "block_ids.total_harvest_uom_qty",
        "block_ids.total_harvest_qty",
        "child_ids",
        "child_ids.total_area",
        "child_ids.total_harvest_uom_qty",
        "child_ids.total_harvest_qty",
    )
    def _compute_estate_summary(self):
        for record in self:
            data = (
                record.child_ids
                if record.location_type == "estate"
                else record.block_ids
            )
            harvest_data = self.env["estate.harvest"].search(
                [("block_id", "in", data.ids)]
                if record.location_type == "afdeling"
                else [("afdeling_id", "in", data.ids)]
            )
            record.total_area = sum(data.mapped("total_area"))
            record.total_harvest_qty = sum(harvest_data.mapped("harvest_qty_unit"))
            record.total_harvest_uom_qty = sum(
                harvest_data.mapped("harvest_qty_weight")
            )
            if record.total_harvest_uom_qty and record.total_harvest_qty:
                record.average_weight = (
                    record.total_harvest_uom_qty / record.total_harvest_qty
                )
            record.total_tree_qty = (
                sum(data.mapped("total_tree"))
                if record.location_type != "estate"
                else sum(record.child_ids.mapped("block_ids").mapped("total_tree"))
            )

    @api.constrains("parent_id")
    def _check_estate_recursion(self):
        if not self._check_recursion():
            raise ValidationError(_("Error! You cannot create recursive estates."))

    @api.depends("name", "code", "parent_id")
    def _compute_display_name(self):
        names = dict(self.name_get())
        for record in self:
            record.display_name = names.get(record.id, False)

    @api.depends("warehouse_id")
    def _compute_locations(self):
        for estate in self:
            company_id = (
                estate.company_id
                if (estate.company_id and estate.company_id in self.env.companies)
                else self.env.company
            )
            parent_location = self.env.ref(
                "stock.stock_location_locations_virtual", raise_if_not_found=False
            )
            production_location = self.env["stock.location"].search(
                [
                    ("name", "=", "Production"),
                    ("usage", "=", "production"),
                    ("location_id", "=", parent_location.id),
                    ("company_id", "=", company_id.id),
                ],
                limit=1,
            )
            fallback_loc = (
                self.env["stock.warehouse"]
                .search([("company_id", "=", company_id.id)], limit=1)
                .lot_stock_id
            )
            warehouse_loc = (
                estate.warehouse_id.lot_stock_id
                if estate.warehouse_id
                else fallback_loc
            )

            estate.harvest_location_id = production_location
            estate.stock_location_id = warehouse_loc

    @api.onchange("parent_id")
    def _onchange_parent_id(self):
        for estate in self:
            if estate.parent_id:
                estate.country_id = estate.parent_id.country_id.id
                estate.state_id = estate.parent_id.state_id.id

    def name_get(self):
        res = []
        for record in self:
            name = record.name or ""
            if record.parent_id:
                name = "%s, %s" % (record.sudo().parent_id.name, record.name)
            else:
                name = record.name
            res.append((record.id, name))
        return res

    @api.depends(
        "name",
        "code",
        "location_type",
        "qr_version",
        "qr_error_correction",
        "qr_box_size",
        "qr_border",
        "qr_logo",
        "qr_key",
    )
    def _compute_qr_code(self):
        res = super()._compute_qr_code()
        return res

    def prepare_qr_value(self):
        name = self.name
        code = self.code
        location_type = self.location_type
        qr_value = "%s - %s (%s)" % (name, code, location_type)
        return qr_value
