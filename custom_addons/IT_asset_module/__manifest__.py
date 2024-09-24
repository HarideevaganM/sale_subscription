# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'IT Asset Management',
    'author': 'Herlabytes',
    'category': 'Asset',
    'sequence': 6,
    'summary': 'Manages the IT Assets Owned by any Company and this done with ease',
    'depends': ['base', 'account_asset', 'hr', 'stock', 'mail', 'website'],
    'images': ['images/main.png', 'images/main_screenshot.png'],

    'website': 'https://herlabytes.com',
    'description': """
            IT Assets management
            =================
            Manages IT assets owned by a company or a person.
            Keeps track of depreciation, and creates corresponding journal entries.
            """,
    'data': [
        'security/asset_request_security.xml',
        'views/asset_menus.xml',
        'views/asset_return_view.xml',
        'views/asset_request_view.xml',
        'views/main_asset_view.xml',
        'views/asset_branch_view.xml',
        'views/asset_model_view.xml',
        'views/hr_view.xml',
        'views/asset_category_view.xml',
        'views/asset_repair_view.xml',
        'views/asset_disposal_view.xml',
        'views/internal_transfer_request_view.xml',
        'views/lost_stolen_asset_view.xml',
        'views/batch_asset_disposal_view.xml',

        # 'views/asset_history_view.xml',
        'report/asset_number_label.xml',
        'report/asset_report_wizard.xml',
        'report/all_asset_report_view.xml',

        'scheduler/asset_request_scheduler_view.xml',

        'templates/accept_request_controller_view.xml',


        'security/ir.model.access.csv',
    ],
    'installable': True,
    'license': 'OPL-1',
}
