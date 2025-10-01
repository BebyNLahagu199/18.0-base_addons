from datetime import date

from odoo import _, fields, models
from odoo.exceptions import UserError


class MonitoringBjrReport(models.TransientModel):
    _name = "monitoring.bjr.report"
    _description = "Monitoring BJR Report"

    date = fields.Date(default=date.today(), required=True)
    estate_id = fields.Many2one(
        comodel_name="estate.estate",
        required=True,
        domain="[('location_type','=','estate')]",
    )
    product_id = fields.Many2one(
        comodel_name="product.product", required=True, domain="[('farm_data','=',True)]"
    )

    def harvest_query(self, date_filter=""):
        query_ = """
            SELECT
                eb.id,
                COALESCE(SUM(CASE WHEN eh.harvest_main_product_id = %(product_id)s
                    THEN eh.harvest_qty_unit
                    WHEN eh.harvest_other_product_id = %(product_id)s
                    THEN eh.other_harvest_qty ELSE 0
                    END),0) AS harvest_qty
            FROM
                estate_estate ee
                FULL JOIN estate_block eb ON eb.estate_id = ee.id
                FULL JOIN estate_harvest eh ON eh.block_id = eb.id
            WHERE
                ee.parent_id = %(estate_id)s
                AND (eh.harvest_main_product_id = %(product_id)s
                    OR eh.harvest_other_product_id = %(product_id)s)
                AND eh.state != 'cancel'
                AND CAST(eh.harvest_qty_unit + eh.other_harvest_qty AS numeric) != 0
                %(date_filter)s
            GROUP BY
                eb.id
        """ % {
            "product_id": self.product_id.id,
            "estate_id": self.estate_id.id,
            "date_filter": date_filter,
        }
        return query_

    def picking_query(self, date_filter=""):
        query_ = """
            SELECT
                eb.id,
                COALESCE(SUM(CASE WHEN eh.harvest_main_product_id = %(product_id)s
                    THEN eh.harvest_qty_unit
                    WHEN eh.harvest_other_product_id = %(product_id)s
                    THEN eh.other_harvest_qty ELSE 0
                    END),0) AS picking_qty
            FROM
                estate_estate ee
                FULL JOIN estate_block eb ON eb.estate_id = ee.id
                FULL JOIN estate_harvest eh ON eh.block_id = eb.id
            WHERE
                ee.parent_id = %(estate_id)s
                AND (eh.harvest_main_product_id = %(product_id)s
                    OR eh.harvest_other_product_id = %(product_id)s)
                AND eh.state != 'cancel'
                AND eh.picking_id != 0
                AND CAST(eh.harvest_qty_unit + eh.other_harvest_qty AS numeric) != 0
                %(date_filter)s
            GROUP BY
                eb.id
        """ % {
            "product_id": self.product_id.id,
            "estate_id": self.estate_id.id,
            "date_filter": date_filter,
        }
        return query_

    def avg_weight_query(self, date_filter=""):
        query_ = """
            SELECT
                picking_ref.id,
                SUM(picking_ref.avg_weight * picking_ref.harvest_qty) /
                SUM(picking_ref.harvest_qty) AS avg_factory
            FROM
                (
                    SELECT
                        eb.id AS id,
                        ep.id AS picking_id,
                        COALESCE(
                            (ep.unload_weight + ep.additional_weight -
                                COALESCE(MAX(CASE WHEN
                                    eh.harvest_main_product_id = %(product_id)s
                                    THEN ep.total_other_harvest_stock
                                    WHEN eh.harvest_other_product_id = %(product_id)s
                                    THEN ep.total_harvest_stock ELSE 0
                                    END), 0)
                            ) /
                                MAX(CASE WHEN
                                    eh.harvest_main_product_id = %(product_id)s
                                    THEN ep.total_harvest_qty
                                    WHEN eh.harvest_other_product_id = %(product_id)s
                                    THEN ep.total_other_harvest_qty ELSE 0
                                    END),0) AS avg_weight,
                        COALESCE(SUM(CASE WHEN
                                    eh.harvest_main_product_id = %(product_id)s
                                    THEN eh.harvest_qty_unit
                                    WHEN eh.harvest_other_product_id = %(product_id)s
                                    THEN eh.other_harvest_qty ELSE 0
                                    END), 0) AS harvest_qty
                    FROM
                        estate_picking ep
                        RIGHT JOIN estate_harvest eh ON eh.picking_id = ep.id
                        LEFT JOIN estate_block eb ON eh.block_id = eb.id
                        LEFT JOIN estate_estate ee ON eb.estate_id = ee.id
                    WHERE
                        ee.parent_id = %(estate_id)s
                        AND (eh.harvest_main_product_id = %(product_id)s
                            OR eh.harvest_other_product_id = %(product_id)s)
                        AND eh.state != 'cancel'
                        AND eh.picking_id <> 0
                        AND CAST(eh.harvest_qty_unit + eh.other_harvest_qty
                                AS numeric) <> 0
                        %(date_filter)s
                    GROUP BY
                        eb.id,
                        ep.id
                ) AS picking_ref
            GROUP BY
                picking_ref.id
        """ % {
            "product_id": self.product_id.id,
            "estate_id": self.estate_id.id,
            "date_filter": date_filter,
        }
        return query_

    def remnant_query(self, date_filter=""):
        query_ = """
            SELECT
                eb.id,
                COALESCE(SUM(CASE WHEN erl.harvest_product_id = %(product_id)s
                    THEN erl.harvest_qty
                    WHEN erl.other_product_id = %(product_id)s
                    THEN erl.other_hrvst_qty ELSE 0
                    END),0) AS remnant
            FROM
                estate_estate ee
                FULL JOIN estate_block eb ON eb.estate_id = ee.id
                FULL JOIN estate_restan_log erl ON erl.block_id = eb.id
            WHERE
                ee.parent_id = %(estate_id)s
                AND (erl.harvest_product_id = %(product_id)s
                    OR erl.other_product_id = %(product_id)s)
                AND CAST(erl.harvest_qty + erl.other_hrvst_qty AS numeric) != 0
                %(date_filter)s
            GROUP BY
                eb.id
        """ % {
            "product_id": self.product_id.id,
            "estate_id": self.estate_id.id,
            "date_filter": date_filter,
        }
        return query_

    def header_query(self):
        query_ = """
            eb.code,
            eb.planting_year,
            eb.total_area,
            eb.total_tree,
            COALESCE(harvest_ttd.harvest_qty,0) AS harvest_ttd,
            COALESCE(harvest_mtd.harvest_qty,0) AS harvest_mtd,
            COALESCE(harvest_ytd.harvest_qty,0) AS harvest_ytd,
            COALESCE(picking_ttd.picking_qty,0) AS picking_ttd,
            COALESCE(picking_mtd.picking_qty,0) AS picking_mtd,
            COALESCE(picking_ytd.picking_qty,0) AS picking_ytd,
            (COALESCE(avg_weight_ttd.avg_factory,0)
                * COALESCE(picking_ttd.picking_qty,0)) AS kg_wb_ttd,
            (COALESCE(avg_weight_mtd.avg_factory,0)
                * COALESCE(picking_mtd.picking_qty,0)) AS kg_wb_mtd,
            (COALESCE(avg_weight_ytd.avg_factory,0)
                * COALESCE(picking_ytd.picking_qty,0)) AS kg_wb_ytd,
            COALESCE(avg_weight_ttd.avg_factory,0) AS avg_factory_ttd,
            COALESCE(avg_weight_mtd.avg_factory,0) AS avg_factory_mtd,
            COALESCE(avg_weight_ytd.avg_factory,0) AS avg_factory_ytd,
            COALESCE(remnant_ttd.remnant,0) AS remnant
        """
        return query_

    def _get_date_filter(self, params=None, field=""):
        date_filter = ""
        if params:
            date_filter = """
            AND DATE_TRUNC('%(params)s', %(date_field)s) =
                DATE_TRUNC('%(params)s', CAST('%(op_date)s' as DATE))
            AND %(date_field)s <= CAST('%(op_date)s' as DATE)
        """ % {
                "params": params,
                "op_date": self.date.strftime("%Y-%m-%d"),
                "date_field": field,
            }
        return date_filter

    def _query(self):
        day_filter = self._get_date_filter(params="day", field="eh.operation_date")
        month_filter = self._get_date_filter(params="month", field="eh.operation_date")
        year_filter = self._get_date_filter(params="year", field="eh.operation_date")
        day_remnant = self._get_date_filter(params="day", field="erl.restan_date")
        query = """
            WITH harvest_ttd AS (
                %(harvest_ttd)s
            ), picking_ttd AS (
                %(picking_ttd)s
            ), avg_weight_ttd AS (
                %(avg_weight_ttd)s
            ), remnant_ttd AS (
                %(remnant_ttd)s
            ), harvest_mtd AS (
                %(harvest_mtd)s
            ), picking_mtd AS (
                %(picking_mtd)s
            ), avg_weight_mtd AS (
                %(avg_weight_mtd)s
            ), harvest_ytd AS (
                %(harvest_ytd)s
            ), picking_ytd AS (
                %(picking_ytd)s
            ), avg_weight_ytd AS (
                %(avg_weight_ytd)s
            )
            SELECT
                %(header_query)s
            FROM
                estate_block eb
                RIGHT JOIN harvest_ytd ON harvest_ytd.id = eb.id
                FULL JOIN harvest_mtd ON harvest_mtd.id = harvest_ytd.id
                FULL JOIN harvest_ttd ON harvest_ttd.id = harvest_ytd.id
                FULL JOIN picking_ytd ON picking_ytd.id = harvest_ytd.id
                FULL JOIN picking_mtd ON picking_mtd.id = picking_ytd.id
                FULL JOIN picking_ttd ON picking_ttd.id = picking_ytd.id
                FULL JOIN avg_weight_ytd ON avg_weight_ytd.id = harvest_ytd.id
                FULL JOIN avg_weight_mtd ON avg_weight_mtd.id = avg_weight_ytd.id
                FULL JOIN avg_weight_ttd ON avg_weight_ttd.id = avg_weight_ytd.id
                FULL JOIN remnant_ttd ON remnant_ttd.id = harvest_ytd.id
            ORDER BY
	            eb.planting_year
        """ % {
            "header_query": self.header_query(),
            "harvest_ttd": self.harvest_query(day_filter),
            "picking_ttd": self.picking_query(day_filter),
            "avg_weight_ttd": self.avg_weight_query(day_filter),
            "remnant_ttd": self.remnant_query(day_remnant),
            "harvest_mtd": self.harvest_query(month_filter),
            "picking_mtd": self.picking_query(month_filter),
            "avg_weight_mtd": self.avg_weight_query(month_filter),
            "harvest_ytd": self.harvest_query(year_filter),
            "picking_ytd": self.picking_query(year_filter),
            "avg_weight_ytd": self.avg_weight_query(year_filter),
        }
        return query

    def print_report(self):
        self.ensure_one()
        query = self._query()

        self.env.cr.execute(query)
        data = self.env.cr.dictfetchall()

        if data:
            datas = {
                "ids": [],
                "model": "monitoring.bjr.report",
                "summary": data,
                "date": self.date,
                "estate": self.estate_id.code,
                "product": self.product_id.name,
            }

            return self.env.ref(
                "wi_base_farm_stock.monitoring_bjr_print_report"
            ).report_action([], data=datas)
        else:
            raise UserError(_("No data to print."))
