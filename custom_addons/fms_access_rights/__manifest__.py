# -*- coding: utf-8 -*-
##############################################################################
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    GENERAL PUBLIC LICENSE (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'GFMS Access Rights',
    'summary': """GFMS Access Rights""",
    'version': '16.0',
    'description': """GFMS Access Rights""",
    'category': 'Access Rights',
    'depends': ['base','fms_hrms', 'website_support',],
    'data': [
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': False,

}
# 'IT_asset_module'
# access_asset_reordering,access_asset_reordering,IT_asset_module.model_asset_reordering,base.group_user,1,1,1,1
# access_asset_movement_history,access_asset_movement_history,IT_asset_module.model_asset_movement_history,base.group_user,1,1,1,1