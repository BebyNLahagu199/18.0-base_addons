from ast import literal_eval

from odoo import fields, models

WEIGHBRIDGE_WEIGHBRIDGE_TYPE = [
    ("mobile", "Mobile"),
    ("weighbridge", "Weighbridge"),
]


class WeighbridgeWeighbridge(models.Model):
    _name = "weighbridge.weighbridge"
    _description = "Weighbridge Configuration"

    name = fields.Char(default="New", required=True)

    code = fields.Char(required=True)

    color = fields.Integer()

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
        readonly=True,
    )

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Address",
        default=lambda self: self.env.company.partner_id,
        check_company=True,
    )

    warehouse_id = fields.Many2one(
        comodel_name="stock.warehouse",
        string="Warehouse",
    )

    location_stock_id = fields.Many2one(
        comodel_name="stock.location",
        related="warehouse_id.lot_stock_id",
        string="Stock Location",
        readonly=True,
        store=True,
        check_company=True,
    )

    type = fields.Selection(
        selection=WEIGHBRIDGE_WEIGHBRIDGE_TYPE,
        default="weighbridge",
        copy=False,
        required=True,
    )

    weighbridge_scale_ids = fields.One2many(
        "weighbridge.scale", "weighbridge_id", string="Weighbridge Scale"
    )

    to_post_count = fields.Integer(
        string="To Post",
        compute="_compute_to_post_count",
    )

    show_sequence = fields.Boolean(
        compute="_compute_show_sequence",
    )

    def _compute_show_sequence(self):
        for rec in self:
            rec.show_sequence = False

    def _compute_to_post_count(self):
        for wb in self:
            scale = wb.weighbridge_scale_ids
            wb.to_post_count = len(scale.filtered(lambda line: line.state == "draft"))

    def action_scale(self):
        return self._get_action("wi_base_weighbridge.action_weighbridge_scale_view")

    def action_quality_control(self):
        return self._get_action(
            "wi_base_weighbridge.action_weighbridge_quality_control_view"
        )

    def action_to_post(self):
        return self._get_action(
            "wi_base_weighbridge.action_weighbridge_scale_view",
            params="to_post",
        )

    def action_acceptance(self):
        return self._get_action("wi_base_weighbridge.action_acceptance_reporting_view")

    def action_shipment(self):
        return self._get_action("wi_base_weighbridge.action_shipment_reporting_view")

    def _get_action(self, action_xmlid, params=False):
        action = self.env["ir.actions.actions"]._for_xml_id(action_xmlid)
        if self:
            action["display_name"] = "Weighbridge - %s" % self.name
        context = {
            "default_weighbridge_id": self.id,
            "default_company_id": self.company_id.id,
        }
        action_context = literal_eval(action["context"])
        context = {**action_context, **context}
        action["context"] = context
        domain = self._compute_action_domain(action, params)
        action["domain"] = domain
        return action

    def _compute_action_domain(self, action, params):
        action_domain = literal_eval(action["domain"])
        domain = ("weighbridge_id", "=", self.id)
        action_domain.append(domain)
        if params == "to_post":
            tmp = ("state", "=", "draft")
            action_domain.append(tmp)
        return action_domain
