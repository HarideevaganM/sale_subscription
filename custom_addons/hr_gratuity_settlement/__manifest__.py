# -*- coding: utf-8 -*-
###################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2017-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Ajmal JK(<https://www.cybrosys.com>)
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
    'name': 'Open HRMS Gratuity Settlement',
    'summary': """Employee Gratuity Settlement During Resignation """,
    'depends': ['base', 'hr_resignation','mail','hr_payroll', 'hr_work_from_home'],
    'data': ['views/employee_gratuity_view.xml',
             'views/gratuity_sequence.xml',
             'views/other_settlements.xml',
             'security/ir.model.access.csv'],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': False,
}
