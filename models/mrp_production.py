from odoo import api, fields, models, _


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    employee_production_line_ids = fields.One2many(
        'ff.mrp.employee.production.line', 'production_id',
        string='Production Employees', copy=False)
    employee_production_qty = fields.Float(
        string='Total Assigned Employee Quantity',
        compute='_compute_employee_production_summary', store=True,
        digits='Product Unit')
    employee_unassigned_qty = fields.Float(
        string='Remaining Unassigned Quantity',
        compute='_compute_employee_production_summary', store=True,
        digits='Product Unit')
    employee_overassigned_qty = fields.Float(
        string='Over-assigned Quantity',
        compute='_compute_employee_production_summary', store=True,
        digits='Product Unit')
    employee_production_status = fields.Selection([
        ('draft', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('complete', 'Complete'),
        ('unassigned', 'Unassigned Quantity'),
        ('over_assigned', 'Over Assigned'),
        ('cancelled', 'Cancelled'),
    ], string='Employee Distribution Status',
        compute='_compute_employee_production_summary', store=True)
    employee_production_reportable = fields.Boolean(
        string='Eligible for Employee Production Report',
        compute='_compute_employee_production_summary', store=True, index=True)

    def _employee_production_workorders(self):
        self.ensure_one()
        return self.workorder_ids.filtered(lambda workorder: workorder.workcenter_id)

    @api.depends(
        'employee_production_line_ids.quantity',
        'qty_produced', 'state', 'product_uom_id',
        'move_finished_ids', 'move_finished_ids.quantity',
        'move_finished_ids.picked', 'move_finished_ids.state')
    def _compute_employee_production_summary(self):
        for production in self:
            assigned = sum(production.employee_production_line_ids.mapped('quantity'))
            actual = production.qty_produced or 0.0
            production.employee_production_qty = assigned
            production.employee_unassigned_qty = max(actual - assigned, 0.0)
            production.employee_overassigned_qty = max(assigned - actual, 0.0)
            if production.state == 'cancel':
                status = 'cancelled'
            elif actual == 0.0:
                status = 'draft' if not assigned else 'in_progress'
            elif production.product_uom_id.compare(assigned, actual) > 0:
                status = 'over_assigned'
            elif production.product_uom_id.compare(assigned, actual) < 0:
                status = 'unassigned'
            else:
                status = 'complete' if production.state == 'done' else 'in_progress'
            production.employee_production_status = status
            production.employee_production_reportable = (
                production.state == 'done' and status == 'complete')

    @api.onchange('employee_production_line_ids')
    def _onchange_employee_production_line_ids(self):
        for production in self:
            if production.employee_production_status == 'over_assigned':
                return {
                    'warning': {
                        'title': _('Employee quantities exceed production'),
                        'message': _(
                            'The assigned employee quantity is greater than the actual '
                            'manufactured quantity. Correct the distribution before reporting.'),
                    }
                }

    def copy(self, default=None):
        default = dict(default or {})
        default['employee_production_line_ids'] = []
        return super().copy(default)
