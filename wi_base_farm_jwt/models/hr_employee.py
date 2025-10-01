import base64

from odoo import models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def get_api_domain(self):
        return [("job_id.farm_data", "=", True), ("active", "=", True)]

    def get_employee_data(self, company=None):
        res = []
        domain = self.get_api_domain()
        if company:
            domain.append(("company_id", "=", company))
        data = self.sudo().with_company(company).search(domain)
        if data:
            for employee in data:
                res.append(self._prepare_data_employee(employee))
        return res

    def _prepare_data_employee(self, data):
        is_image = self._check_image(data.image_128)
        return {
            "id": data.id,
            "name": data.name,
            "code": data.barcode or "",
            "type": data.employee_type,
            "position": data.job_id.name or "",
            "department": data.department_id.id or 0,
            "company_id": data.company_id.id,
            "profile_image": str(data.image_128.decode("utf-8")) if is_image else "",
        }

    def _check_image(self, image):
        base64_data = image.decode("utf-8")
        decoded_data = base64.b64decode(base64_data)
        is_svg = decoded_data.startswith(b"<?xml") and b"<svg" in decoded_data
        return False if is_svg else True
