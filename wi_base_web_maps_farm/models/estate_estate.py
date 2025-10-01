from datetime import date, timedelta

from odoo import api, fields, models


def get_6_months_range():
    # Mendapatkan rentang tanggal 6 bulan ke belakang dari hari ini.
    # Get the date range of the last 6 months from today.
    return (
        date.today().strftime("%Y-%m-%d"),
        (date.today() - timedelta(weeks=24)).strftime("%Y-%m-%d"),
    )


class EstateEstate(models.Model):
    _name = "estate.estate"
    _inherit = ["estate.estate", "web.maps.mixin"]

    web_maps_data = fields.Json(compute="_compute_maps_data")

    def _get_query(self):
        # Mengembalikan query SQL untuk mengambil data panen.
        # Returns the SQL query to fetch harvest data.
        return """
            SELECT
                harvest_main_product_id,
                harvest_other_product_id,
                TO_CHAR(operation_date, 'YYYY-MM') AS month,
                SUM(harvest_qty_weight + other_harvest_stock_qty) AS total_weight,
                CASE WHEN
                    SUM(harvest_qty_unit) <> 0
                    THEN ROUND((
                        SUM(harvest_qty_weight)/SUM(harvest_qty_unit)
                        )::numeric, 2)
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
                AND afdeling_id IN %(afdeling_id)s
            GROUP BY
                TO_CHAR(operation_date, 'YYYY-MM'),
                harvest_main_product_id,
                harvest_other_product_id
            ORDER BY
                TO_CHAR(operation_date, 'YYYY-MM');
        """

    def _get_product_name(self, product_id):
        # Mengambil nama produk berdasarkan ID produk.
        # Fetches the product name based on the product ID.
        return self.env["product.product"].browse(product_id).name

    def _execute_query(self, date_range, afdeling_ids):
        # Menjalankan query SQL dengan parameter yang diberikan.
        # Executes the SQL query with the given parameters.
        self.env.cr.execute(
            self._get_query(),
            {
                "fromDate": date_range[1],
                "toDate": date_range[0],
                "afdeling_id": tuple(afdeling_ids)
                if isinstance(afdeling_ids, list)
                else tuple([afdeling_ids]),
            },
        )
        return self.env.cr.dictfetchall()

    def _prepare_data(self, date_range, rec):
        data_result = {"monthly": []}
        afdeling_ids = rec.child_ids.ids if rec.child_ids else [rec.id]
        result = self._execute_query(date_range, afdeling_ids)
        if result:
            for data in result:
                data["harvest_main_product_id"] = self._get_product_name(
                    data["harvest_main_product_id"]
                )
                data["harvest_other_product_id"] = self._get_product_name(
                    data["harvest_other_product_id"]
                )
                data_result["monthly"].append(data)
            today_data = self._execute_query(
                (
                    date.today().strftime("%Y-%m-%d"),
                    date.today().strftime("%Y-%m-%d"),
                ),
                afdeling_ids,
            )
            if today_data:
                data_result["today"] = today_data[0]
            return data_result
        else:
            return {}

    @api.depends("name", "block_ids", "date_localization")
    def _compute_maps_data(self):
        # Menghitung data untuk grafik berdasarkan lokalitas tanggal dan blok.
        # Computes data for the chart based on date localization and blocks.
        date_range = get_6_months_range()
        for rec in self:
            block = rec.env.ref("wi_base_farm.analytic_plan_block")
            block_column = block._column_name()
            block_ids = rec.get_block_ids()
            aa_id = block_ids.mapped("analytic_account_id").ids
            analytic_balance = rec.env["account.analytic.line"].search(
                [
                    (block_column, "in", aa_id),
                    ("date", ">=", date_range[1]),
                    ("date", "<=", date_range[0]),
                ],
                order="date",
            )
            rec.web_maps_data = {
                "total_tree_qty": rec.total_tree_qty,
                "weight_data": self._prepare_data(date_range, rec)
                if rec.location_latitude or rec.location_longitude
                else {},
                "analytic_balance": rec.grouping_rec_by_month(analytic_balance),
                "total_harvest_uom_qty": rec.total_harvest_uom_qty,
                "average_weight": rec.average_weight,
                "total_area": rec.total_area,
                "contact_address_complete": rec.contact_address_complete,
            }

    def get_block_ids(self):
        # Mengambil blok ID dari estate atau afdeling.
        if self.location_type == "estate":
            return self.child_ids.mapped("block_ids")
        else:
            return self.block_ids

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
