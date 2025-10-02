/** @odoo-module **/

import dom from "@web/legacy/js/core/dom";
import publicWidget from "@web/legacy/js/public/public_widget";
import PortalSidebar from "@portal/js/portal_sidebar";

publicWidget.registry.WeighbridgePortalSidebar = PortalSidebar.extend({
    selector: ".o_portal_weighbridge_sidebar",
    events: {
        "click .o_portal_weighbridge_print": "_onPrintWeighbridgeTicket",
    },

    /**
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);

        var $TicketHtml = this.$el.find("iframe#weighbridge_ticket_html");
        var updateIframeSize = this._updateIframeSize.bind(this, $TicketHtml);

        $(window).on("resize", updateIframeSize);

        var iframeDoc =
            $TicketHtml[0].contentDocument || $TicketHtml[0].contentWindow.document;
        if (iframeDoc.readyState === "complete") {
            updateIframeSize();
        } else {
            $TicketHtml.on("load", updateIframeSize);
        }

        return def;
    },

    // --------------------------------------------------------------------------
    // Handlers
    // --------------------------------------------------------------------------

    /**
     * Called when the iframe is loaded or the window is resized on customer portal.
     * The goal is to expand the iframe height to display the full report without scrollbar.
     *
     * @private
     * @param {Object} $el: the iframe
     */
    _updateIframeSize: function ($el) {
        var $wrapwrap = $el.contents().find("div#wrapwrap");
        // Set it to 0 first to handle the case where scrollHeight is too big for its content.
        $el.height(0);
        $el.height($wrapwrap[0].scrollHeight);

        // Scroll to the right place after iframe resize
        const isAnchor = /^#[\w-]+$/.test(window.location.hash);
        if (!isAnchor) {
            return;
        }
        var $target = $(window.location.hash);
        if (!$target.length) {
            return;
        }
        dom.scrollTo($target[0], {duration: 0});
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onPrintWeighbridgeTicket: function (ev) {
        ev.preventDefault();
        var href = $(ev.currentTarget).attr("href");
        this._printIframeContent(href);
    },
});
