from odoo import api, fields, models


class EstateHarvestLabourLines(models.TransientModel):
    _name = "harvest.labour.lines"
    _description = "Harvest Labour Lines"

    harvest_operation = fields.Many2one("estate.operation")
    harvest_id = fields.Many2one("estate.harvest")
    prev_member_team = fields.Many2one(
        "hr.employee",
        domain=[("job_id.farm_data", "=", True)],
    )
    afdeling = fields.Many2one(
        "estate.estate",
        related="harvest_operation.afdeling_id",
    )
    team_member = fields.Many2one(
        "hr.employee",
        domain=[("job_id.farm_data", "=", True)],
        required=True,
    )
    block = fields.Many2one(
        "estate.block",
        required=True,
    )
    prev_block = fields.Many2one(
        "estate.block",
    )
    code_TPH = fields.Char()
    harvest_qty_unit = fields.Integer(
        required=True,
    )
    harvest_rates = fields.Float()
    harvest_area = fields.Float()
    other_harvest_qty = fields.Float()

    penalty = fields.One2many(
        "estate.harvest.labour.penalty.lines",
        "harvest",
        compute="_compute_penalty_prev",
        store=True,
        readonly=False,
    )
    planning_qty = fields.Integer()
    work_note = fields.Text()

    @api.depends("harvest_id")
    def _compute_penalty_prev(self):
        for rec in self:
            prev_penalty = rec.env.context.get("prev_penalty")
            rec.adding_penalty_record(prev_penalty)

    def adding_penalty_record(self, prev):
        if prev:
            penalty_mod = self.env["estate.harvest.labour.penalty.lines"]
            for id_rec, qty in prev:
                self.penalty += penalty_mod.create(
                    {"penalty_id": id_rec, "qty": qty, "harvest": self.id}
                )
        else:
            self.penalty = []

    def action_confirm(self):
        self.ensure_one()
        for rec in self.harvest_id.penalty_harvest_ids:
            rec.unlink()
        self.harvest_id.write(
            {
                "member_id": self.team_member.id,
                "harvest_qty_unit": self.harvest_qty_unit,
                "planning_qty": self.planning_qty,
                "work_note": self.work_note,
                "block_id": self.block.id,
                "tph_code": self.code_TPH,
                "harvest_area": self.harvest_area,
                "harvest_rates": self.harvest_rates,
                "other_harvest_qty": self.other_harvest_qty,
                "penalty_harvest_ids": [
                    (
                        0,
                        0,
                        {
                            "penalty_type_id": penalty.penalty_id.id,
                            "penalty_qty": penalty.qty,
                        },
                    )
                    for penalty in self.penalty
                ],
            }
        )
        harvest_labours = self.env["estate.harvest"].search(
            [("member_id", "=", self.team_member.id), ("block_id", "=", self.block.id)],
            order="id ASC",
        )
        self._recompute_labour(harvest_labours)

        if self.team_member != self.prev_member_team or self.block != self.prev_block:
            prev_harvest_labours = self.env["estate.harvest"].search(
                [
                    ("member_id", "=", self.prev_member_team.id),
                    ("block_id", "=", self.prev_block.id),
                ],
                order="id ASC",
            )
            self._recompute_labour(prev_harvest_labours)
        return {"type": "ir.actions.act_window_close"}

    def _recompute_labour(self, labours_ids):
        for labour in labours_ids:
            prev_harvest_qty = labour.harvest_qty_unit
            labour.write(
                {
                    "harvest_qty_unit": 0,
                }
            )
            labour.write(
                {
                    "harvest_qty_unit": prev_harvest_qty,
                }
            )

    def create_labour(self):
        self.ensure_one()
        self.harvest_operation.estate_harvest_ids.create(
            {
                "estate_operation_id": self.harvest_operation.id,
                "harvest_qty_unit": self.harvest_qty_unit,
                "member_id": self.team_member.id,
                "block_id": self.block.id,
                "tph_code": self.code_TPH,
                "harvest_area": self.harvest_area,
                "harvest_rates": self.harvest_rates,
                "other_harvest_qty": self.other_harvest_qty,
                "penalty_harvest_ids": [
                    (
                        0,
                        0,
                        {
                            "penalty_type_id": penalty.penalty_id.id,
                            "penalty_qty": penalty.qty,
                        },
                    )
                    for penalty in self.penalty
                ],
            }
        )
        harvest_labours = self.env["estate.harvest"].search(
            [("member_id", "=", self.team_member.id), ("block_id", "=", self.block.id)],
            order="id ASC",
        )
        self._recompute_labour(harvest_labours)
        return {"type": "ir.actions.act_window_close"}
