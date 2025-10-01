from passlib.context import CryptContext

from odoo import Command, api, fields, models, tools

CUSTOM_ROUNDS = 25000


class ResUsers(models.Model):
    _inherit = "res.users"

    mobile_user = fields.Boolean(default=False)

    mobile_menu_ids = fields.Many2many(
        comodel_name="mobile.menu",
        string="Mobile Menu",
    )

    @tools.ormcache()
    def _crypt_context(self):
        res = super()._crypt_context()
        return res if not self.mobile_user else self._get_custom_crypt_context()

    @tools.ormcache()
    def _get_custom_crypt_context(self):
        return CryptContext(
            ["pbkdf2_sha512", "plaintext"],
            deprecated=["auto"],
            pbkdf2_sha512__rounds=CUSTOM_ROUNDS,
        )

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        for user in users:
            if user.mobile_user:
                user_group_id = self.env["ir.model.data"]._xmlid_to_res_id(
                    "base.group_user"
                )
                user.groups_id = [Command.unlink(user_group_id)]
        return users

    def get_api_domain(self):
        return [("active", "=", True), ("mobile_user", "=", True)]

    def get_users_data(self, company=None):
        res = []
        domain = self.get_api_domain()
        if company:
            domain.append(("company_ids", "in", company))
        data = self.sudo().with_company(company).search(domain)
        if data:
            for user in data:
                res.append(self._prepare_data_user(user))
        return res

    def _prepare_data_user(self, data):
        password_query = """
                            SELECT password FROM res_users
                            WHERE id = %s
                        """
        self.env.cr.execute(password_query, [data.id])
        result = self.env.cr.dictfetchall()
        return {
            "id": data.id,
            "name": data.name,
            "login": data.login,
            "password": result[0]["password"],
            "email": data.email,
            "allowed_menu": data.mobile_menu_ids.mapped("code") or [],
            "profile_image": str(data.image_128.decode("utf-8"))
            if data.image_128
            else "",
            "employee_id": data.employee_id.id or 0,
        }

    def action_set_to_mobile(self):
        for record in self:
            record.mobile_user = True


class MobileMenu(models.Model):
    _name = "mobile.menu"
    _description = "Mobile Menu"

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    active = fields.Boolean(default=True)
