
{
    'name': 'Repair Internal Picking',
    'version': '1.0',
    'category': 'Repair',
    'summary': 'Move device internal location to repair or replace',
    'depends': ['fms_repair', 'stock'],
    'data': [
    	'wizard/make_internal_wizard.xml',
        # 'views/repair_views.xml'
        ],
    'installable': True,
}
