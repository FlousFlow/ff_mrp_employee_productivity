from odoo import api, fields, models, _
from odoo.exceptions import AccessError, ValidationError
from odoo.tools.float_utils import float_compare


class FfMrpEmployeeProductionLine(models.Model):
    _name = 'ff.mrp.employee.production.line'
    _description = 'Employee Production Allocation'
    _order = 'production_date, id'
    _check_company_auto = True

    production_id = fields.Many2one(
        'mrp.production', string='Manufacturing Order', required=True,
        ondelete='cascade', index=True, copy=False, check_company=True)
    workorder_id = fields.Many2one(
        'mrp.workorder', string='Work Order', required=True, ondelete='restrict',
        index=True, check_company=True,
        domain="[('production_id', '=', production_id)]")
    workcenter_id = fields.Many2one(
        'mrp.workcenter', string='Work Center', related='workorder_id.workcenter_id',
        store=True, readonly=True, index=True, check_company=True)
    allowed_employee_ids = fields.Many2many(
        related='workcenter_id.employee_ids', readonly=True)
    employee_id = fields.Many2one(
        'hr.employee', string='Employee', required=True, ondelete='restrict',
        index=True, check_company=True)
    production_date = fields.Date(
        string='Production Date', required=True,
        default=fields.Date.context_today, index=True)
    quantity = fields.Float(
        string='Produced Quantity', required=True, digits='Product Unit')
    approval_state = fields.Selection([
        ('draft', 'Draft'), ('submitted', 'Submitted'), ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Approval', default='draft', required=True, index=True, copy=False)
    approved_by = fields.Many2one('res.users', string='Approved By', readonly=True, copy=False)
    approved_at = fields.Datetime(string='Approved At', readonly=True, copy=False)
    payroll_state = fields.Selection([
        ('pending', 'Pending Payroll'), ('sent', 'Sent to Payroll'),
    ], string='Payroll', default='pending', required=True, index=True, copy=False)
    payroll_input_id = fields.Many2one('hr.payslip.input', string='Payroll Input', readonly=True, copy=False)
    product_id = fields.Many2one(
        'product.product', string='Product', related='production_id.product_id',
        store=True, readonly=True, index=True)
    product_uom_id = fields.Many2one(
        'uom.uom', string='Unit of Measure', related='production_id.product_uom_id',
        store=True, readonly=True)
    company_id = fields.Many2one(
        'res.company', string='Company', related='production_id.company_id',
        store=True, readonly=True, index=True)
    production_state = fields.Selection(
        related='production_id.state', string='Manufacturing Status',
        store=True, readonly=True)
    production_status = fields.Selection(
        related='production_id.employee_production_status',
        string='Distribution Status', store=True, readonly=True)
    report_eligible = fields.Boolean(
        related='production_id.employee_production_reportable',
        string='Eligible for Report', store=True, readonly=True, index=True)

    _quantity_positive = models.Constraint(
        'check (quantity > 0)',
        'Produced quantity must be greater than zero.',
    )

    @api.constrains('production_id', 'workorder_id', 'employee_id', 'quantity', 'production_date')
    def _check_employee_production_line(self):
        for line in self:
            if line.workorder_id and line.workorder_id.production_id != line.production_id:
                raise ValidationError(_('The work order must belong to the selected manufacturing order.'))
            if line.workorder_id and line.workcenter_id.employee_ids and line.employee_id not in line.workcenter_id.employee_ids:
                raise ValidationError(_(
                    'Employee %(employee)s is not assigned to work center %(workcenter)s.'
                ) % {
                    'employee': line.employee_id.display_name,
                    'workcenter': line.workcenter_id.display_name,
                })
            if line.employee_id.company_id and line.employee_id.company_id != line.company_id:
                raise ValidationError(_(
                    'Employee %(employee)s belongs to %(employee_company)s and cannot '
                    'be assigned to a manufacturing order in %(production_company)s.'
                ) % {
                    'employee': line.employee_id.display_name,
                    'employee_company': line.employee_id.company_id.display_name,
                    'production_company': line.company_id.display_name,
                })
            if line.production_id and line.product_uom_id:
                if float_compare(
                        line.quantity, 0.0, precision_rounding=line.product_uom_id.rounding) <= 0:
                    raise ValidationError(_('Produced quantity must be greater than zero.'))

    def _check_finalized_edit(self):
        cancelled = self.filtered(lambda line: line.production_state == 'cancel')
        if cancelled:
            raise AccessError(_('Cancelled employee production allocations cannot be changed.'))
        if not self.env.user.has_group('mrp.group_mrp_manager'):
            finalized = self.filtered(lambda line: line.production_state == 'done')
            if finalized:
                raise AccessError(_(
                    'Finalized employee production allocations can only be corrected by a '
                    'Manufacturing Manager.'))
        approved = self.filtered(lambda line: line.approval_state == 'approved')
        if approved and not self.env.user.has_group('mrp.group_mrp_manager'):
            raise AccessError(_('Approved production entries can only be corrected by a Manufacturing Manager.'))

    def action_submit(self):
        self.filtered(lambda line: line.approval_state in ('draft', 'rejected')).write({'approval_state': 'submitted'})
        return True

    def action_approve(self):
        if not self.env.user.has_group('mrp.group_mrp_manager'):
            raise AccessError(_('Only a Manufacturing Manager can approve production.'))
        incomplete = self.filtered(lambda line: not line.report_eligible)
        if incomplete:
            raise ValidationError(_(
                'Only completed manufacturing orders with a fully assigned employee '
                'distribution can be approved.'))
        self.write({'approval_state': 'approved', 'approved_by': self.env.user.id, 'approved_at': fields.Datetime.now()})
        return True

    def action_reject(self):
        if not self.env.user.has_group('mrp.group_mrp_manager'):
            raise AccessError(_('Only a Manufacturing Manager can reject production.'))
        self.write({'approval_state': 'rejected', 'approved_by': False, 'approved_at': False})
        return True

    def write(self, vals):
        self._check_finalized_edit()
        finalized = self.filtered(lambda line: line.production_state == 'done')
        result = super().write(vals)
        if finalized and self.env.user.has_group('mrp.group_mrp_manager'):
            for line in finalized:
                line.production_id.message_post(body=_(
                    'Employee production allocation corrected by %(user)s for %(employee)s.'
                ) % {
                    'user': self.env.user.display_name,
                    'employee': line.employee_id.display_name,
                })
        return result

    def unlink(self):
        self._check_finalized_edit()
        return super().unlink()
