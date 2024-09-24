# -*- coding: utf-8 -*-
from odoo import http

# class BbisReports(http.Controller):
#     @http.route('/bbis_reports/bbis_reports/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/bbis_reports/bbis_reports/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('bbis_reports.listing', {
#             'root': '/bbis_reports/bbis_reports',
#             'objects': http.request.env['bbis_reports.bbis_reports'].search([]),
#         })

#     @http.route('/bbis_reports/bbis_reports/objects/<model("bbis_reports.bbis_reports"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('bbis_reports.object', {
#             'object': obj
#         })