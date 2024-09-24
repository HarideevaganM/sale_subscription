# -*- coding: utf-8 -*-
###################################################################################
#    A part of OpenHRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2018-TODAY Cybrosys Technologies (<https://www.cybrosys.com>).
#    Author: Ijaz Ahammed (<https://www.cybrosys.com>)
#
#    This program is free software: you can modify
#    it under the terms of the GNU Affero General Public License (AGPL) as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
###################################################################################
{
    'name': 'HR Overtime',
    'summary': 'Manage Employee Overtime',
    'description': """Helps you to manage Employee Overtime""",
    'depends': ['base', 'hr', 'hr_contract','hr_attendance', 'hr_payroll_community', 'hr_holidays', 'project', 'resource'],
    'data': [
        'data/data.xml',
        'views/mail_template.xml',
        'views/overtime_request_view.xml',
        'views/overtime_type.xml',
        'views/hr_contract.xml',
        'views/hr_payslip.xml',
        'security/ir.model.access.csv',
    ],
    'demo': ['data/hr_overtime_demo.xml'],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
}
