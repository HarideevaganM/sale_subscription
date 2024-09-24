# -*- coding: utf-8 -*-
from openerp import http

# class EndServicesBenfits(http.Controller):
#     @http.route('/end_services_benfits/end_services_benfits/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/end_services_benfits/end_services_benfits/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('end_services_benfits.listing', {
#             'root': '/end_services_benfits/end_services_benfits',
#             'objects': http.request.env['end_services_benfits.end_services_benfits'].search([]),
#         })

#     @http.route('/end_services_benfits/end_services_benfits/objects/<model("end_services_benfits.end_services_benfits"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('end_services_benfits.object', {
#             'object': obj
#         })