from datetime import date

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class FfMrpEmployeeProductionReportWizard(models.TransientModel):
    _name = 'ff.mrp.employee.production.report.wizard'
    _description = 'Employee Production Statement Wizard'

    employee_id = fields.Many2one(
        'hr.employee', string='Employee', readonly=True)
    employee_ids = fields.Many2many(
        'hr.employee', string='Employees')
    date_from = fields.Date(string='Date From', required=True)
    date_to = fields.Date(string='Date To', required=True)
    print_datetime = fields.Datetime(
        string='Print Date', default=fields.Datetime.now, readonly=True)
    show_order_details = fields.Boolean(
        string='Show Manufacturing Order Details', default=True)

    @api.model
    def default_get(self, field_list):
        values = super().default_get(field_list)
        today = fields.Date.context_today(self)
        values.setdefault('date_from', today.replace(day=1))
        values.setdefault('date_to', today)
        employee_ids = self.env.context.get('default_employee_ids')
        if employee_ids and not values.get('employee_ids'):
            values['employee_ids'] = employee_ids
        active_ids = self.env.context.get('active_ids')
        if active_ids and not values.get('employee_ids'):
            values['employee_ids'] = [(6, 0, active_ids)]
        if values.get('employee_id') and not values.get('employee_ids'):
            values['employee_ids'] = [(6, 0, [values['employee_id']])]
        return values

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for wizard in self:
            if wizard.date_from and wizard.date_to and wizard.date_from > wizard.date_to:
                raise ValidationError(_('Date From cannot be later than Date To.'))

    def _selected_employee_ids(self):
        self.ensure_one()
        employees = self.employee_ids
        if self.employee_id:
            employees |= self.employee_id
        return employees

    def _production_lines(self):
        self.ensure_one()
        domain = [
            ('report_eligible', '=', True),
            ('approval_state', '=', 'approved'),
            ('production_date', '>=', self.date_from),
            ('production_date', '<=', self.date_to),
        ]
        employees = self._selected_employee_ids()
        if employees:
            domain.append(('employee_id', 'in', employees.ids))
        return self.env['ff.mrp.employee.production.line'].search(
            domain, order='employee_id, production_date, production_id')

    def get_report_sections(self):
        self.ensure_one()
        lines = self._production_lines()
        sections = []
        for employee in self._selected_employee_ids().sorted(key=lambda item: item.name or ''):
            employee_lines = lines.filtered(lambda line: line.employee_id == employee)
            summary = {}
            for line in employee_lines:
                key = (line.product_id.id, line.product_uom_id.id)
                bucket = summary.setdefault(key, {
                    'product': line.product_id.display_name,
                    'uom': line.product_uom_id.display_name,
                    'quantity': 0.0,
                })
                bucket['quantity'] += line.quantity
            sections.append({
                'employee': employee,
                'lines': employee_lines,
                'summary': list(summary.values()),
                'order_count': len(employee_lines.mapped('production_id')),
            })
        return sections

    def action_view_records(self):
        self.ensure_one()
        employees = self._selected_employee_ids()
        domain = [
            ('report_eligible', '=', True),
            ('approval_state', '=', 'approved'),
            ('production_date', '>=', self.date_from),
            ('production_date', '<=', self.date_to),
        ]
        if employees:
            domain.append(('employee_id', 'in', employees.ids))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Employee Production'),
            'res_model': 'ff.mrp.employee.production.line',
            'view_mode': 'list,pivot,graph,form',
            'domain': domain,
            'target': 'current',
        }

    def action_print(self):
        self.ensure_one()
        if not self._selected_employee_ids():
            raise ValidationError(_('Select at least one employee.'))
        return self.env.ref(
            'ff_mrp_employee_productivity.action_report_employee_production_statement'
        ).report_action(self)
