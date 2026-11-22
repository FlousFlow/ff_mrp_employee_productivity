from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class FfMrpEmployeeWorkorderSession(models.Model):
    _name = 'ff.mrp.employee.workorder.session'
    _description = 'Employee Work Order Session'
    _order = 'started_at desc, id desc'
    _check_company_auto = True

    workorder_id = fields.Many2one('mrp.workorder', required=True, ondelete='cascade', index=True, check_company=True)
    production_id = fields.Many2one('mrp.production', related='workorder_id.production_id', store=True, readonly=True, index=True)
    workcenter_id = fields.Many2one('mrp.workcenter', related='workorder_id.workcenter_id', store=True, readonly=True, index=True)
    employee_id = fields.Many2one('hr.employee', required=True, ondelete='restrict', index=True, check_company=True)
    allowed_employee_ids = fields.Many2many(related='workcenter_id.employee_ids', readonly=True)
    company_id = fields.Many2one('res.company', related='workorder_id.company_id', store=True, readonly=True, index=True)
    started_at = fields.Datetime(required=True, default=fields.Datetime.now)
    ended_at = fields.Datetime()
    duration_hours = fields.Float(compute='_compute_duration', store=True, digits=(16, 2))
    hourly_cost = fields.Float(compute='_compute_cost', store=True, digits='Product Price')
    cost_amount = fields.Monetary(compute='_compute_cost', store=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    produced_quantity = fields.Float(
        string='Produced Quantity', digits='Product Unit', default=0.0,
        help='Quantity completed by this employee during the session.')
    production_line_id = fields.Many2one(
        'ff.mrp.employee.production.line', string='Production Allocation',
        readonly=True, copy=False, ondelete='set null')
    state = fields.Selection([('running', 'Running'), ('stopped', 'Stopped'), ('cancelled', 'Cancelled')], default='running', required=True, index=True)

    @api.depends('started_at', 'ended_at')
    def _compute_duration(self):
        for session in self:
            stop = session.ended_at or fields.Datetime.now()
            session.duration_hours = max((stop - session.started_at).total_seconds() / 3600.0, 0.0) if session.started_at else 0.0

    @api.depends('employee_id.production_hourly_cost', 'workcenter_id.employee_costs_hour', 'duration_hours')
    def _compute_cost(self):
        for session in self:
            employee_cost = getattr(session.employee_id, 'hourly_cost', 0.0) or session.employee_id.production_hourly_cost
            session.hourly_cost = employee_cost or session.workcenter_id.employee_costs_hour
            session.cost_amount = session.duration_hours * session.hourly_cost

    @api.constrains('workorder_id', 'employee_id', 'started_at', 'ended_at')
    def _check_session(self):
        for session in self:
            if session.workcenter_id.employee_ids and session.employee_id not in session.workcenter_id.employee_ids:
                raise ValidationError(_('Employee %(employee)s is not assigned to work center %(workcenter)s.') % {'employee': session.employee_id.display_name, 'workcenter': session.workcenter_id.display_name})
            if session.ended_at and session.ended_at < session.started_at:
                raise ValidationError(_('Session end cannot be before its start.'))
            if session.state == 'running' and self.search_count([('id', '!=', session.id), ('employee_id', '=', session.employee_id.id), ('state', '=', 'running')]):
                raise ValidationError(_('An employee cannot have two running work-order sessions.'))

    @api.constrains('produced_quantity')
    def _check_produced_quantity(self):
        for session in self:
            if session.produced_quantity < 0:
                raise ValidationError(_('Produced quantity cannot be negative.'))

    def _create_production_allocation(self):
        for session in self.filtered(lambda s: s.produced_quantity > 0 and not s.production_line_id):
            line = self.env['ff.mrp.employee.production.line'].create({
                'production_id': session.production_id.id,
                'workorder_id': session.workorder_id.id,
                'employee_id': session.employee_id.id,
                'production_date': fields.Date.context_today(session),
                'quantity': session.produced_quantity,
            })
            session.production_line_id = line.id

    def action_stop(self):
        running = self.filtered(lambda s: s.state == 'running')
        if running and not self.env.context.get('skip_standard_timer_sync'):
            for session in running:
                user = session.employee_id.user_id
                if user:
                    session.workorder_id.with_user(user).with_context(
                        skip_employee_session_sync=True
                    ).button_pending()
        running.write({'ended_at': fields.Datetime.now(), 'state': 'stopped'})
        running._create_production_allocation()
        return True

    def action_cancel(self):
        running = self.filtered(lambda s: s.state == 'running')
        for session in running:
            user = session.employee_id.user_id
            if user:
                session.workorder_id.with_user(user).with_context(
                    skip_employee_session_sync=True
                ).button_pending()
        self.write({'ended_at': fields.Datetime.now(), 'state': 'cancelled'})
        return True
