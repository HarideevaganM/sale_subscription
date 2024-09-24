# -*- coding: utf-8 -*-
import logging
from odoo import http
from odoo.http import request
_logger = logging.getLogger("Job")
import requests
import odoo.tools as tools

class FmsIntregration(http.Controller):
	@http.route(['/receive_job_data'], type='json', auth="public", csrf=False)
	def receive_job_data(self, **post):
		db, login, password = '', '', ''
		if post.get('login'):
			login = post.get('login')
		if post.get('password'):
			password = post.get('password')

		db = tools.config['db_name']

		log_details = {"jsonrpc": "2.0", "params": {"db": db, "login": login, "password": password}}

		response = requests.post('http://localhost:8090/web/session/authenticate/', json=log_details)
		response = response.json()
		result = {}
		if response.get('result'):
			result = response.get('result')

		job_data = []
		limit = []
		domain = []
		if post.get('limit'):
			limit = post.get('limit')
		# company_id = request.env.user and request.env.user.company_id
		# token = company_id.token if company_id else False
		# _logger.info('============= User Found ================ : %s', result.get('name'))
		if result.get('uid'):
			fms_filter = post.get('domain')
			if fms_filter:
				if fms_filter.get('date') and not fms_filter.get('operator', False):
					job_data.append({'DateError': "Date must be send with extra parameter, i.e operator : '>=' "})
					return job_data
				if fms_filter.get('date') and fms_filter.get('operator'):
					domain.append(('create_date', fms_filter.get('operator'), fms_filter.get('date')))
				if fms_filter.get('device_name'):
					domain.append(('device_id.name', '=', fms_filter.get('device_name')))
				if fms_filter.get('customer_name'):
					domain.append(('company_id.name', '=', fms_filter.get('customer_name')))
				if fms_filter.get('sale_name'):
					domain.append(('sale_order_id.name', '=', fms_filter.get('sale_name')))
				if fms_filter.get('device_code'):
					domain.append(('device_code', '=', fms_filter.get('device_code')))
				if fms_filter.get('job_id') and fms_filter.get('operator'):
					domain.append(('id', fms_filter.get('operator'), fms_filter.get('job_id')))
				if fms_filter.get('state'):
					domain.append(('state', '=', fms_filter.get('state')))

			# Add filter to not include job card from cancelled sale order
			domain.append(('sale_order_id.state', '!=', 'cancel'))

			filter_jobs = request.env['job.card'].sudo().search(domain, limit=limit)
			for fil in filter_jobs:
				job_data.append({
						'job_id': fil.id,
						'job_name': fil.name,
						'job_date': fil.create_date, 
						"sale_order": fil.sale_order_id.name if fil.sale_order_id else False,
						"customer_name": fil.company_id.name if fil.company_id else False,
						"device_name": fil.device_id.name if fil.device_id else False,
						"device_code": fil.device_code,
						"customer_bbis_code": fil.company_id.bbis_code if fil.company_id else False,
						"customer_normal_code": fil.company_id.customer_id if fil.company_id else False,
						'state': fil.state,
					})
		else:
			job_data.append({'Error': 'Unable to process request.'})
			_logger.info('============= User Not Found ======================')
		_logger.info('============= Sending Job Card Data On FMS Request ======================')
		return job_data
