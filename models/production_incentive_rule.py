from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class FfMrpProductionIncentiveRule(models.Model):
    _name = 'ff.mrp.production.incentive.rule'
    _description = 'Production Incentive Rule'
    _order = 'sequence, name'
    _check_company_auto = True

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    employee_ids = fields.Many2many('hr.employee', string='Employees')
    workcenter_ids = fields.Many2many('mrp.workcenter', string='Work Centers')
    product_ids = fields.Many2many('product.product', string='Products')
    input_type_id = fields.Many2one('hr.payslip.input.type', required=True, string='Payroll Input Type')
    calculation_mode = fields.Selection([
        ('per_unit', 'Amount per approved unit'),
        ('target_variance', 'Amount per unit above/below target'),
    ], default='per_unit', required=True)
    target_quantity = fields.Float(string='Monthly Target Quantity')
    rate_per_unit = fields.Float(string='Amount per Unit', required=True, digits='Product Price')
    max_amount = fields.Float(string='Maximum Adjustment', help='Optional absolute cap. Leave zero for no cap.', digits='Product Price')
    note = fields.Text()

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
