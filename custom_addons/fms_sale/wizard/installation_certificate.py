from odoo import api, fields, models, _


class InstallationCertificate(models.Model):
    _name = "installation.certificate"
    
    name = fields.Char("Reference Number")
    company_id = fields.Many2one("res.company", "Company Name")
    partner_id = fields.Many2one("res.partner", "Customer Name")
    validity = fields.Integer("Validity")
    serial_no = fields.Char("Device Serial Number")
    vehicle_number = fields.Char("Vehicle Number")
    fleet_description = fields.Char("Fleet Description")
    job_card_id = fields.Many2one("job.card", "Job Card Reference")


class CertificateDetails(models.Model):
    _name = "certificate.details"
    
    name = fields.Char("Reference Number")
    company_id = fields.Many2one("res.company", "Company Name")
    partner_id = fields.Many2one("res.partner", "Customer Name")
    validity = fields.Integer("Validity")
    serial_no = fields.Char("Device Serial Number")
    vehicle_number = fields.Char("Vehicle Number")
    fleet_description = fields.Char("Fleet Description")
        
        
        
        
