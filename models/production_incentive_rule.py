from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class FfMrpProductionIncentiveRule(models.Model):
    _name = 'ff.mrp.production.incentive.rule'
    _description = 'Production Incentive Rule'
    _order = 'sequence, name'
    _check_company_auto = True

    name = fields.Char(required=True, string='Rule Name')
    active = fields.Boolean(default=True, string='Active')
    sequence = fields.Integer(default=10, string='Sequence')
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, string='Company')
    employee_ids = fields.Many2many(
        'hr.employee', string='Employees',
        help='Leave empty to apply to every employee in the selected company.',
    )
    workcenter_ids = fields.Many2many(
        'mrp.workcenter', string='Work Centers',
        help='Leave empty to apply to production from every work center.',
    )
    product_ids = fields.Many2many(
        'product.product', string='Products',
        help='Leave empty to apply to every product.',
    )
    input_type_id = fields.Many2one(
        'hr.payslip.input.type', required=True, string='Payroll Input Type',
        help='The payslip input type that receives this rule amount.',
    )
    calculation_mode = fields.Selection([
        ('per_unit', 'Amount per approved unit'),
        ('target_variance', 'Amount per unit above/below target'),
    ], default='per_unit', required=True, help=(
        'Amount per approved unit pays the rate for every approved unit. '
        'Amount per unit above/below target applies the rate to the difference '
        'between approved quantity and the monthly target.'
    ))
    target_quantity = fields.Float(
        string='Monthly Target Quantity',
        help='Monthly target used only with the above/below target calculation mode.',
    )
    rate_per_unit = fields.Float(
        string='Amount per Unit', required=True, digits='Product Price',
        help='Adjustment amount for each approved unit. A negative value reduces the payslip amount.',
    )
    max_amount = fields.Float(
        string='Maximum Adjustment',
        help='Optional absolute cap for the adjustment. Leave zero for no cap.',
        digits='Product Price',
    )
    note = fields.Text(string='Notes')

    @api.constrains('target_quantity', 'max_amount')
    def _check_non_negative(self):
        for rule in self:
            if rule.target_quantity < 0 or rule.max_amount < 0:
                raise ValidationError(_('Target and maximum adjustment cannot be negative.'))

    def matches(self, employee, lines):
        self.ensure_one()
        if self.employee_ids and employee not in self.employee_ids:
            return False
        if self.workcenter_ids and not (lines.mapped('workcenter_id') & self.workcenter_ids):
            return False
        if self.product_ids and not (lines.mapped('product_id') & self.product_ids):
            return False
        return True

    def compute_amount(self, quantity):
        self.ensure_one()
        base = quantity if self.calculation_mode == 'per_unit' else quantity - self.target_quantity
        amount = base * self.rate_per_unit
        if self.max_amount:
            amount = max(min(amount, self.max_amount), -self.max_amount)
        return amount
