{
    'name': 'Flous Flow Employee Production Tracking',
    'version': '19.0.2.0.18',
    'category': 'Manufacturing/Reporting',
    'summary': 'Track manufactured quantities by employee on manufacturing orders.',
    'description': """
Record employee production allocations directly on manufacturing orders and
report approved completed production by employee, product and date.
""",
    'author': 'Flous Flow',
    'website': 'https://flousflow.com',
    'license': 'LGPL-3',
    'images': [
        'static/description/images/employee_production_screenshot.png',
    ],
    # Payroll integration uses the Flous Flow payslip/input models.
    'depends': ['mrp', 'hr', 'ff_hr_payroll'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/mrp_production_views.xml',
        'views/mrp_workcenter_views.xml',
        'views/employee_workorder_session_views.xml',
        'views/mrp_workorder_employee_views.xml',
        'views/production_payroll_wizard_views.xml',
        'views/production_incentive_rule_views.xml',
        'views/hr_employee_views.xml',
        'views/employee_production_line_views.xml',
        'views/employee_production_report_wizard_views.xml',
        'reports/employee_production_report.xml',
        'reports/employee_production_templates.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
