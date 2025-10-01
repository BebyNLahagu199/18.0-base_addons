import base64
from io import BytesIO

import qrcode
from cryptography.fernet import Fernet
from PIL import Image

from odoo import fields, models
from odoo.tools.image import base64_to_image


class QRCodeMixin(models.AbstractModel):
    _name = "qr.code.mixin"
    _description = "QR Code Mixin"

    qr_code = fields.Binary(
        string="QR Code",
        attachment=True,
        store=True,
        readonly=True,
        compute="_compute_qr_code",
        help="QR Code of the record",
    )

    qr_version = fields.Integer(
        string="QR Version",
        related="company_id.qr_version",
        store=True,
    )

    qr_error_correction = fields.Selection(
        string="QR Error Correction",
        related="company_id.qr_error_correction",
        store=True,
    )

    qr_box_size = fields.Integer(
        string="QR Box Size",
        related="company_id.qr_box_size",
        store=True,
    )

    qr_border = fields.Integer(
        string="QR Border",
        related="company_id.qr_border",
        store=True,
    )

    qr_logo = fields.Image(
        string="QR Logo",
        related="company_id.qr_logo",
        store=True,
    )

    qr_key = fields.Char(
        string="QR Key",
        related="company_id.qr_key",
        store=True,
    )

    company_id = fields.Many2one(
        string="Company",
        comodel_name="res.company",
        default=lambda self: self.env.company,
    )

    def prepare_qr_value(self):
        return

    def _compute_qr_code(self):
        for record in self:
            qr_value = record.prepare_qr_value()
            encrypted_value = (
                record._encrypt_qr_value(qr_value)
                if record.qr_key and qr_value
                else qr_value
            )
            record.qr_code = record._generate_qr_code(encrypted_value)

    def _encrypt_qr_value(self, qr_value):
        key = self.qr_key.encode()
        f = Fernet(key)
        encrypted_value = f.encrypt(qr_value.encode())
        return encrypted_value

    def _generate_qr_code(self, qr_value):
        err_correction = (
            qrcode.constants.ERROR_CORRECT_L
            if self.qr_error_correction == "L"
            else qrcode.constants.ERROR_CORRECT_H
            if self.qr_error_correction == "H"
            else qrcode.constants.ERROR_CORRECT_Q
            if self.qr_error_correction == "Q"
            else qrcode.constants.ERROR_CORRECT_M
        )
        qr = qrcode.QRCode(
            version=self.qr_version or 1,
            error_correction=err_correction,
            box_size=self.qr_box_size or 10,
            border=self.qr_border or 4,
        )
        qr.add_data(qr_value.decode()) if isinstance(qr_value, bytes) else qr.add_data(
            qr_value
        )
        qr.make(fit=True)

        qr_img = qr.make_image()

        if not self.qr_logo:
            img_bytes = BytesIO()
            qr_img.save(img_bytes, format="PNG")
            qr_image = base64.b64encode(img_bytes.getvalue())

            return qr_image

        qr_width, qr_height = qr_img.size

        logo_dummy = base64_to_image(self.qr_logo).convert("RGBA")
        logo = logo_dummy.resize((qr_width // 5, qr_width // 5), Image.LANCZOS)

        logo_width, logo_height = logo.size
        x = (qr_width - logo_width) // 2
        y = (qr_height - logo_height) // 2

        qr_img.paste(logo, (x, y))

        img_bytes = BytesIO()
        qr_img.save(img_bytes, format="PNG")
        qr_image = base64.b64encode(img_bytes.getvalue())

        return qr_image
