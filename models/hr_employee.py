from odoo import api, fields, models, _
from odoo.exceptions import AccessError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    production_hourly_cost = fields.Float(
        string='Production Hourly Cost', digits='Product Price', default=0.0,
        help='Actual hourly labor cost used for employee production costing.')

    employee_production_count = fields.Integer(
        string='Production Entries', compute='_compute_employee_production_count')

    def _check_production_access(self):
        if not (
            self.env.user.has_group('mrp.group_mrp_user')
            or self.env.user.has_group('hr.group_hr_user')
        ):
            raise AccessError(_('You are not allowed to view employee production records.'))

    def _compute_employee_production_count(self):
        line_model = self.env['ff.mrp.employee.production.line']
        for employee in self:
            employee.employee_production_count = line_model.search_count([
                ('employee_id', '=', employee.id),
                ('company_id', 'in', self.env.companies.ids),
            ])

    def action_open_employee_production(self):
        self._check_production_access()
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Employee Production'),
            'res_model': 'ff.mrp.employee.production.line',
            'view_mode': 'list,pivot,graph,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {
                'default_employee_id': self.id,
                'search_default_employee_id': self.id,
            },
        }

    def action_print_employee_production_statement(self):
        self._check_production_access()
        employee_ids = self.ids
        return {
            'type': 'ir.actions.act_window',
            'name': _('Print Employee Production Statements'),
            'res_model': 'ff.mrp.employee.production.report.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_employee_id': self.id if len(self) == 1 else False,
                'default_employee_ids': [(6, 0, employee_ids)],
            },
        }
