from datetime import date

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_BATCH_STATE = [
    ("active", "Active"),
    ("out", "Out of Stock"),
]

_MUTATION_STATE = [
    ("draft", "Draft"),
    ("posted", "Posted"),
]

_MUTATION_TYPE = [
    ("seeding", "Seeding"),
    ("doubletone", "Doubletone"),
    ("afkir", "Afkir"),
    ("transplant", "Transplanting"),
    ("delivery", "Delivery"),
    ("receipt", "Receipt"),
]

_DELIVERY_TYPE = [
    ("internal", "Internal"),
    ("external", "External"),
    ("affiliate", "Affiliate"),
]


class FarmSeedMutation(models.Model):
    _name = "estate.seed.mutation"
    _description = "Seed Mutation"

    name = fields.Char(
        copy=False,
        required=True,
        default=lambda self: _("New"),
        readonly=True,
    )
    mutation_type = fields.Selection(
        selection=_MUTATION_TYPE,
        required=True,
        default="seeding",
    )
    block_id = fields.Many2one(
        comodel_name="estate.block",
        string="Block",
        required=True,
        ondelete="cascade",
    )
    batch_id = fields.Many2one(
        comodel_name="estate.seed.batch",
        string="Batch",
        default=False,
        domain="[('seed_qty', '>', 0)]",
        ondelete="cascade",
    )
    operation_date = fields.Date(
        default=fields.Date.today,
        required=True,
        string="Date",
    )
    seed_id = fields.Many2one(
        comodel_name="product.product",
        string="Seed",
        required=True,
        domain=[("farm_data", "=", True)],
    )
    seed_qty = fields.Integer(
        required=True,
    )
    seed_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Unit of Measurement",
        required=True,
        related="seed_id.uom_id",
    )
    description = fields.Char()
    state = fields.Selection(
        selection=_MUTATION_STATE,
        default="draft",
        readonly=True,
    )

    # Seeding Fields
    receipt_number = fields.Char()
    production_date = fields.Date()
    accepted_qty = fields.Integer()
    rejected_qty = fields.Integer()

    # Delivery Fields
    delivery_number = fields.Char()
    licence_plate = fields.Char()
    driver_name = fields.Char()
    delivery_type = fields.Selection(
        selection=_DELIVERY_TYPE,
    )
    dest_block_id = fields.Many2one(
        comodel_name="estate.block",
        string="Destination Block",
        domain="[('id', '!=', block_id)]",
        ondelete="cascade",
    )
    dest_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Destination",
    )
    dest_partner_ids = fields.Many2many(
        comodel_name="res.partner",
        compute="_compute_dest_partner_ids",
    )
    dest_note = fields.Char(string="Destination Note")

    # Receipt Fields
    receipt_trans_id = fields.Many2one(
        comodel_name="estate.seed.mutation",
        string="Transplant From",
        domain="[('mutation_type', '=', 'transplant')]",
    )
    receipt_batch_id = fields.Many2one(
        comodel_name="estate.seed.batch",
        string="Current Batch",
    )

    @api.onchange("delivery_type")
    def _onchange_delivery_type(self):
        self.dest_block_id = False
        self.dest_partner_id = False

    @api.depends("delivery_type")
    def _compute_dest_partner_ids(self):
        for rec in self:
            companies = (
                self.env["res.company"]
                .search([("id", "!=", self.env.company.id)])
                .mapped("partner_id")
            )
            if rec.delivery_type == "affiliate":
                rec.dest_partner_ids = self.env["res.partner"].search(
                    [("id", "in", companies.ids)]
                )
            elif rec.delivery_type == "external":
                rec.dest_partner_ids = self.env["res.partner"].search(
                    [("id", "not in", companies.ids)]
                )
            else:
                rec.dest_partner_ids = self.env["res.partner"].search([])

    @api.onchange("accepted_qty", "rejected_qty")
    def _onchange_seed_qty(self):
        accepted = self.accepted_qty or 0
        rejected = self.rejected_qty or 0
        self.seed_qty = accepted - rejected

    @api.onchange("batch_id")
    def _onchange_batch_id(self):
        self.block_id = self.batch_id.block_id
        self.seed_id = self.batch_id.seed_id
        self.dest_block_id = False

    def _increase_batch_qty(self):
        batch = self.batch_id
        if batch:
            batch.write({"seed_qty": batch.seed_qty + self.seed_qty})

    def _decrease_batch_qty(self):
        batch = self.batch_id
        if batch:
            if batch.seed_qty - self.seed_qty < 0:
                raise UserError(_("This batch has no seed left to be processed."))
            batch.write({"seed_qty": batch.seed_qty - self.seed_qty})

    def _get_seeding_localdict(self):
        localdict = {
            "block_id": self.dest_block_id.id or self.block_id.id,
            "seed_id": self.seed_id.id,
            "seed_qty": self.seed_qty,
            "planting_date": self.operation_date,
            "production_date": self.production_date or self.batch_id.production_date,
        }
        return localdict

    def _post_seeding_batch(self):
        localdict = self._get_seeding_localdict()
        self.batch_id = self.env["estate.seed.batch"].create(localdict)

    def _post_doubletone_batch(self):
        self._increase_batch_qty()

    def _post_afkir_batch(self):
        self._decrease_batch_qty()

    def _create_receipt(self, batch_id):
        localdict = {
            "name": self._create_name("receipt"),
            "block_id": self.block_id.id,
            "seed_id": self.seed_id.id,
            "seed_qty": self.seed_qty,
            "operation_date": self.operation_date,
            "production_date": self.production_date,
            "receipt_trans_id": self.id,
            # "batch_id": self.batch_id.id,
            "batch_id": batch_id.id,
            # "receipt_batch_id": batch_id.id,
            "receipt_batch_id": self.batch_id.id,
            "dest_block_id": self.dest_block_id.id,
            "mutation_type": "receipt",
            "state": "posted",
        }
        return self.env["estate.seed.mutation"].create(localdict)

    def _create_transplant(self):
        localdict = {
            "name": self._create_name("transplant"),
            "block_id": self.block_id.id,
            "dest_block_id": self.dest_block_id.id,
            "seed_id": self.seed_id.id,
            "seed_qty": self.seed_qty,
            "operation_date": self.operation_date,
            "production_date": self.production_date,
            "batch_id": self.batch_id.id,
            "mutation_type": "transplant",
            "state": "posted",
        }
        return self.env["estate.seed.mutation"].create(localdict)

    def _post_transplant_batch(self):
        self._decrease_batch_qty()
        localdict = self._get_seeding_localdict()
        localdict["source_id"] = self.batch_id.id
        batch_id = self.env["estate.seed.batch"].create(localdict)
        res = self._create_receipt(batch_id)
        res._seed_mutation_message()

    def _post_delivery_batch(self):
        self._decrease_batch_qty()

    def _post_receipt_batch(self):
        self._decrease_batch_qty()
        localdict = self._get_seeding_localdict()
        localdict["source_id"] = self.batch_id.id
        batch_id = self.env["estate.seed.batch"].create(localdict)
        res = self._create_transplant()
        res._seed_mutation_message()
        self.receipt_trans_id = res
        self.receipt_batch_id = self.batch_id.id
        self.batch_id = batch_id

    def _update_farm_seed_qty(self):
        farm_product_obj = self.env["estate.product"]
        for rec in self:
            farm_product = farm_product_obj.search(
                [
                    ("block_id", "=", rec.block_id.id),
                    ("product_id", "=", rec.seed_id.id),
                ]
            )
            dest_product = farm_product_obj.search(
                [
                    ("block_id", "=", rec.dest_block_id.id),
                    ("product_id", "=", rec.seed_id.id),
                ]
            )
            if farm_product:
                if rec.mutation_type in ["seeding", "doubletone"]:
                    farm_product.amount += rec.seed_qty
                elif rec.mutation_type in [
                    "afkir",
                    "transplant",
                    "delivery",
                    "receipt",
                ]:
                    farm_product.amount -= rec.seed_qty
            else:
                farm_product_obj.create(
                    {
                        "block_id": rec.block_id.id,
                        "product_id": rec.seed_id.id,
                        "amount": rec.seed_qty,
                    }
                )
            if dest_product:
                if rec.mutation_type in ["transplant", "receipt"]:
                    dest_product.amount += rec.seed_qty
            else:
                farm_product_obj.create(
                    {
                        "block_id": rec.dest_block_id.id,
                        "product_id": rec.seed_id.id,
                        "amount": rec.seed_qty,
                    }
                )

    def action_post(self):
        for rec in self:
            if rec.seed_qty == 0:
                raise UserError(_("Seed quantity must be more than 0."))
            if rec.mutation_type == "seeding":
                rec._post_seeding_batch()
            elif rec.mutation_type == "doubletone":
                rec._post_doubletone_batch()
            elif rec.mutation_type == "afkir":
                rec._post_afkir_batch()
            elif rec.mutation_type == "transplant":
                rec._post_transplant_batch()
            elif rec.mutation_type == "delivery":
                rec._post_delivery_batch()
            elif rec.mutation_type == "receipt":
                rec._post_receipt_batch()

            rec.write({"name": self._create_name(rec.mutation_type), "state": "posted"})
            rec._seed_mutation_message()
            rec._update_farm_seed_qty()
        return True

    def _create_name(self, mut_type=False):
        sequence = "estate.seed.mutation"
        if mut_type == "seeding":
            sequence = "estate.seed.mutation.seeding"
        elif mut_type == "doubletone":
            sequence = "estate.seed.mutation.doubletone"
        elif mut_type == "afkir":
            sequence = "estate.seed.mutation.afkir"
        elif mut_type == "transplant":
            sequence = "estate.seed.mutation.transplant"
        elif mut_type == "delivery":
            sequence = "estate.seed.mutation.delivery"
        elif mut_type == "receipt":
            sequence = "estate.seed.mutation.receipt"
        return self.env["ir.sequence"].next_by_code(sequence)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self._create_name()
        return super().create(vals_list)

    def _seed_mutation_message_content(self):
        self.ensure_one()
        message = Markup(
            _(
                "There's <b>%(type)s</b> done in this block on <b>%(date)s</b> \
                using <b>%(seed)s</b> in the amount of <b>%(amount)s.</b> <br />"
                "Reference: <b>%(name)s</b>"
            )
        ) % {
            "type": self.mutation_type,
            "date": self.operation_date,
            "seed": self.seed_id.name,
            "amount": self.seed_qty,
            "name": self._get_html_link(),
        }
        return message

    def _seed_mutation_message(self):
        block_obj = self.env["estate.block"]
        for mut in self:
            block = block_obj.browse(
                mut.receipt_trans_id.dest_block_id.id
            ) or block_obj.browse(mut.block_id.id)
            message = mut._seed_mutation_message_content()
            block.message_post(
                body=message, subtype_id=self.env.ref("mail.mt_comment").id
            )

    @api.onchange("mutation_type")
    def _onchange_mutation_type(self):
        fields = self.fields_get(attributes=["readonly", "required"]).items()

        fields_to_reset = []

        for fname, value in fields:
            if not value.get("readonly"):
                fields_to_reset.append(fname)

        for field in fields_to_reset:
            if field not in ["mutation_type", "operation_date"]:
                self[field] = False


class FarmSeedBatch(models.Model):
    _name = "estate.seed.batch"
    _description = "Seed Batch"

    name = fields.Char(
        copy=False,
        required=True,
        default=lambda self: _("New"),
        readonly=True,
    )
    block_id = fields.Many2one(
        comodel_name="estate.block",
        string="Block",
        required=True,
        ondelete="cascade",
    )
    seed_id = fields.Many2one(
        comodel_name="product.product",
        string="Seed",
        required=True,
        domain=[("farm_data", "=", True)],
    )
    seed_qty = fields.Integer(
        required=True,
    )
    seed_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Unit of Measurement",
        required=True,
        related="seed_id.uom_id",
    )
    planting_date = fields.Date(
        required=True,
        default=fields.Date.today,
    )
    production_date = fields.Date()
    batch_age = fields.Float(
        compute="_compute_batch_age", store=True, help="Age of the batch in months."
    )
    batch_value = fields.Monetary(
        string="Batches Value",
        default=0,
        copy=False,
        currency_field="currency_id",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        required=True,
        related="company_id.currency_id",
    )
    state = fields.Selection(
        selection=_BATCH_STATE,
        compute="_compute_state",
        store=True,
        compute_sudo=True,
    )
    seed_mutation_ids = fields.One2many(
        comodel_name="estate.seed.mutation",
        inverse_name="batch_id",
        string="Seed Mutation",
    )
    source_id = fields.Many2one(
        comodel_name="estate.seed.batch",
        string="Source Batch",
    )
    dest_ids = fields.One2many(
        comodel_name="estate.seed.batch",
        inverse_name="source_id",
        string="Destination Batch",
    )

    @api.depends("seed_qty")
    def _compute_state(self):
        for rec in self:
            if rec.seed_qty > 0:
                rec.state = "active"
            else:
                rec.state = "out"

    @api.depends("planting_date")
    def _compute_batch_age(self):
        for rec in self:
            if rec.seed_qty > 0:
                today = date.today()
                if rec.planting_date and rec.planting_date <= today:
                    rec.batch_age = (today - rec.planting_date).days / 30
                else:
                    rec.batch_age = 0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code("estate.seed.batch")
        return super().create(vals_list)
