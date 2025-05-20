from odoo import api, models, fields
from odoo.exceptions import UserError

from .utils.a_trust_library import SessionData, OrderData, LoginData, create_signature, login
from .utils.order_utils import chain_hash, format_order_date
from .utils.revenue_counter import encrypt_revenue_counter

class CustomPOSOrder(models.Model):
    _inherit = 'pos.order'

    encrypted_revenue = fields.Char(string='Encrypted revenue counter', translate=True)
    order_signature = fields.Char(string='Signature from signing unit', translate=True)
    prev_order_signature = fields.Char(string='Signature of the previous invoice', translate=True)
    certificate_serial_number = fields.Char(string='Serial number of the ', translate=True)
    registrierkasse_receipt_number = fields.Integer(string='Sequence of receipt specific to RKSV ', index=True)

    sum_vat_normal = fields.Float(string='VAT Normal', digits=(16, 2), required=True, default=0)
    sum_vat_discounted_1 = fields.Float(string='VAT Discounted 1', digits=(16, 2), required=True, default=0)
    sum_vat_discounted_2 = fields.Float(string='VAT Discounted 2', digits=(16, 2), required=True, default=0)
    sum_vat_null = fields.Float(string='VAT null', digits=(16, 2), required=True, default=0)
    sum_vat_special = fields.Float(string='VAT special', digits=(16, 2), required=True, default=0)

    @api.model
    def sign_order(self, order_data_dict):  # Expects a dictionary
        session_id = order_data_dict.get('session_id')
        if not isinstance(session_id, int):
            # Handle error: session_id missing or not an int
            return {'error': 'Invalid session_id in order_data_dict'}

        session = self.env['pos.session'].browse(session_id)
        if not session.exists():
            return {'error': f'Session {session_id} not found.'}

        config = session.config_id
        if not config.exists():
            return {'error': f'Config for session {session_id} not found.'}

        if not config.pos_use_registrierkasse:
            return {'rksv_signed': False, 'message': 'RKSV not active for this POS'}

        config.revenue_counter = config.revenue_counter + order_data_dict.get('amount_total', 0.0)

        receipt_number = config.receipt_sequence_id.next_by_id()

        prev_order = self.env['pos.order'].search(
            [('registrierkasse_receipt_number', '=', int(receipt_number) - 1),
             ('config_id', '=', config.id)])

        if order_data_dict.get("has_refundable_lines", False):
            encrypted_revenue = "U1RP"  # base64 encoded "STO" string
        else:
            encrypted_revenue = encrypt_revenue_counter(
                config.revenue_counter,
                config.registrierkasse_aes_key,
                config.name,
                receipt_number
            )

        a_trust_session_data_obj = SessionData(config.a_trust_session_key, config.a_trust_session_id)

        # Ensure date_order is a string
        date_order_str = order_data_dict.get('date_order')
        if not isinstance(date_order_str, str):
            date_order_str = fields.Datetime.to_string(fields.Datetime.now())

        order_data_payload = OrderData(
            config.name,
            receipt_number,
            format_order_date(date_order_str),
            order_data_dict.get("sum_vat_normal", 0.0),
            order_data_dict.get("sum_vat_discounted_1", 0.0),
            order_data_dict.get("sum_vat_discounted_2", 0.0),
            order_data_dict.get("sum_vat_null", 0.0),
            order_data_dict.get("sum_vat_special", 0.0),
            encrypted_revenue,
            config.certificate_serial_number,
            chain_hash(config, prev_order)
        )

        try:
            order_signature = create_signature(a_trust_session_data_obj, order_data_payload)
        except PermissionError:
            a_trust_login_session = login(LoginData(config.a_trust_user_name, config.a_trust_password))
            config.a_trust_session_key = a_trust_login_session.sessionKey
            config.a_trust_session_id = a_trust_login_session.sessionId
            a_trust_session_data_obj_retry = SessionData(a_trust_login_session.sessionKey,
                                                         a_trust_login_session.sessionId)
            order_signature = create_signature(a_trust_session_data_obj_retry, order_data_payload)
        except Exception as e:
            return {'error': f'A-Trust signature creation failed: {e}'}

        return {
            'encrypted_revenue': encrypted_revenue,
            'order_signature': order_signature,
            'certificate_serial_number': config.certificate_serial_number,
            'prev_order_signature': order_data_payload.prev_order_signature,
            'registrierkasse_receipt_number': receipt_number,
            'rksv_signed': True
        }
