from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class FfMrpProductionPayrollWizard(models.TransientModel):
    _name = 'ff.mrp.production.payroll.wizard'
    _description = 'Send Approved Production to Payroll'

    employee_ids = fields.Many2many('hr.employee', string='Employees')
    date_from = fields.Date(required=True, default=lambda self: fields.Date.today().replace(day=1))
    date_to = fields.Date(required=True, default=fields.Date.today)
    rule_id = fields.Many2one('ff.mrp.production.incentive.rule', string='Incentive Rule', required=True, domain="[('active', '=', True)]")

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for wizard in self:
            if wizard.date_from > wizard.date_to:
                raise ValidationError(_('Date From cannot be later than Date To.'))

    def action_send_to_payroll(self):
        self.ensure_one()
        domain = [
            ('approval_state', '=', 'approved'), ('payroll_state', '=', 'pending'),
            ('report_eligible', '=', True),
            ('production_date', '>=', self.date_from), ('production_date', '<=', self.date_to),
        ]
        if self.employee_ids:
            domain.append(('employee_id', 'in', self.employee_ids.ids))
        lines = self.env['ff.mrp.employee.production.line'].search(domain)
        if not lines:
            raise ValidationError(_('No approved production entries are pending for this period.'))
        payslips = self.env['hr.payslip'].search([
            ('employee_id', 'in', lines.mapped('employee_id').ids),
            ('date_from', '<=', self.date_to), ('date_to', '>=', self.date_from),
            ('state', '=', 'draft'),
        ])
        created = self.env['hr.payslip.input']
        for employee in lines.mapped('employee_id'):
            employee_lines = lines.filtered(lambda line: line.employee_id == employee)
            payslip = payslips.filtered(lambda slip: slip.employee_id == employee)[:1]
            if not payslip:
                raise ValidationError(_('No draft payslip found for %s in the selected period.') % employee.display_name)
            if not self.rule_id.matches(employee, employee_lines):
                raise ValidationError(_('The incentive rule does not match %s.') % employee.display_name)
            amount = self.rule_id.compute_amount(sum(employee_lines.mapped('quantity')))
            payroll_input = self.env['hr.payslip.input'].create({
                'payslip_id': payslip.id,
                'input_type_id': self.rule_id.input_type_id.id,
                'name': _('Production adjustment (%s units)') % sum(employee_lines.mapped('quantity')),
                'amount': amount,
            })
            created |= payroll_input
            employee_lines.write({'payroll_state': 'sent', 'payroll_input_id': payroll_input.id})
        return {'type': 'ir.actions.act_window_close'}
