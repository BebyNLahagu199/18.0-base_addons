from odoo import _, api, fields, models
from odoo.exceptions import UserError


class EstateRainLogs(models.Model):
    _name = "estate.rain.logs"
    _description = "Rain Logs"

    name = fields.Char(copy=False, default="New", store=True, compute="_compute_name")
    afdeling = fields.Many2one(
        "estate.estate",
        required=True,
        ondelete="cascade",
        domain="[('location_type', '=', 'afdeling')]",
    )
    code_afdeling = fields.Char(related="afdeling.code")
    log_date = fields.Date(default=fields.Date.today())
    rain_start_t = fields.Float(string="Start Time")
    rain_end_t = fields.Float(string="End Time")
    intensity = fields.Float()
    duration = fields.Float(compute="_compute_duration", store=True)
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)

    @api.depends("rain_start_t", "rain_end_t")
    def _compute_duration(self):
        for rec in self:
            duration = rec.rain_end_t - rec.rain_start_t
            rec.duration = duration

    @api.depends("afdeling")
    def _compute_name(self):
        for rec in self:
            rec.name = self.env["ir.sequence"].next_by_code("estate.rainfall.logs.name")
            rec.name = rec.name + "/" + rec.code_afdeling

    def create(self, vals):
        res = super().create(vals)
        if res.duration < 0:
            raise UserError(
                _("Invalid Time set. Duration value cannot be less than zero ")
            )
        if res.rain_start_t < 0:
            raise UserError(_("Invalid start time"))
        if res.rain_end_t > 24:
            raise UserError(_("Invalid end time"))
        return res
