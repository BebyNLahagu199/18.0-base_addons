from datetime import date, timedelta

from odoo import api, fields, models

RANGE_6_MONTHS = (
    date.today().strftime("%Y-%m-%d"),
    (date.today() - timedelta(weeks=24)).strftime("%Y-%m-%d"),
)


class EstateBlock(models.Model):
    _name = "estate.block"
    _inherit = ["estate.block", "web.maps.mixin"]

    web_maps_data = fields.Json(compute="_compute_maps_data")

    def _get_block_ids_tuple(self, block_id):
        """Mengembalikan tuple ID blok."""
        return tuple([block_id]) if not isinstance(block_id, list) else tuple(block_id)

    def _execute_query(self, query, params):
        """Menjalankan query dan mengembalikan hasilnya."""
        self.env.cr.execute(query, params)
        return self.env.cr.dictfetchall()

    def _prepare_query_params(self, date_from, date_to, block_id):
        """Menyiapkan parameter untuk query."""
        return {
            "fromDate": date_from,
            "toDate": date_to,
            "block_id": self._get_block_ids_tuple(block_id),
        }

    def _fetch_data(self, date_range, block_id):
        """Mengambil data dari database."""
        query = """
        SELECT
            harvest_main_product_id,
            harvest_other_product_id,
            to_char(operation_date, 'YYYY-MM') AS month,
            SUM(harvest_qty_weight + other_harvest_stock_qty) AS total_weight,
            CASE WHEN
                SUM(harvest_qty_unit) <> 0
                THEN ROUND((SUM(harvest_qty_weight)/SUM(harvest_qty_unit))::numeric, 2)
                ELSE 0 END
            AS avg_harvest_weight,
            CASE WHEN
                SUM(other_harvest_qty) <> 0
                THEN ROUND((
                    SUM(other_harvest_stock_qty)/SUM(other_harvest_qty)
                    )::numeric, 2)
                ELSE 0 END
            AS avg_other_harvest_weight
        FROM
            estate_harvest
        WHERE
            operation_date BETWEEN %(fromDate)s AND %(toDate)s
            AND block_id IN %(block_id)s
        GROUP BY
            to_char(operation_date, 'YYYY-MM'),
            harvest_main_product_id,
            harvest_other_product_id
        ORDER BY
            to_char(operation_date, 'YYYY-MM');
        """
        params = self._prepare_query_params(date_range[1], date_range[0], block_id)
        return self._execute_query(query, params)

    def _prepare_data(self, date_range, rec_id):
        result = self._fetch_data(date_range, rec_id)
        data_result = {"monthly": []}
        if result:
            for data in result:
                main_product = (
                    self.env["product.product"]
                    .browse(data["harvest_main_product_id"])
                    .name
                )

                other_product = (
                    self.env["product.product"]
                    .browse(data["harvest_other_product_id"])
                    .name
                )
                data["harvest_main_product_id"] = main_product
                data["harvest_other_product_id"] = other_product
                data_result["monthly"].append(data)
            today_data = self._fetch_data(
                (
                    date.today().strftime("%Y-%m-%d"),
                    date.today().strftime("%Y-%m-%d"),
                ),
                rec_id,
            )
            if today_data:
                data_result["today"] = today_data[0]
            return data_result
        else:
            return {}

    @api.depends("coordinate", "analytic_account_id")
    def _compute_maps_data(self, date_range=RANGE_6_MONTHS):
        for rec in self:
            block = rec.env.ref("wi_base_farm.analytic_plan_block")
            block_column = block._column_name()
            analytic_balance = rec.env["account.analytic.line"].search(
                [
                    (block_column, "=", rec.analytic_account_id.id),
                    ("date", ">=", date_range[1]),
                    ("date", "<=", date_range[0]),
                ],
                order="date",
            )
            rec.web_maps_data = {
                "total_tree_qty": rec.total_tree,
                "weight_data": self._prepare_data(date_range, rec.id)
                if rec.location_latitude or rec.location_longitude
                else {},
                "analytic_balance": rec.grouping_rec_by_month(analytic_balance),
                "total_harvest_uom_qty": rec.total_harvest_uom_qty,
                "average_weight": rec.average_weight,
                "total_area": rec.total_area,
                "contact_address_complete": rec.contact_address_complete,
            }

    def grouping_rec_by_month(self, recs):
        """Mengelompokkan data analytic line berdasarkan bulan."""
        result = {}
        for rec in recs:
            date = rec["date"]
            month = date.strftime("%Y-%m")
            if month not in result:
                result[month] = 0
            result[month] += rec.amount
        return result
