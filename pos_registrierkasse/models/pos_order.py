from inspect import signature

from odoo import api, models, fields
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from hashlib import sha256
from base64 import b64decode


class CustomPOSOrder(models.Model):
    _inherit = 'pos.order'

    encrypted_revenue = fields.Char(string='Encrypted revenue counter', translate=True)
    order_signature = fields.Char(string='Signature from signing unit', translate=True)
    prev_order_signature = fields.Char(string='Signature of the previous invoice', translate=True)
    certificate_serial_number = fields.Char(string='Serial number of the ', translate=True)

    @api.model
    def create_from_ui(self, orders, draft=False):
        # Custom logic before starting the session
        print("UI Sync started")

        # Call the original method
        result = super(CustomPOSOrder, self).create_from_ui(orders, draft)

        if len(orders) == 1:  # This is the wrong check. If only 1 is synced after disconect, this will sign the bill, enven though it shouldn't
            order = orders[0]
            order_name = order['data']['name']

            existing_order = self.env['pos.order'].search([('pos_reference', '=', order_name)])[0]
            config = existing_order.config_id

            config.revenue_counter = existing_order.config_id.revenue_counter + order['data'][
                'amount_total']
            result[0]['encrypted'] = self._encrypt_revenue_counter(config.revenue_counter,
                                                                   config.registrierkasse_aes_key,
                                                                   config.name, existing_order.sequence_number)
            result[0]['signatureValue'] = self._create_signature()
            result[0]['certificateSerialNumber'] = self._create_signature()

        elif len(orders) > 1:
            print("create 0 Beleg for recovery")

        return result

    def _export_for_ui(self, order):
        result = super(CustomPOSOrder, self)._export_for_ui(order)
        result['encrypted_revenue'] = order.encrypted_revenue
        result['order_signature'] = order.order_signature
        result['prev_order_signature'] = order.prev_order_signature
        result['certificate_serial_number'] = order.certificate_serial_number

        return result

    @api.model
    def _order_fields(self, ui_order):
        result = super(CustomPOSOrder, self)._order_fields(ui_order)
        result['encrypted_revenue'] = ui_order['encrypted_revenue']
        result['order_signature'] = ui_order['order_signature']
        result['prev_order_signature'] = ui_order['prev_order_signature']
        result['certificate_serial_number'] = ui_order['certificate_serial_number']
        return result

    @api.model
    def sign_order(self, order):
        session_id = order['pos_session_id']

        session = self.env['pos.session'].browse(session_id)
        config = session.config_id

        config.revenue_counter = config.revenue_counter + order['amount_total']
        sig = self._create_signature()
        return {
            'encrypted_revenue': self._encrypt_revenue_counter(config.revenue_counter, config.registrierkasse_aes_key,
                                                               config.name, order['sequence_number']),
            'order_signature': sig,
            'certificate_serial_number': '1234',
            'prev_order_signature':'2552'
        }

    def _encrypt_revenue_counter(self, revenue_counter, aes_key, pos_name, sequence_number):
        cipher = Cipher(algorithms.AES(b64decode(aes_key)), self._init_vector(pos_name, sequence_number))
        encryptor = cipher.encryptor()

        data = int(revenue_counter * 100).to_bytes(5, byteorder='big')

        return encryptor.update(data) + encryptor.finalize()

    def _init_vector(self, pos_name, bill_number):
        return modes.CTR(sha256((pos_name + str(bill_number)).encode('utf-8')).digest()[:16])

    def _create_signature(self):
        return 'signature'
