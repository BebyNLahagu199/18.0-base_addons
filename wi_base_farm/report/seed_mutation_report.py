from odoo import fields, models, tools


class SeedBatchReport(models.Model):
    _name = "seed.batch.report"
    _description = "Seed Batch Report"
    _auto = False

    batch_id = fields.Many2one("estate.seed.batch", "Batch", readonly=True)
    planting_date = fields.Date(readonly=True)
    seed_id = fields.Many2one("product.product", "Seed", readonly=True)
    accepted_qty = fields.Float(readonly=True)
    rejected_qty = fields.Float(readonly=True)
    seeding = fields.Float("Planted", readonly=True)
    afkir = fields.Float(readonly=True)
    doubletone = fields.Float(readonly=True)
    transplant = fields.Float(readonly=True)
    delivery = fields.Float(readonly=True)
    total = fields.Float(readonly=True)
    age = fields.Integer(readonly=True, help="Age in months")

    def _query(self, fields="", from_clause="", groupby_clause="", orderby_clause=""):
        select_ = (
            """
            esb.id,
            esb.id as batch_id,
            esb.planting_date,
            prod.id as seed_id,
            SUM(CASE WHEN esm.mutation_type = 'seeding' THEN esm.accepted_qty
                WHEN esm.mutation_type = 'receipt' THEN esm.seed_qty ELSE 0
                END) AS accepted_qty,
            SUM(CASE WHEN esm.mutation_type = 'seeding' THEN esm.rejected_qty ELSE 0
                END) AS rejected_qty,
            SUM(CASE WHEN esm.mutation_type = 'seeding' THEN esm.seed_qty
                WHEN esm.mutation_type = 'receipt' THEN esm.seed_qty ELSE 0
                END) AS seeding,
            SUM(CASE WHEN esm.mutation_type = 'afkir' THEN esm.seed_qty ELSE 0
                END) AS afkir,
            SUM(CASE WHEN esm.mutation_type = 'doubletone' THEN esm.seed_qty ELSE 0
                END) AS doubletone,
            SUM(CASE WHEN esm.mutation_type = 'transplant' THEN esm.seed_qty ELSE 0
                END) AS transplant,
            SUM(CASE WHEN esm.mutation_type = 'delivery' THEN esm.seed_qty ELSE 0
                END) AS delivery,
            esb.seed_qty as total,
            esb.batch_age as age
            %s
        """
            % fields
        )

        from_ = (
            """
            estate_seed_mutation esm
            INNER JOIN estate_seed_batch esb ON esb.id = esm.batch_id
            LEFT JOIN product_product prod ON esb.seed_id = prod.id
            %s
        """
            % from_clause
        )

        where_ = """
            esm.state = 'posted'
        """

        groupby_ = (
            """
            esb.id,
            prod.id
            %s
        """
            % groupby_clause
        )

        orderby_ = (
            """
            esb.planting_date
            %s
        """
            % orderby_clause
        )

        return "(SELECT %s FROM %s WHERE %s GROUP BY %s ORDER BY %s)" % (
            select_,
            from_,
            where_,
            groupby_,
            orderby_,
        )

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """CREATE or REPLACE VIEW %s as (%s)""" % (self._table, self._query())
        )
