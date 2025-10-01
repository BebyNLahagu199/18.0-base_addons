from odoo import fields, models, tools


class EstatePickingReport(models.Model):
    _name = "estate.picking.report"
    _description = "Estate Picking Report"
    _auto = False

    scheduled_date = fields.Date("Date", readonly=True)
    picking_id = fields.Many2one("estate.picking", "Picking", readonly=True)
    block_id = fields.Many2one("estate.block", "Block", readonly=True)
    vehicle = fields.Char("Licence Plate", readonly=True)
    ticket_id = fields.Many2one("estate.harvest", "Harvest", readonly=True)
    harvest_qty_unit = fields.Integer("Harvest Qty", readonly=True)
    harvest_qty_weight = fields.Float("Harvest Weight", readonly=True)
    other_harvest_qty = fields.Float(readonly=True)
    other_harvest_stock_qty = fields.Float(readonly=True)
    additional_weight = fields.Float(readonly=True)
    unload_weight = fields.Float(readonly=True)
    total_harvest_qty = fields.Float(readonly=True)
    total_other_harvest_qty = fields.Float(readonly=True)

    def _query(self, fields="", from_clause="", where_clause="", orderby_clause=""):
        select_ = (
            """
                eh.id,
                ep.scheduled_date,
                ep.id as picking_id,
                eh.block_id,
                ep.vehicle,
                eh.id as ticket_id,
                eh.harvest_qty_unit,
                eh.harvest_qty_weight,
                eh.other_harvest_qty,
                eh.other_harvest_stock_qty,
                ep.additional_weight,
                ep.unload_weight,
                ep.total_harvest_qty,
                ep.total_other_harvest_qty
            %s
        """
            % fields
        )

        from_ = (
            """
                estate_picking ep
	            inner join estate_harvest eh on ep.id = eh.picking_id
            %s
        """
            % from_clause
        )

        where_ = (
            """
                ep.state not in ('draft', 'cancel')
            %s
        """
            % where_clause
        )

        orderby_ = (
            """
                ep.scheduled_date
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
