from odoo import api, models, fields

from .utils.a_trust_library import OrderData, create_signature, login, LoginData
from .utils.order_utils import hash_signature
from .utils.revenue_counter import encrypt_revenue_counter, generate_aes_key, generate_aes_checksum


class CustomPOSConfig(models.Model):
    _inherit = 'pos.config'
    _sql_constraints = [
        ('unique_name', 'unique(name)', 'The name of the POS must be unique!'),
    ]
    receipt_sequence_id = fields.Many2one('ir.sequence', string='Receipt IDs Sequence', readonly=True,
                                          help="This sequence is automatically created by Odoo but you can change it "
                                               "to customize the reference numbers of your orders.", copy=False,
                                          ondelete='restrict')

    registrierkasse_aes_key = fields.Char(string='Umsatzzähler AES', translate=True)
    registrierkasse_aes_key_checksum = fields.Char(string='Umsatzzähler AES Prüfsumme', translate=True)
    revenue_counter = fields.Float(string='Total', digits=0, default=0)

    a_trust_user_name = fields.Char(string='A-Trust User Name')
    a_trust_password = fields.Char(string='A-Trust Password')
    certificate_serial_number = fields.Char(string='A-Trust Certificate Serial Number')

    a_trust_session_key = fields.Char(string='A-Trust Session Key')
    a_trust_session_id = fields.Char(string='A-Trust Session Id')
    pos_use_registrierkasse = fields.Boolean(string='Does this POS use the RKSV module')
    pos_rksv_lock = fields.Boolean(string='If this lock is set, RKSV settings can not be changed')

    def copy(self, default=None):
        raise NotImplemented("Copying POS is not allowed when using the Austrian Registrierkasse module")

    @api.model
    def create(self, vals):
        pos_config = super(CustomPOSConfig, self).create(vals)
        if not pos_config.receipt_sequence_id:
            pos_config.receipt_sequence_id = self._create_sequence(pos_config)

        if pos_config.pos_use_registrierkasse:
            self._create_starting_receipt(pos_config)
        return pos_config

    def _create_sequence(self, pos_config):
        sequence = self.env['ir.sequence'].create({
            'name': f"POS Order Sequence for {pos_config.id}",
            'code': f'pos.order.{pos_config.id}',
            'padding': 5,
            'use_date_range': False,
        })
        return sequence

    def _create_starting_receipt(self, pos_config):
        pos_session = self.env['pos.session'].create({
            'name': 'Starting recipt session',  # Name of the session
            'config_id': pos_config.id,
            'user_id': self.env.user.id,  # User creating the session
            'start_at': fields.Datetime.now(),  # Session start time
        })

        order = self.env['pos.order'].create({
            'date_order': fields.Datetime.now(),  # Order timestamp
            'amount_total': 0,
            'amount_tax': 0,
            'amount_paid': 0,
            'amount_return': 0,
            'lines': [(0, 0, {
                'product_id': self._get_null_product().id,
                'price_unit': 0,
                'price_subtotal': 0,
                'price_subtotal_incl': 0,
                'qty': 1,
            }), ],
            'session_id': pos_session.id,
            'registrierkasse_receipt_number': pos_config.receipt_sequence_id.next_by_id(),
            'certificate_serial_number': pos_config.certificate_serial_number
        })
        order.pos_reference = str(pos_session.id).zfill(5) + "-" + '0'.zfill(3) + "-" + '1'.zfill(4)

        order.action_pos_order_paid()
        order.write({'state': 'done'})

        order.encrypted_revenue = encrypt_revenue_counter(0, pos_config.registrierkasse_aes_key, pos_config.name,
                                                          order.registrierkasse_receipt_number)

        a_trust_session = login(LoginData(pos_config.a_trust_user_name, pos_config.a_trust_password))

        pos_config.a_trust_session_id = a_trust_session.sessionId
        pos_config.a_trust_session_key = a_trust_session.sessionKey
        pos_config.pos_rksv_lock = True

        order_data = OrderData(pos_config.name, order.registrierkasse_receipt_number, order.date_order, 0, 0, 0, 0, 0,
                               order.encrypted_revenue, pos_config.certificate_serial_number,
                               hash_signature(pos_config.name))

        order.order_signature = create_signature(a_trust_session, order_data)

        pos_session.write({'state': 'closed', 'stop_at': fields.Datetime.now()})

    def _get_null_product(self):
        product = self.env['product.template'].search([('name', '=', 'Nullbelegprodukt')])
        if not product:
            product = self.env['product.template'].create({
                'name': 'Nullbelegprodukt',  # Product name
                'type': 'service',
                'list_price': 0,  # Sales price
                'standard_price': 0,
                'available_in_pos': True
            })
        return product

    @api.model
    def write(self, vals):
        temp = super(CustomPOSConfig, self).write(vals)
        if "pos_use_registrierkasse" in vals:
            self._create_starting_receipt(self)
        return temp

    @api.onchange('registrierkasse_aes_key')
    def generate_aes_key(self):
        # This is not a very nice
        for record in self:
            if not record.registrierkasse_aes_key:
                record.registrierkasse_aes_key = generate_aes_key()
            record.registrierkasse_aes_key_checksum = generate_aes_checksum(record.registrierkasse_aes_key)
