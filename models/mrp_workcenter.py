from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'

    employee_costs_hour = fields.Float(string='Employee Cost per Hour', help='Estimated hourly cost per employee used for manufacturing cost calculations.', default=0.0, digits='Product Price')

    employee_ids = fields.Many2many(
        'hr.employee',
        'ff_mrp_workcenter_employee_rel',
        'workcenter_id', 'employee_id',
        string='Employees',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        check_company=True,
        help='Employees allowed to record production on this work center.')

    @api.constrains('employee_ids', 'company_id')
    def _check_employee_companies(self):
        for workcenter in self:
            if not workcenter.company_id:
                continue
            invalid = workcenter.employee_ids.filtered(
                lambda employee: employee.company_id and employee.company_id != workcenter.company_id
            )
            if invalid:
                raise ValidationError(_(
                    'Employees from another company cannot be assigned to work center %(workcenter)s: %(employees)s.'
                ) % {
                    'workcenter': workcenter.display_name,
                    'employees': ', '.join(invalid.mapped('display_name')),
                })
