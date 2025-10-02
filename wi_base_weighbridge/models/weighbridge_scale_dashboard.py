import json
from ast import literal_eval
from datetime import date, timedelta

from babel.dates import format_date

from odoo import _, fields, models, tools
from odoo.release import version
from odoo.tools.misc import get_lang


class WeighbridgeScaleDashboard(models.Model):
    _name = "weighbridge.scale.dashboard"
    _description = "Weighbridge Scale Dashboard"
    _rec_name = "product_id"
    _auto = False

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
    )

    count = fields.Integer(
        string="Total Unit",
        group_operator="sum",
        readonly=True,
    )

    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product",
        help="Delivered/Received Product.",
    )

    kanban_dashboard = fields.Text(
        compute="_compute_kanban_dashboard",
    )

    kanban_dashboard_graph = fields.Text(
        compute="_compute_kanban_dashboard_graph",
    )

    def _compute_kanban_dashboard(self):
        dashboard_data = self._get_scale_dashboard_data()
        for product in self:
            product.kanban_dashboard = json.dumps(
                dashboard_data[product.product_id], default=str
            )

    def _query_get_data(
        self,
        product_id,
        company_id,
        last_month,
        today,
        select_clause="",
        from_clause="",
        where_clause="",
        group_by_clause="",
    ):
        _select = (
            """
            SELECT
                sum(net_after_quality_control) as net_after_quality_control,
                count(1),
                sum(net_weight) as net_weight
                %s
            """
            % select_clause
        )

        _from = (
            """
            FROM
                weighbridge_scale ws
                %s
            """
            % from_clause
        )

        _where = """
            WHERE
                product_id = %s
                AND company_id = %s
                AND date > '%s'
                AND date <= '%s'
                %s
            """ % (
            product_id,
            company_id,
            last_month,
            today,
            where_clause,
        )

        return "%s %s %s" % (_select, _from, _where)

    def _get_scale_dashboard_data(self):
        today = date.today()
        last_month = today + timedelta(days=-30)

        dashboard_data = {}
        for product in self:
            query = self._query_get_data(
                product.id, self.env.company.id, last_month, today
            )
            self.env.cr.execute(query)
            result = self.env.cr.dictfetchall()
            dashboard_data[product.product_id] = {
                "company_count": len(self.env.companies),
                "net_after_quality_control": result[0]["net_after_quality_control"]
                if result[0]["net_after_quality_control"] is not None
                else 0,
                "count": "{:,.2f}".format(result[0]["count"])
                if result[0]["count"] is not None
                else "0.00",
                "net_weight": "{:,.2f}".format(result[0]["net_weight"])
                if result[0]["net_weight"] is not None
                else "0.00",
            }

        return dashboard_data

    def _compute_kanban_dashboard_graph(self):
        dashboard_graph_data = self._get_scale_dashboard_graph_data()
        for product in self:
            product.kanban_dashboard_graph = json.dumps(
                dashboard_graph_data[product.product_id], default=str
            )

    def _get_scale_dashboard_graph_data(self):
        def build_graph_data(date, net_after_qc):
            name = format_date(date, "d LLLL Y", locale=locale)
            short_name = format_date(date, "d MMM", locale=locale)
            return {"x": short_name, "y": net_after_qc, "name": name}

        today = date.today()
        last_month = today + timedelta(days=-30)
        locale = get_lang(self.env).code

        query = """
            SELECT
                ws.date,
                sum(net_after_quality_control) as net_after_quality_control
            FROM
                weighbridge_scale ws
            WHERE
                product_id = %s
                AND company_id = %s
                AND date > %s
                AND date <= %s
            GROUP BY
                ws.date
            ORDER BY
                ws.date asc
        """

        dashboard_graph_data = {}
        for product in self:
            self.env.cr.execute(
                query, (product.id, self.env.company.id, last_month, today)
            )
            result = self.env.cr.dictfetchall()

            graph_title, graph_key = product._graph_title_and_key()
            color = "#875A7B" if "e" in version else "#7c7bad"

            data = []
            if len(result) == 0:
                data.append(build_graph_data(last_month, 0))
                data.append(build_graph_data(today, 0))
            elif len(result) == 1:
                data.append(build_graph_data(last_month, 0))
                data.append(
                    build_graph_data(
                        result[0]["date"], result[0]["net_after_quality_control"]
                    )
                )
            else:
                for i in range(0, len(result)):
                    data.append(
                        build_graph_data(
                            result[i]["date"], result[i]["net_after_quality_control"]
                        )
                    )

            dashboard_graph_data[product.product_id] = [
                {
                    "values": data,
                    "title": graph_title,
                    "key": graph_key,
                    "color": color,
                    "area": True,
                }
            ]

        return dashboard_graph_data

    def _graph_title_and_key(self):
        return ["", _("Net After Quality Control")]

    def _query(self):
        select_ = """
            ws.product_id as id,
            count(1),
            ws.product_id,
            ws.company_id
        """

        from_ = """
            weighbridge_scale ws
        """

        group_by_ = """
            ws.company_id,
            ws.product_id
        """

        return "(SELECT %s FROM %s GROUP BY %s)" % (select_, from_, group_by_)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """CREATE or REPLACE VIEW %s as (%s)""" % (self._table, self._query())
        )

    def _get_last_31_days(self):
        today = date.today()
        last_month = today + timedelta(days=-30)
        return last_month, today

    def open_action(self):
        return self._get_action("wi_base_weighbridge.action_weighbridge_scale_view")

    def _get_action(self, action_xmlid):
        action = self.env["ir.actions.actions"]._for_xml_id(action_xmlid)
        if self:
            action["display_name"] = "Weighbridge Scale - %s" % self.product_id.name
        context = {
            "default_product_id": self.product_id.id,
            "default_company_id": self.company_id.id,
            "search_default_last_days": 1,
            "search_default_year": 0,
        }
        action_context = literal_eval(action["context"])
        context = {**action_context, **context}
        action["domain"] = [("product_id", "=", self.product_id.id)]
        action["context"] = context
        return action
