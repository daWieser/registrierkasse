from odoo import api, models, fields

from .utils.a_trust_library import SessionData, OrderData, LoginData, create_signature, login
from .utils.order_utils import encrypt_revenue_counter, chain_hash


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

    def _export_for_ui(self, order):
        result = super(CustomPOSOrder, self)._export_for_ui(order)
        result['encrypted_revenue'] = order.encrypted_revenue
        result['order_signature'] = order.order_signature
        result['prev_order_signature'] = order.prev_order_signature
        result['certificate_serial_number'] = order.certificate_serial_number
        result['registrierkasse_receipt_number'] = order.registrierkasse_receipt_number
        result['sum_vat_normal'] = order['sum_vat_normal']
        result['sum_vat_discounted_1'] = order['sum_vat_discounted_1']
        result['sum_vat_discounted_2'] = order['sum_vat_discounted_2']
        result['sum_vat_null'] = order['sum_vat_null']
        result['sum_vat_special'] = order['sum_vat_special']

        return result

    @api.model
    def _order_fields(self, ui_order):
        result = super(CustomPOSOrder, self)._order_fields(ui_order)
        result['encrypted_revenue'] = ui_order['encrypted_revenue']
        result['order_signature'] = ui_order['order_signature']
        result['prev_order_signature'] = ui_order['prev_order_signature']
        result['certificate_serial_number'] = ui_order['certificate_serial_number']
        result['registrierkasse_receipt_number'] = ui_order['registrierkasse_receipt_number']
        result['sum_vat_normal'] = ui_order['sum_vat_normal']
        result['sum_vat_discounted_1'] = ui_order['sum_vat_discounted_1']
        result['sum_vat_discounted_2'] = ui_order['sum_vat_discounted_2']
        result['sum_vat_null'] = ui_order['sum_vat_null']
        result['sum_vat_special'] = ui_order['sum_vat_special']
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

        encrypt_revenue = encrypt_revenue_counter(config.revenue_counter, config.registrierkasse_aes_key,
                                                       config.name, receipt_number)

        a_trust_session = SessionData(config.a_trust_session_key, config.a_trust_session_id)

        order_data = OrderData(config.name,
                               receipt_number,
                               order['date_order'],
                               order["sum_vat_normal"],
                               order["sum_vat_discounted_1"],
                               order["sum_vat_discounted_2"],
                               order["sum_vat_null"],
                               order["sum_vat_special"],
                               encrypt_revenue,
                               config.certificate_serial_number,
                               chain_hash(config, prev_order))

        try:
            order_signature = create_signature(a_trust_session, order_data)
        except PermissionError:
            a_trust_session = login(LoginData(config.a_trust_user_name, config.a_trust_password))
            config.a_trust_session_key = a_trust_session.sessionKey
            config.a_trust_session_id = a_trust_session.sessionId
            order_signature = create_signature(a_trust_session, order_data)

        return {
            'encrypted_revenue': encrypt_revenue,
            'order_signature': order_signature,
            'certificate_serial_number': config.certificate_serial_number,
            'prev_order_signature': order_data.prev_order_signature,
            'registrierkasse_receipt_number': receipt_number
        }