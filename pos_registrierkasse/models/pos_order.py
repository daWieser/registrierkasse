from odoo import api, models, fields, _
from odoo.exceptions import UserError

from .libs.a_trust.a_trust_library import SessionData, OrderData, LoginData
from .utils.order_utils import chain_hash, format_order_date, base64url_to_base64
from .utils.revenue_counter import encrypt_revenue_counter


class CustomPOSOrder(models.Model):
    _inherit = 'pos.order'

    encrypted_revenue = fields.Char(string='Encrypted revenue counter', translate=True)
    order_signature = fields.Char(string='Signature from signing unit', translate=True)
    prev_order_signature = fields.Char(string='Signature of the previous invoice', translate=True)
    machine_readable_code = fields.Char(string='The whole code sent to A-Trust', translate=True)
    certificate_serial_number = fields.Char(string='Serial number of the ', translate=True)
    registrierkasse_receipt_number = fields.Integer(string='Sequence of receipt specific to RKSV ', index=True)

    sum_vat_normal = fields.Float(string='VAT Normal', digits=(16, 2), required=True, default=0)
    sum_vat_discounted_1 = fields.Float(string='VAT Discounted 1', digits=(16, 2), required=True, default=0)
    sum_vat_discounted_2 = fields.Float(string='VAT Discounted 2', digits=(16, 2), required=True, default=0)
    sum_vat_null = fields.Float(string='VAT null', digits=(16, 2), required=True, default=0)
    sum_vat_special = fields.Float(string='VAT special', digits=(16, 2), required=True, default=0)

    def _generate_pos_reference(self, order):
        """Generate a consistent pos_reference for an order."""
        order_sequence_in_session = self.search_count([('session_id', '=', order.session_id.id)])
        return (f"{order.session_id.id:05d}-"
                  f"{order_sequence_in_session:03d}-"
                  f"{order.registrierkasse_receipt_number:04d}")

    def _get_rksv_signature(self, config, order_vals, is_refund=False):
        """Helper method to perform RKSV signing."""
        config.revenue_counter += order_vals.get('amount_total', 0.0)
        receipt_number = int(config.receipt_sequence_id.next_by_id())

        prev_order = self.env['pos.order'].search(
            [('registrierkasse_receipt_number', '=', int(receipt_number) - 1),
             ('config_id', '=', config.id)], limit=1)

        if is_refund:
            encrypted_revenue = "U1RP"  # Storno
        else:
            encrypted_revenue = encrypt_revenue_counter(
                config.revenue_counter,
                config.registrierkasse_aes_key,
                config.name,
                receipt_number
            )

        date_order_str = order_vals.get('date_order')
        if not isinstance(date_order_str, str):
            date_order_str = fields.Datetime.to_string(fields.Datetime.now())

        prev_order_signature = chain_hash(prev_order)

        machine_readable_code = OrderData(
            config.name,
            receipt_number,
            format_order_date(date_order_str),
            order_vals.get("sum_vat_normal", 0.0),
            order_vals.get("sum_vat_discounted_1", 0.0),
            order_vals.get("sum_vat_discounted_2", 0.0),
            order_vals.get("sum_vat_null", 0.0),
            order_vals.get("sum_vat_special", 0.0),
            encrypted_revenue,
            config.certificate_serial_number,
            prev_order_signature
        ).parse()

        try:
            atrust_api = config.get_atrust_provider()
            a_trust_session_data_obj = SessionData(config.a_trust_session_key, config.a_trust_session_id)
            order_signature = atrust_api.create_signature(a_trust_session_data_obj, machine_readable_code)
        except PermissionError:
            atrust_api = config.get_atrust_provider()
            a_trust_login_session = atrust_api.login(LoginData(config.a_trust_user_name, config.a_trust_password))
            config.write({
                'a_trust_session_key': a_trust_login_session.sessionKey,
                'a_trust_session_id': a_trust_login_session.sessionId
            })
            a_trust_session_data_obj_retry = SessionData(a_trust_login_session.sessionKey, a_trust_login_session.sessionId)
            order_signature = atrust_api.create_signature(a_trust_session_data_obj_retry, machine_readable_code)

        return {
            'encrypted_revenue': encrypted_revenue,
            'order_signature': order_signature,
            'machine_readable_code': machine_readable_code,
            'certificate_serial_number': config.certificate_serial_number,
            'prev_order_signature': prev_order_signature,
            'registrierkasse_receipt_number': receipt_number,
        }

    @api.model
    def sign_order(self, order_data_dict):
        session_id = order_data_dict.get('session_id')
        if not isinstance(session_id, int):
            return {'error': 'Invalid session_id in order_data_dict'}

        session = self.env['pos.session'].browse(session_id)
        if not session.exists():
            return {'error': f'Session {session_id} not found.'}

        config = session.config_id
        if not config.exists() or not config.pos_use_registrierkasse:
            return {'rksv_signed': False, 'message': 'RKSV not active for this POS'}

        is_refund = order_data_dict.get("has_refundable_lines", False)
        return self._get_rksv_signature(config, order_data_dict, is_refund=is_refund)

    @api.model
    def _process_order(self, *args, **kwargs):
        order_id = super()._process_order(*args, **kwargs)
        order_rec = self.browse(order_id)

        if order_rec and order_rec.registrierkasse_receipt_number:
            new_ref = self._generate_pos_reference(order_rec)
            order_rec.write({'pos_reference': new_ref})

        return order_id

    def _prepare_refund_values(self, current_session):
        self.ensure_one()
        values = super()._prepare_refund_values(current_session)
        values.update({
            'registrierkasse_receipt_number': None,
            'order_signature': None,
            'prev_order_signature': None,
            'machine_readable_code': None,
            'encrypted_revenue': None,
            'certificate_serial_number': None,
        })
        return values

    def _refund(self):
        refund_orders = super()._refund()

        for order in self:
            refund_order = refund_orders.filtered(lambda r: r.refunded_order_id == order)
            if not refund_order:
                continue

            config = refund_order.session_id.config_id
            if not config.pos_use_registrierkasse:
                continue

            refund_order.write({
                'sum_vat_normal': -order.sum_vat_normal,
                'sum_vat_discounted_1': -order.sum_vat_discounted_1,
                'sum_vat_discounted_2': -order.sum_vat_discounted_2,
                'sum_vat_null': -order.sum_vat_null,
                'sum_vat_special': -order.sum_vat_special,
            })

            refund_vals = {
                'amount_total': refund_order.amount_total,
                'date_order': refund_order.date_order,
                'sum_vat_normal': refund_order.sum_vat_normal,
                'sum_vat_discounted_1': refund_order.sum_vat_discounted_1,
                'sum_vat_discounted_2': refund_order.sum_vat_discounted_2,
                'sum_vat_null': refund_order.sum_vat_null,
                'sum_vat_special': refund_order.sum_vat_special,
            }

            rksv_data = self._get_rksv_signature(config, refund_vals, is_refund=True)
            refund_order.write(rksv_data)

            new_ref = self._generate_pos_reference(refund_order)
            refund_order.write({'pos_reference': new_ref})

        return refund_orders

    def unlink(self):
        """Prevent deletion of RKSV-signed orders."""
        for order in self:
            if order.registrierkasse_receipt_number:
                raise UserError(_('Eine bereits mit der Registrierkasse (RKSV) signierte Bestellung kann nicht gelöscht werden. Bitte erstellen Sie stattdessen eine Erstattung.'))
        return super(CustomPOSOrder, self).unlink()
