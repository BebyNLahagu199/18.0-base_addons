from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class FarmIssue(models.Model):
    _name = "farm.issue"
    _inherit = ["mail.thread", "mail.tracking.duration.mixin"]
    _description = "Farm Issue"

    sequence = fields.Integer()
    name = fields.Char(compute="_compute_subject_to_name")
    latitude = fields.Float(digits=(10, 6), required=True)
    longitude = fields.Float(digits=(10, 6), required=True)
    foto = fields.Binary(required=True)
    subject = fields.Char(required=True)
    description = fields.Char(required=True)
    date = fields.Datetime(required=True)
    detail_location = fields.Char(required=True)
    inspection_id = fields.Many2one(
        "farm.inspection", ondelete="cascade", required=True
    )
    activity_id = fields.Many2one("account.analytic.account", ondelete="cascade")
    block_id = fields.Many2one("estate.block", ondelete="set null")
    image_ids = fields.One2many("farm.issue.image", "issue_id")
    image_count = fields.Integer(compute="_compute_image_count")
    kbm_count = fields.Integer(compute="_compute_issues_kbm")

    company_id = fields.Many2one(
        "res.company", string="", default=lambda self: self.env.company
    )

    states_id = fields.Many2one(
        "farm.issue.stage",
        tracking=True,
        index=True,
        ondelete="set null",
        group_expand="_read_group_states",
        string="State",
    )
    _track_duration_field = "states_id"

    states_state = fields.Selection(
        related="states_id.state",
        readonly=True,
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        default_state = self.env["farm.issue.stage"].search(
            [("state", "=", "not_bkm")], limit=1
        )
        res["states_id"] = default_state.id
        return res

    @api.depends("subject")
    def _compute_subject_to_name(self):
        for issue in self:
            issue.name = issue.subject

    @api.depends("image_count")
    def _compute_image_count(self):
        for rec in self:
            rec.image_count = len(rec.image_ids)

    def get_button_smart(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Smart Issue",
            "res_model": "farm.issue",
            "view_mode": "tree,form",
            "target": "current",
        }

    @api.depends("kbm_count")
    def _compute_issues_kbm(self):
        for rec in self:
            rec.kbm_count = 0

    def button_confirm_bkm(self):
        for rec in self:
            if not rec.activity_id:
                raise UserError(_("Please define an Activity before confirming."))

            if not rec.activity_id.operation_type_id:
                raise UserError(
                    _("Please define an Operation Type for the selected Activity.")
                )

            operation_type_id = rec.activity_id.operation_type_id.id

            confirmed_stage = self.env["farm.issue.stage"].search(
                [("state", "=", "confirmed")], limit=1
            )

            if not confirmed_stage:
                raise UserError(_("Stage with state 'confirmed' not found."))

            if rec.states_id.state == "not_bkm":
                rec.states_id = confirmed_stage

            actifity = self.env["account.analytic.account"].search(
                [("operation_type_id", "=", operation_type_id)], limit=1
            )

            if actifity and operation_type_id:
                operation = (
                    self.env["estate.operation"]
                    .sudo()
                    .create(
                        {
                            "activity_id": actifity.id,
                            "afdeling_id": rec.block_id.estate_id.id or 0,
                            "operation_date": datetime.now(),
                            "operation_type_id": actifity.operation_type_id.id,
                            "farm_issue_id": rec.id,
                        }
                    )
                )

                return {
                    "type": "ir.actions.act_window",
                    "res_model": "estate.operation",
                    "res_id": operation.id,
                    "view_mode": "form",
                    "target": "current",
                }
            else:
                raise UserError(
                    _("No Analytic Account found for the specified Operation Type.")
                )

    def get_confirm_tbm(self):
        for rec in self:
            operation_type_id = rec.activity_id.operation_type_id.id

            actifity = self.env["account.analytic.account"].search(
                [("operation_type_id", "=", operation_type_id)], limit=1
            )

            if not actifity:
                raise UserError(
                    _("No Analytic Account found for the specified Operation Type.")
                )

            operation = self.env["estate.operation"].search(
                [
                    ("activity_id", "=", rec.activity_id.id),
                    ("afdeling_id", "=", rec.block_id.estate_id.id),
                    ("operation_type_id", "=", actifity.operation_type_id.id),
                ],
                limit=1,
            )

            if rec.states_id.state == "confirmed" and operation:
                return {
                    "type": "ir.actions.act_window",
                    "res_model": "estate.operation",
                    "res_id": operation.id,
                    "view_mode": "form",
                    "target": "current",
                }
            else:
                raise UserError(_("Please, Clik button confirm BKM"))
