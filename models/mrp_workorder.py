from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    employee_session_ids = fields.One2many('ff.mrp.employee.workorder.session', 'workorder_id', string='Employee Sessions', copy=False)
    employee_session_count = fields.Integer(compute='_compute_employee_session_count')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    employee_hours = fields.Float(compute='_compute_employee_session_totals', store=True, digits=(16, 2))
    employee_cost = fields.Monetary(compute='_compute_employee_session_totals', store=True, currency_field='currency_id')
    employee_produced_quantity = fields.Float(
        string='Employee Produced Quantity', compute='_compute_employee_session_totals',
        store=True, digits='Product Unit')

    def _current_production_employee(self):
        return self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)

    def button_start(self):
        """Keep the native Odoo Play action and create its employee session."""
        result = super().button_start()
        if self.env.context.get('skip_employee_session_sync'):
            return result
        employee = self._current_production_employee()
        if not employee:
            return result
        session_model = self.env['ff.mrp.employee.workorder.session']
        for workorder in self:
            if workorder.workcenter_id.employee_ids and employee not in workorder.workcenter_id.employee_ids:
                raise UserError(_('You are not an allowed employee for work center %s.') % workorder.workcenter_id.display_name)
            if not session_model.search_count([
                ('workorder_id', '=', workorder.id),
                ('employee_id', '=', employee.id),
                ('state', '=', 'running'),
            ]):
                session_model.create({
                    'workorder_id': workorder.id,
                    'employee_id': employee.id,
                })
        return result

    def action_start_employee_session(self):
        self.ensure_one()
        employee = self._current_production_employee()
        if not employee:
            raise UserError(_('Your user is not linked to an employee.'))
        if self.workcenter_id.employee_ids and employee not in self.workcenter_id.employee_ids:
            raise UserError(_('You are not an allowed employee for work center %s.') % self.workcenter_id.display_name)
        if self.env['ff.mrp.employee.workorder.session'].search_count([
            ('employee_id', '=', employee.id), ('state', '=', 'running')]):
            raise UserError(_('You already have a running work-order session.'))
        # Use Odoo's native work-order timer as the source of truth for the
        # operator's work time.  The employee session is an additional
        # per-employee costing layer, not a second independent timer.
        self.button_start()
        session = self.env['ff.mrp.employee.workorder.session'].search([
            ('workorder_id', '=', self.id),
            ('employee_id', '=', employee.id),
            ('state', '=', 'running'),
        ], limit=1)
        if not session:
            session = self.env['ff.mrp.employee.workorder.session'].create({
                'workorder_id': self.id, 'employee_id': employee.id,
            })
        return {
            'type': 'ir.actions.act_window', 'name': _('Employee Work Session'),
            'res_model': 'ff.mrp.employee.workorder.session', 'view_mode': 'form',
            'res_id': session.id, 'target': 'current',
        }

    def _stop_running_employee_sessions(self, employee=None):
        if employee is None:
            employee = self.env['hr.employee'].search(
                [('user_id', '=', self.env.user.id)], limit=1)
        sessions = self.mapped('employee_session_ids').filtered(
            lambda s: s.state == 'running' and (employee is False or s.employee_id == employee))
        if sessions:
            sessions.with_context(skip_standard_timer_sync=True).action_stop()

    def button_pending(self):
        result = super().button_pending()
        if not self.env.context.get('skip_employee_session_sync'):
            self._stop_running_employee_sessions()
        return result

    def button_finish(self):
        # Finishing an operation closes every employee session on it, even
        # when the action is performed by a supervisor rather than an operator.
        self._stop_running_employee_sessions(employee=False)
        return super().button_finish()

    def _compute_employee_session_count(self):
        grouped = self.env['ff.mrp.employee.workorder.session']._read_group([('workorder_id', 'in', self.ids)], ['workorder_id'], ['__count'])
        counts = {workorder.id: count for workorder, count in grouped}
        for workorder in self:
            workorder.employee_session_count = counts.get(workorder.id, 0)

    @api.depends(
        'employee_session_ids.duration_hours',
        'employee_session_ids.cost_amount',
        'employee_session_ids.produced_quantity',
        'employee_session_ids.state',
    )
    def _compute_employee_session_totals(self):
        for workorder in self:
            sessions = workorder.employee_session_ids.filtered(lambda s: s.state != 'cancelled')
            workorder.employee_hours = sum(sessions.mapped('duration_hours'))
            workorder.employee_cost = sum(sessions.mapped('cost_amount'))
            workorder.employee_produced_quantity = sum(sessions.mapped('produced_quantity'))
