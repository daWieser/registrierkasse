from odoo import api, models, fields
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from hashlib import sha256
from base64 import b64decode, b64encode

from .a_trust_library import SessionData, OrderData, LoginData, create_signature, login


class CustomPOSOrder(models.Model):
    _inherit = 'pos.order'

    encrypted_revenue = fields.Char(string='Encrypted revenue counter', translate=True)
    order_signature = fields.Char(string='Signature from signing unit', translate=True)
    prev_order_signature = fields.Char(string='Signature of the previous invoice', translate=True)
    certificate_serial_number = fields.Char(string='Serial number of the ', translate=True)
    registrierkasse_receipt_number = fields.Integer(string='Sequence of receipt specific to RKSV ', index=True)

    def _export_for_ui(self, order):
        result = super(CustomPOSOrder, self)._export_for_ui(order)
        result['encrypted_revenue'] = order.encrypted_revenue
        result['order_signature'] = order.order_signature
        result['prev_order_signature'] = order.prev_order_signature
        result['certificate_serial_number'] = order.certificate_serial_number
        result['registrierkasse_receipt_number'] = order.registrierkasse_receipt_number

        return result

    @api.model
    def _order_fields(self, ui_order):
        result = super(CustomPOSOrder, self)._order_fields(ui_order)
        result['encrypted_revenue'] = ui_order['encrypted_revenue']
        result['order_signature'] = ui_order['order_signature']
        result['prev_order_signature'] = ui_order['prev_order_signature']
        result['certificate_serial_number'] = ui_order['certificate_serial_number']
        result['registrierkasse_receipt_number'] = ui_order['registrierkasse_receipt_number']
        return result

    @api.model
    def sign_order(self, order):
        session_id = order['pos_session_id']

        session = self.env['pos.session'].browse(session_id)
        config = session.config_id

        config.revenue_counter = config.revenue_counter + order['amount_total']

        receipt_number = config.receipt_sequence_id.next_by_id()
        prev_order = self.env['pos.order'].search(
            [('registrierkasse_receipt_number', '=', int(receipt_number) - 1),
             ('config_id', '=', config.id)])

        encrypt_revenue = self.encrypt_revenue_counter(config.revenue_counter, config.registrierkasse_aes_key,
                                                       config.name, receipt_number)

        a_trust_session = SessionData(config.a_trust_session_key, config.a_trust_session_id)
        order_data = OrderData(config.name, receipt_number, order['date_order'], 0, 0, 0, 0, encrypt_revenue,
                               config.certificate_serial_number, prev_order.order_signature)

        try:
            sig = create_signature(a_trust_session, order_data)
        except PermissionError:
            a_trust_session = login(LoginData(config.a_trust_user_name, config.a_trust_password))
            config.a_trust_session_key = a_trust_session.sessionKey
            config.a_trust_session_id = a_trust_session.sessionId
            sig = create_signature(a_trust_session, order_data)

        return {
            'encrypted_revenue': encrypt_revenue,
            'order_signature': sig,
            'certificate_serial_number': config.certificate_serial_number,
            'prev_order_signature': prev_order.order_signature,
            'registrierkasse_receipt_number': receipt_number
        }

    def encrypt_revenue_counter(self, revenue_counter, aes_key, pos_name, sequence_number):
        cipher = Cipher(algorithms.AES(b64decode(aes_key)), self._init_vector(pos_name, sequence_number))
        encryptor = cipher.encryptor()

        # According to the detailed Specification, the length of a block needs to be 16 Bytes.
        # However for the qr code it needs to be 5 bytes. So the first 5 bytes of the revenue counter are filled
        data = int(revenue_counter * 100).to_bytes(5, byteorder='big') + b'\x00' * 11

        encrypted =  encryptor.update(data) + encryptor.finalize()[:5]
        return str(b64encode(encrypted))

    def _init_vector(self, pos_name, bill_number):
        return modes.CTR(sha256((pos_name + str(bill_number)).encode('utf-8')).digest()[:16])
