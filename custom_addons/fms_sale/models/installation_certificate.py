from odoo import api, fields, models, _
from datetime import datetime,date,timedelta,time
from dateutil.relativedelta import relativedelta


class InstallationCertificate(models.Model):
    _name = "installation.certificate"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char("Reference Number")
    company_id = fields.Many2one("res.company","Company Name")
    partner_id = fields.Many2one("res.partner","Customer Name")
    validity = fields.Integer("Validity", default=1)
    serial_no = fields.Many2one("stock.lot","Device Serial Number")
    vehicle_number = fields.Many2one("vehicle.master","Vehicle Number")
    fleet_description = fields.Char("Fleet Description")
    job_card_id = fields.Many2one("job.card","Job Card Reference")
    certificate_subject = fields.Char("Certificate Subject")
    certificate_content = fields.Text("Certificate Content")
    vin_no = fields.Char("VIN No.")
    certificate_validity = fields.Char(compute='get_certificate_end_date',string='Certificates')
    is_certificate_expired = fields.Boolean(string='Certificates') 
    installation_date = fields.Date('Installation Date')      
    device_id = fields.Many2one("product.product","Device Type",store=True)
    from_date = fields.Date('From Date')
    to_date = fields.Date('To Date', compute='get_to_date', store=True)
    issue_date = fields.Date('Issue Date', default=fields.datetime.now())

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('installation.certificate')
        return super(InstallationCertificate,self).create(vals)

    # @api.one
    @api.depends('from_date')
    def _get_to_date(self):
        for rec in self:
            if rec.from_date:
                from_date = datetime.strptime(str(rec.from_date), "%Y-%m-%d")
                to_date = from_date + relativedelta(years=1)
                todate = to_date - relativedelta(days=1)
                rec.to_date = fields.Date.to_string(todate)

    # @api.multi
    # @api.depends('')
    def _get_certificate_end_date(self):
        for rec in self:
            today_date = datetime.now()
            res = today_date + relativedelta(years=1)
            result = res - relativedelta(days=1)
            end_date = result.strftime('%Y-%m-%d')
            rec.certificate_validity = end_date
            date_create = fields.Datetime.from_string(rec.create_date)
            certificate_create_date = date_create.strftime('%Y-%m-%d')
            if certificate_create_date >= end_date:
                self.env.cr.execute("""update installation_certificate set is_certificate_expired=true where id = %s""" % certificate_id.id)
