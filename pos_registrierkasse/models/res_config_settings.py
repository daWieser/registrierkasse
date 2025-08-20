from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    fon_active = fields.Boolean(config_parameter='pos_registrierkasse.fon_active')
    fon_tid = fields.Char(config_parameter='pos_registrierkasse.fon_tid')
    fon_benid = fields.Char(config_parameter='pos_registrierkasse.fon_benid')
    fon_pin = fields.Char(config_parameter='pos_registrierkasse.fon_pin')
    fon_herstellerid = fields.Char(config_parameter='pos_registrierkasse.fon_herstellerid')
    fon_environment = fields.Selection(
        [('test', 'Test Environment'), ('production', 'Production Environment')],
        config_parameter='pos_registrierkasse.fon_environment',
        default='production'
    )
