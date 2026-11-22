from datetime import date

from psycopg2 import errors
from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase


class TestEmployeeProduction(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.employee = cls.env['hr.employee'].search(
            [('company_id', '=', cls.company.id)], limit=1)
        cls.product = cls.env['product.product'].search(
            [('company_id', 'in', [False, cls.company.id]), ('is_storable', '=', True)], limit=1)
        if not cls.employee or not cls.product:
            raise cls.skipTest('The test database has no employee and storable product fixture.')
        warehouse = cls.env['stock.warehouse'].search(
            [('company_id', '=', cls.company.id)], limit=1)
        if not warehouse:
            warehouse = cls.env['stock.warehouse'].create({
                'name': 'Production Test Warehouse',
                'code': 'FFP',
                'company_id': cls.company.id,
            })
        cls.production = cls.env['mrp.production'].create({
            'product_id': cls.product.id,
            'product_qty': 10,
            'product_uom_id': cls.product.uom_id.id,
            'picking_type_id': warehouse.manu_type_id.id,
            'company_id': cls.company.id,
        })
        cls.workorder = cls.production.workorder_ids[:1]
        if not cls.workorder:
            raise cls.skipTest('The test product has no work order fixture.')
        cls.workorder.workcenter_id.employee_ids = [(4, cls.employee.id)]

    def test_positive_allocation_and_copy_isolated(self):
        line = self.env['ff.mrp.employee.production.line'].create({
            'production_id': self.production.id,
            'workorder_id': self.workorder.id,
            'employee_id': self.employee.id,
            'production_date': date.today(),
            'quantity': 2,
        })
        self.assertEqual(line.product_id, self.production.product_id)
        self.assertEqual(line.company_id, self.company)
        self.assertEqual(self.production.employee_production_qty, 2)
        copied = self.production.copy()
        self.assertFalse(copied.employee_production_line_ids)

    def test_zero_or_negative_allocation_rejected(self):
        with self.assertRaises(errors.CheckViolation):
            self.env['ff.mrp.employee.production.line'].create({
                'production_id': self.production.id,
                'workorder_id': self.workorder.id,
                'employee_id': self.employee.id,
                'quantity': 0,
            })

    def test_report_wizard_filters_to_finalized_complete_orders(self):
        wizard = self.env['ff.mrp.employee.production.report.wizard'].create({
            'employee_ids': [(6, 0, [self.employee.id])],
            'date_from': fields.Date.today(),
            'date_to': fields.Date.today(),
        })
        self.assertFalse(wizard._production_lines())
        self.assertEqual(wizard._selected_employee_ids(), self.employee)

    def test_cancelled_allocation_cannot_be_changed(self):
        line = self.env['ff.mrp.employee.production.line'].create({
            'production_id': self.production.id,
            'workorder_id': self.workorder.id,
            'employee_id': self.employee.id,
            'quantity': 1,
        })
        self.production.action_cancel()
        with self.assertRaises(AccessError):
            line.write({'quantity': 2})

    def test_employee_session_syncs_native_workorder_timer(self):
        if not self.employee.user_id:
            self.skipTest('The employee fixture is not linked to a user.')
        self.workorder.workcenter_id.employee_ids = [(4, self.employee.id)]
        self.workorder.with_user(self.employee.user_id).action_start_employee_session()
        session = self.env['ff.mrp.employee.workorder.session'].search([
            ('workorder_id', '=', self.workorder.id),
            ('employee_id', '=', self.employee.id),
            ('state', '=', 'running'),
        ], order='id desc', limit=1)
        self.assertTrue(session)
        native_timer = self.env['mrp.workcenter.productivity'].search([
            ('workorder_id', '=', self.workorder.id),
            ('user_id', '=', self.employee.user_id.id),
            ('date_end', '=', False),
        ], limit=1)
        self.assertTrue(native_timer)
        session.with_user(self.employee.user_id).action_stop()
        self.assertEqual(session.state, 'stopped')
        self.assertFalse(self.env['mrp.workcenter.productivity'].search([
            ('workorder_id', '=', self.workorder.id),
            ('user_id', '=', self.employee.user_id.id),
            ('date_end', '=', False),
        ], limit=1))

    def test_stopped_session_creates_production_allocation(self):
        if not self.employee.user_id:
            self.skipTest('The employee fixture is not linked to a user.')
        self.workorder.workcenter_id.employee_ids = [(4, self.employee.id)]
        self.workorder.with_user(self.employee.user_id).action_start_employee_session()
        session = self.env['ff.mrp.employee.workorder.session'].search([
            ('workorder_id', '=', self.workorder.id),
            ('employee_id', '=', self.employee.id),
            ('state', '=', 'running'),
        ], order='id desc', limit=1)
        session.produced_quantity = 2
        session.with_user(self.employee.user_id).action_stop()
        self.assertTrue(session.production_line_id)
        self.assertEqual(session.production_line_id.quantity, 2)
        self.assertEqual(session.production_line_id.workorder_id, self.workorder)
