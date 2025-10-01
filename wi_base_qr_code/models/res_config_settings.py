from cryptography.fernet import Fernet

from odoo import _, api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"
    _check_company_auto = True

    qr_version = fields.Integer(
        string="QR Version",
        readonly=False,
        related="company_id.qr_version",
    )

    @api.onchange("qr_version")
    def _onchange_qr_version(self):
        if self.qr_version < 1 or self.qr_version > 40:
            self.qr_version = 1
            return {"warning": {"message": _("The version must be between 1 and 40")}}
        return

    qr_error_correction = fields.Selection(
        string="QR Error Correction",
        readonly=False,
        related="company_id.qr_error_correction",
    )

    qr_box_size = fields.Integer(
        string="QR Box Size",
        readonly=False,
        related="company_id.qr_box_size",
    )

    @api.onchange("qr_box_size")
    def _onchange_qr_box_size(self):
        if not self.qr_box_size:
            return

        if self.qr_box_size < 0:
            self.qr_box_size = 10
            return {"warning": {"message": _("The box size must be positive")}}
        return

    qr_border = fields.Integer(
        string="QR Border",
        readonly=False,
        related="company_id.qr_border",
    )

    @api.onchange("qr_border")
    def _onchange_qr_border(self):
        if not self.qr_border:
            return

        if self.qr_border < 4:
            self.qr_border = 4
            return {"warning": {"message": _("The border value must be at least 4")}}
        return

    qr_logo = fields.Image(
        string="QR Logo",
        max_width=128,
        max_height=128,
        readonly=False,
        related="company_id.qr_logo",
    )

    qr_key = fields.Char(
        string="QR Key",
        copy=False,
        readonly=True,
        related="company_id.qr_key",
    )

    def generate_qr_api_key(self):
        key = Fernet.generate_key()
        self.company_id.qr_key = key.decode()


class ResCompany(models.Model):
    _inherit = "res.company"

    qr_version = fields.Integer(
        string="QR Version",
        help="Version of the QR Code (maximum 40)",
        copy=True,
        default=1,
        store=True,
    )

    qr_error_correction = fields.Selection(
        string="QR Error Correction",
        selection=[
            ("L", "Low"),
            ("M", "Medium"),
            ("Q", "Quartile"),
            ("H", "High"),
        ],
        copy=True,
        default="M",
        store=True,
        help="""Error correction level of the QR Code:
        - Low: 7% of codewords can be restored.
        - Medium: 15% of codewords can be restored.
        - Quartile: 25% of codewords can be restored.
        - High: 30% of codewords can be restored.
        """,
    )

    qr_box_size = fields.Integer(
        string="QR Box Size",
        help="Size of the QR Code boxes in pixels",
        copy=True,
        default=10,
        store=True,
    )

    qr_border = fields.Integer(
        string="QR Border",
        help="Size of the QR Code border in boxes",
        copy=True,
        default=4,
        store=True,
    )

    qr_logo = fields.Image(
        string="QR Logo",
        max_width=128,
        max_height=128,
        store=True,
    )

    qr_key = fields.Char(
        string="QR Key",
        copy=False,
        readonly=True,
        store=True,
    )
