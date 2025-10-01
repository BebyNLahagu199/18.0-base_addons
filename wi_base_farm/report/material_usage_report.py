from odoo import fields, models, tools


class MaterialUsageReport(models.Model):
    _name = "material.usage.report"
    _description = "Material Usage Report"
    _auto = False
    _order = "operation_date"

    operation_id = fields.Many2one("estate.operation", "Operation", readonly=True)
    operation_date = fields.Date(readonly=True)
    activity_id = fields.Many2one("account.analytic.account", "Activity", readonly=True)
    location_id = fields.Many2one("estate.block", "Block", readonly=True)
    product_id = fields.Many2one("product.product", "Product", readonly=True)
    product_qty = fields.Float("Quantity", readonly=True)
    product_standard_price = fields.Float("Unit Price", readonly=True)
    product_uom_id = fields.Many2one("uom.uom", "UoM", readonly=True)
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)

    def _query(self, fields="", from_clause="", where_clause="", orderby_clause=""):
        select_ = (
            """
                eum.id,
                eo.id as operation_id,
                eo.operation_date,
                eo.activity_id,
                eo.company_id,
                eum.location_id,
                eum.product_id,
                eum.product_qty,
                eum.product_standard_price,
                CASE WHEN eum.product_uom IS NULL THEN NULL ELSE eum.product_uom
                END as product_uom_id
            %s
        """
            % fields
        )

        from_ = (
            """
                estate_upkeep_material eum
                inner join estate_operation eo on eum.estate_operation_id = eo.id
            %s
        """
            % from_clause
        )

        where_ = (
            """
                eo.state in ('posted','done')
            %s
        """
            % where_clause
        )

        orderby_ = (
            """
                eo.operation_date
            %s
        """
            % orderby_clause
        )

        return "(SELECT %s FROM %s WHERE %s ORDER BY %s)" % (
            select_,
            from_,
            where_,
            orderby_,
        )

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """CREATE or REPLACE VIEW %s as (%s)""" % (self._table, self._query())
        )
