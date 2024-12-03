from odoo import api, models, fields


class CustomPOSConfig(models.Model):
    _inherit = 'pos.config'
    _sql_constraints = [
        ('unique_name', 'unique(name)', 'The name of the POS must be unique!'),
    ]
    registrierkasse_aes_key = fields.Char(string='Umsatzzähler AES', required=True, translate=True)
    revenue_counter = fields.Float(string='Total', digits=0, required=True, default=0)

    def copy(self, default=None):
        # Ensure the `default` dictionary is initialized
        default = dict(default or {})

        # Customize the behavior: e.g., clear the name field
        default['name'] = "Copy of POS"

        # Reset specific fields, like the session or amounts, if needed
        default.update({
            'registrierkasse_aes_key': None,
            'revenue_counter': 0.0,
        })

        # Call the parent method to handle the standard copy behavior
        return super(CustomPOSConfig, self).copy(default)
