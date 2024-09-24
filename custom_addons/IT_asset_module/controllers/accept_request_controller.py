# -*- coding: utf-8 -*-
from odoo import http
from odoo import SUPERUSER_ID
from odoo.http import request
from odoo import models, fields


class ResellerSignup(http.Controller):
    """Get input from employee and checks if request exists"""

    @http.route('/confirm', auth='public', website=True, method='POST')
    def index(self, **kwargs):
        return http.request.render('IT_asset_module.index')

    @http.route('/asset', auth='public', website=True, csrf=False)
    def check_request(self, **kwargs):
        req_id = kwargs.get('req_id') or ''
        yes_button = kwargs.get('yes') or 'Clicked'
        request_obj = request.env['asset.request'].sudo().search([('name', '=', req_id)])

        if request_obj:
            return http.request.render('IT_asset_module.thanks', {'objs': request_obj})
        else:
            return request.render("IT_asset_module.error")

    @http.route('/received', auth='public', website=True, csrf=False)
    def confirm_asset(self, **kwargs):
        req_id = kwargs.get('req_id') or ''
        request_obj = request.env['asset.request'].sudo().search([('name', '=', req_id)])
        get_asset = request.env['account.asset.asset'].sudo().search([('asset_number', '=', request_obj.asset_id.asset_number)])
        if get_asset.do_manage is True:
            get_asset.managed_by = request_obj.employee.id
        else:
            get_asset.assigned_to = request_obj.employee.id
        get_asset.location = request_obj.employee.stock_location.id
        # get_asset.date_received = fields.Date.context_today(self)
        get_asset.asset_status = "allocated"

        xyz = request.env['asset.movement.history'].sudo().create({
            'name': request_obj.asset_id.id,
            'location_from': request_obj.asset_id.initial_location.id,
            'location_to': request_obj.employee.stock_location.id,
            'asset_status': request_obj.asset_id.asset_status
        })

        request_obj.state = 'received'
        return request.render('IT_asset_module.received', {'objs': request_obj})
