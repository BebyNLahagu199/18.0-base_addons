from datetime import date

from odoo import _, fields, models
from odoo.exceptions import UserError


class CostProductionReport(models.TransientModel):
    _name = "cost.production.report"
    _description = "Cost Production Report"

    date = fields.Date(default=date.today(), required=True)
    estate_id = fields.Many2one(
        "estate.estate", required=True, domain="[('location_type','=','estate')]"
    )

    def print_report(self):
        self.ensure_one()
        localstr = """
            SELECT
                eb.code,
                eb.planting_year,
                eb.total_area,
                eps.name AS planting_state,
                COALESCE(MAX(_data.production_ttd),0) AS production_ttd,
                COALESCE(MAX(_data.production_mtd),0) AS production_mtd,
                COALESCE(MAX(_data.production_ytd),0) AS production_ytd,
                COALESCE(MAX(_data.harvest_ttd),0) AS harvest_ttd,
                COALESCE(MAX(_data.upkeep_ttd),0) AS upkeep_ttd,
                COALESCE(MAX(_data.harvest_ttd),0) + COALESCE(MAX(_data.upkeep_ttd),0)
                AS total_ttd,
                COALESCE(MAX(_data.harvest_mtd),0) AS harvest_mtd,
                COALESCE(MAX(_data.upkeep_mtd),0) AS upkeep_mtd,
                COALESCE(MAX(_data.harvest_mtd),0) + COALESCE(MAX(_data.upkeep_mtd),0)
                AS total_mtd,
                COALESCE(MAX(_data.harvest_ytd),0) AS harvest_ytd,
                COALESCE(MAX(_data.upkeep_ytd),0) AS upkeep_ytd,
                COALESCE(MAX(_data.harvest_ytd),0) + COALESCE(MAX(_data.upkeep_ytd),0)
                AS total_ytd
            FROM
                (
                    SELECT
                        COALESCE(production.id, harvesting.id, upkeeping.id) AS id,
                        production.production_ttd,
                        production.production_mtd,
                        production.production_ytd,
                        harvesting.harvest_ttd,
                        harvesting.harvest_mtd,
                        harvesting.harvest_ytd,
                        upkeeping.upkeep_ttd,
                        upkeeping.upkeep_mtd,
                        upkeeping.upkeep_ytd
                    FROM
                    (
                        SELECT
                            production_year.id,
                            production_today.production_ttd,
                            production_month.production_mtd,
                            production_year.production_ytd
                        FROM
                            (
                                SELECT
                                    eb.id,
                                    SUM(harvest_qty_weight + other_harvest_stock_qty)
                                    AS production_ytd
                                FROM
                                    estate_harvest eh
                                    JOIN estate_block eb ON eh.block_id = eb.id
                                WHERE
                                    DATE_TRUNC('year', operation_date) =
                                    DATE_TRUNC('year', CAST(%(op_date)s as DATE))
                                    AND operation_date <= CAST(%(op_date)s as DATE)
			                        AND eh.state in ('posted','done')
                                GROUP BY
                                    eb.id
                            ) production_year
                            FULL JOIN
                            (
                                SELECT
                                    eb.id,
                                    SUM(harvest_qty_weight + other_harvest_stock_qty)
                                    AS production_mtd
                                FROM
                                    estate_harvest eh
                                    JOIN estate_block eb ON eh.block_id = eb.id
                                WHERE
                                    DATE_TRUNC('month', operation_date) =
                                    DATE_TRUNC('month', CAST(%(op_date)s as DATE))
                                    AND operation_date <= CAST(%(op_date)s as DATE)
			                        AND eh.state in ('posted','done')
                                GROUP BY
                                    eb.id
                            ) production_month
                            ON production_year.id = production_month.id
                            FULL JOIN
                            (
                                SELECT
                                    eb.id,
                                    SUM(harvest_qty_weight + other_harvest_stock_qty)
                                    AS production_ttd
                                FROM
                                    estate_harvest eh
                                    JOIN estate_block eb ON eh.block_id = eb.id
                                WHERE
                                    DATE_TRUNC('day', operation_date) =
                                    DATE_TRUNC('day', CAST(%(op_date)s as DATE))
                                    AND operation_date <= CAST(%(op_date)s as DATE)
			                        AND eh.state in ('posted','done')
                                GROUP BY
                                    eb.id
                            ) production_today
                            ON production_year.id = production_today.id
                    ) production
                    FULL JOIN
                    (
                        SELECT
                            harvest_year.id,
                            harvest_today.harvest_ttd,
                            harvest_month.harvest_mtd,
                            harvest_year.harvest_ytd
                        FROM
                            (
                                SELECT
                                    eb.id,
                                    SUM(total_include_penalty) AS harvest_ytd
                                FROM
                                    estate_harvest eh
                                    JOIN estate_block eb ON eh.block_id = eb.id
                                WHERE
                                    DATE_TRUNC('year', operation_date) =
                                    DATE_TRUNC('year', CAST(%(op_date)s as DATE))
                                    AND operation_date <= CAST(%(op_date)s as DATE)
			                        AND eh.state in ('posted','done')
                                GROUP BY
                                    eb.id
                            ) harvest_year
                            FULL JOIN
                            (
                                SELECT
                                    eb.id,
                                    SUM(total_include_penalty) AS harvest_mtd
                                FROM
                                    estate_harvest eh
                                    JOIN estate_block eb ON eh.block_id = eb.id
                                WHERE
                                    DATE_TRUNC('month', operation_date) =
                                    DATE_TRUNC('month', CAST(%(op_date)s as DATE))
                                    AND operation_date <= CAST(%(op_date)s as DATE)
			                        AND eh.state in ('posted','done')
                                GROUP BY
                                    eb.id
                            ) harvest_month
                            ON harvest_year.id = harvest_month.id
                            FULL JOIN
                            (
                                SELECT
                                    eb.id,
                                    SUM(total_include_penalty) AS harvest_ttd
                                FROM
                                    estate_harvest eh
                                    JOIN estate_block eb ON eh.block_id = eb.id
                                WHERE
                                    DATE_TRUNC('day', operation_date) =
                                    DATE_TRUNC('day', CAST(%(op_date)s as DATE))
                                    AND operation_date <= CAST(%(op_date)s as DATE)
			                        AND eh.state in ('posted','done')
                                GROUP BY
                                    eb.id
                            ) harvest_today
                            ON harvest_year.id = harvest_today.id
                    ) harvesting
                    ON production.id = harvesting.id
                    FULL JOIN
                    (
                        SELECT
                            upkeep_year.id,
                            upkeep_today.upkeep_ttd,
                            upkeep_month.upkeep_mtd,
                            upkeep_year.upkeep_ytd
                        FROM
                            (
                                SELECT
                                    eb.id,
                                    SUM(total_amount) AS upkeep_ytd
                                FROM
                                    estate_upkeep_labour eul
                                    JOIN estate_block eb ON eul.location_id = eb.id
                                WHERE
                                    DATE_TRUNC('year', operation_date) =
                                    DATE_TRUNC('year', CAST(%(op_date)s as DATE))
                                    AND operation_date <= CAST(%(op_date)s as DATE)
			                        AND eul.state in ('posted','done')
                                GROUP BY
                                    eb.id
                            ) upkeep_year
                            FULL JOIN
                            (
                                SELECT
                                    eb.id,
                                    SUM(total_amount) AS upkeep_mtd
                                FROM
                                    estate_upkeep_labour eul
                                    JOIN estate_block eb ON eul.location_id = eb.id
                                WHERE
                                    DATE_TRUNC('month', operation_date) =
                                    DATE_TRUNC('month', CAST(%(op_date)s as DATE))
                                    AND operation_date <= CAST(%(op_date)s as DATE)
			                        AND eul.state in ('posted','done')
                                GROUP BY
                                    eb.id
                            ) upkeep_month
                            ON upkeep_year.id = upkeep_month.id
                            FULL JOIN
                            (
                                SELECT
                                    eb.id,
                                    SUM(total_amount) AS upkeep_ttd
                                FROM
                                    estate_upkeep_labour eul
                                    JOIN estate_block eb ON eul.location_id = eb.id
                                WHERE
                                    DATE_TRUNC('day', operation_date) =
                                    DATE_TRUNC('day', CAST(%(op_date)s as DATE))
                                    AND operation_date <= CAST(%(op_date)s as DATE)
			                        AND eul.state in ('posted','done')
                                GROUP BY
                                    eb.id
                            ) upkeep_today
                            ON upkeep_year.id = upkeep_today.id
                    ) upkeeping
                ON production.id = upkeeping.id) _data
                LEFT JOIN estate_block eb ON eb.id = _data.id
                LEFT JOIN estate_estate ee ON eb.estate_id = ee.id
                LEFT JOIN estate_planting_state eps ON eb.planting_state_id = eps.id
                LEFT JOIN estate_harvest eh ON eb.id = eh.block_id
                LEFT JOIN estate_upkeep_labour eul ON eb.id = eul.location_id
            WHERE
                ee.parent_id = %(estate_id)s
            GROUP BY
                eb.id,
                ee.id,
                eps.id
            ORDER BY
                ee.id
        """

        self.env.cr.execute(
            localstr,
            {
                "op_date": self.date.strftime("%Y-%m-%d"),
                "estate_id": self.estate_id.id,
            },
        )
        data = self.env.cr.dictfetchall()

        if data:
            datas = {
                "ids": [],
                "model": "cost.production.report",
                "summary": data,
                "date": self.date,
                "estate": self.estate_id.code,
            }

            return self.env.ref(
                "wi_base_farm.cost_production_print_report"
            ).report_action([], data=datas)
        else:
            raise UserError(_("No data to print."))
