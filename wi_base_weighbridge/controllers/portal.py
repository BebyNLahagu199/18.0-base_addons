# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from collections import OrderedDict

from odoo import http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.tools import image_process
from odoo.tools.translate import _

from odoo.addons.portal.controllers import portal
from odoo.addons.portal.controllers.portal import (
    get_records_pager,
)
from odoo.addons.portal.controllers.portal import (
    pager as portal_pager,
)


class CustomerPortal(portal.CustomerPortal):
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        WeighbridgeScale = request.env["weighbridge.scale"]
        if "wb_scale_count" in counters:
            values["wb_scale_count"] = (
                WeighbridgeScale.search_count([])
                if WeighbridgeScale.check_access_rights("read", raise_exception=False)
                else 0
            )

        return values

    def _prepare_weighbridge_domain(self, partner):
        return [
            ("partner_id", "in", [partner.commercial_partner_id.id]),
        ]

    def _get_weighbridge_searchbar_sortings(self):
        return {
            "date": {"label": _("Date"), "order": "date desc"},
            "name": {"label": _("Reference"), "order": "name"},
            "stage": {"label": _("Stage"), "order": "state"},
        }

    def _get_weighbridge_searchbar_filters(self):
        return {
            "all": {"label": _("All"), "domain": []},
            "acceptance": {
                "label": _("Acceptance"),
                "domain": [("delivery_type", "=", "acceptance")],
            },
            "shipment": {
                "label": _("Shipment"),
                "domain": [("delivery_type", "=", "shipment")],
            },
        }

    def _prepare_weighbridge_portal_rendering_values(
        self,
        page=1,
        date_begin=None,
        date_end=None,
        sortby=None,
        filterby=None,
        **kwargs,
    ):
        Weighbridge = request.env["weighbridge.scale"]

        if not sortby:
            sortby = "date"
        partner = request.env.user.partner_id
        values = self._prepare_portal_layout_values()

        url = "/my/weighbridge"
        domain = self._prepare_weighbridge_domain(partner)
        searchbar_sortings = self._get_weighbridge_searchbar_sortings()

        if not filterby:
            filterby = "all"
        searchbar_filter = self._get_weighbridge_searchbar_filters()
        domain += searchbar_filter[filterby]["domain"]
        sort_order = searchbar_sortings[sortby]["order"]

        if date_begin and date_end:
            domain += [
                ("create_date", ">", date_begin),
                ("create_date", "<=", date_end),
            ]

        pager_values = portal_pager(
            url=url,
            total=Weighbridge.search_count(domain),
            page=page,
            step=self._items_per_page,
            url_args={"date_begin": date_begin, "date_end": date_end, "sortby": sortby},
        )
        scales = Weighbridge.search(
            domain,
            order=sort_order,
            limit=self._items_per_page,
            offset=pager_values["offset"],
        )

        values.update(
            {
                "date": date_begin,
                "scales": scales,
                "page_name": "weighbridge",
                "pager": pager_values,
                "default_url": url,
                "searchbar_sortings": searchbar_sortings,
                "sortby": sortby,
                "searchbar_filters": OrderedDict(searchbar_filter.items()),
                "filterby": filterby,
            }
        )

        return values

    @http.route(
        ["/my/weighbridge", "/my/weighbridge/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_weighbridge(self, **kwargs):
        values = self._prepare_weighbridge_portal_rendering_values(**kwargs)
        request.session["my_weighbridge_scale_history"] = values["scales"].ids[:100]
        return request.render("wi_base_weighbridge.portal_my_weighbridge", values)

    @http.route(
        ["/my/weighbridge/<int:scale_id>"], type="http", auth="public", website=True
    )
    def portal_my_weighbridge_scale(
        self, scale_id, access_token=None, message=False, **kw
    ):
        try:
            scale_sudo = self._document_check_access(
                "weighbridge.scale", scale_id, access_token=access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")

        report_type = kw.get("report_type")
        if report_type in ("html", "pdf", "text"):
            return self._show_report(
                model=scale_sudo,
                report_type=report_type,
                report_ref="wi_base_weighbridge.action_report_weighbridge_scale",
                download=kw.get("download"),
            )
        values = {
            "scale": scale_sudo,
            "message": message,
            "token": access_token,
            "page_name": "weighbridge",
            "bootstrap_formatting": True,
            "partner_id": scale_sudo.partner_id.id,
            "report_type": "html",
        }
        values = self._weighbridge_get_page_view_values(scale_sudo, access_token, **kw)

        history = request.session.get("my_weighbridge_scale_history", [])
        values.update(get_records_pager(history, scale_sudo))

        return request.render("wi_base_weighbridge.portal_my_weighbridge_scale", values)

    def _weighbridge_get_page_view_values(self, scale, access_token, **kwargs):
        #
        def resize_to_48(source):
            if not source:
                source = request.env["ir.binary"]._placeholder()
            else:
                source = base64.b64decode(source)
            return base64.b64encode(image_process(source, size=(48, 48)))

        values = {
            "scale": scale,
            "resize_to_48": resize_to_48,
            "report_type": "html",
        }
        return self._get_page_view_values(
            scale, access_token, values, False, False, **kwargs
        )
