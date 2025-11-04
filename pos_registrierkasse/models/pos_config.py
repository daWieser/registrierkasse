import json
import logging
from base64 import urlsafe_b64encode
from odoo import api, models, fields
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from datetime import timedelta, date

from .utils.a_trust_library import SessionData, OrderData, LoginData, get_atrust_api
from .utils.order_utils import chain_hash, hash_signature, format_order_date, base64url_to_base64
from .utils.revenue_counter import encrypt_revenue_counter, generate_aes_key, generate_aes_checksum

_logger = logging.getLogger(__name__)

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
    signature_certificate = fields.Char(string='Signaturzertifikat for Beleg Gruppe')
    certificate_certification_body = fields.Text(string='Zertifizierungsstellen for Beleg Gruppe')

    a_trust_session_key = fields.Char(string='A-Trust Session Key')
    a_trust_session_id = fields.Char(string='A-Trust Session Id')
    pos_use_registrierkasse = fields.Boolean(string='Does this POS use the RKSV module')
    pos_rksv_lock = fields.Boolean(string='If this lock is set, RKSV settings can not be changed')

    monthly_nullbeleg_time = fields.Float(string='Time for Nullbeleg', default=21.0)

    a_trust_environment = fields.Selection(
        [('test', 'Test Environment'), ('production', 'Production Environment'),('qa','A-Trust Abnahme Environment')],
        string='A-Trust Environment',
        default='production'
    )

    def get_atrust_provider(self):
        return get_atrust_api(self.a_trust_environment)

    def copy(self, default=None):
        raise NotImplemented("Copying POS is not allowed when using the Austrian Registrierkasse module")

    @api.model_create_multi
    def create(self, vals_list):
        pos_configs = super().create(vals_list)
        for pos_config in pos_configs:
            if pos_config.pos_use_registrierkasse:
                self._create_starting_receipt(pos_config)
                pos_config._setup_cron_job()
        return pos_configs

    @api.onchange('monthly_nullbeleg_time')
    def _onchange_monthly_nullbeleg_time(self):
        self._setup_cron_job()

    def _create_sequence(self, pos_config):
        sequence = self.env['ir.sequence'].create({
            'name': f"POS Order Sequence for {pos_config.id}",
            'code': f'pos.order.{pos_config.id}',
            'padding': 5,
            'use_date_range': False,
        })
        return sequence

    def _get_null_product(self):
        product_tmpl = self.env['product.template'].search([('name', '=', 'Nullbelegprodukt')], limit=1)
        if not product_tmpl:
            product_tmpl = self.env['product.template'].create({
                'name': 'Nullbelegprodukt', 'type': 'service', 'list_price': 0, 'standard_price': 0,
                'available_in_pos': True, 'categ_id': self.env.ref('product.product_category_all').id,
            })
        return product_tmpl

    def _create_starting_receipt(self, pos_config_rec):
        _logger.info(
            f"RKSV: Creating starting receipt for POS Config '{pos_config_rec.name}' (ID: {pos_config_rec.id})")
        if not pos_config_rec.receipt_sequence_id:
            pos_config_rec.receipt_sequence_id = self._create_sequence(pos_config_rec)

        # Step 1: A-Trust Login & Certificate Info (Specific to starting receipt setup)
        try:
            _logger.info(f"RKSV: Attempting A-Trust login for POS '{pos_config_rec.name}'.")
            atrust_api = pos_config_rec.get_atrust_provider()
            a_trust_api_session = atrust_api.login(
                LoginData(pos_config_rec.a_trust_user_name, pos_config_rec.a_trust_password))
            signature_cert_info = atrust_api.get_certificate_information(pos_config_rec.a_trust_user_name)
            pos_config_rec.a_trust_session_id = a_trust_api_session.sessionId
            pos_config_rec.a_trust_session_key = a_trust_api_session.sessionKey
            pos_config_rec.pos_rksv_lock = True
            pos_config_rec.certificate_serial_number = signature_cert_info.certificate_serial_number
            pos_config_rec.signature_certificate = signature_cert_info.signature_certificate
            pos_config_rec.certificate_certification_body = json.dumps(signature_cert_info.certification_body)
            _logger.info(f"RKSV: POS Config '{pos_config_rec.name}' updated with A-Trust details.")
        except Exception as e:
            _logger.error(f"RKSV CRITICAL: Failed A-Trust setup for POS '{pos_config_rec.name}': {e}", exc_info=True)
            raise UserError(
                f"A-Trust setup failed for '{pos_config_rec.name}'. Starting receipt not created. Error: {e}")

        # Step 2: Create Session & Order
        pos_session = self._rksv_create_pos_session(pos_config_rec, "Starting Receipt Session")
        receipt_num = int(pos_config_rec.receipt_sequence_id.next_by_id())
        order_date_obj = fields.Datetime.now()
        initial_prev_order_sig_hash = hash_signature(pos_config_rec.name)  # Special for first receipt

        order = self._rksv_create_null_order(
            pos_config_rec, pos_session, receipt_num, order_date_obj,
            initial_prev_order_sig_hash, 1)
        order.action_pos_order_paid()

        # Step 3: Perform RKSV Signing
        try:
            # For starting receipt, prospective revenue is 0. JWS uses the initial hash.
            self._rksv_perform_order_signing(pos_config_rec, order, 0, initial_prev_order_sig_hash)
            _logger.info(
                f"RKSV: Starting receipt (Order ID: {order.id}) for POS '{pos_config_rec.name}' signed successfully.")
        except Exception as e:  # Catch errors from _rksv_perform_order_signing
            pos_session.write({'state': 'closed', 'stop_at': fields.Datetime.now()})
            # Error already logged in helper, re-raise UserError for visibility
            raise UserError(f"Failed to sign RKSV starting receipt for POS '{pos_config_rec.name}'. Error: {e}")

        # Step 4: Close Session
        pos_session.write({'state': 'closed', 'stop_at': fields.Datetime.now()})

    def _setup_cron_job(self):
        for config in self:
            _logger.info(f"RKSV: Creating/updating cron job for POS config '{config.name}' (ID: {config.id}).")
            cron_name = f'POS: Create Nullbeleg for {config.name}'
            cron = self.env['ir.cron'].sudo().search([('name', '=', cron_name)], limit=1)
            if not cron:
                cron = self.env['ir.cron'].sudo().create({
                    'name': cron_name,
                    'model_id': self.env.ref('point_of_sale.model_pos_config').id,
                    'state': 'code',
                    'code': f'model.browse({config.id})._cron_create_monthly_receipt()',
                    'interval_number': 1,
                    'interval_type': 'months',
                    'user_id': self.env.user.id,
                })
            hour = int(config.monthly_nullbeleg_time)
            minute = int((config.monthly_nullbeleg_time * 60) % 60)
            today = fields.Date.today()
            next_call_date = today + relativedelta(day=1, months=1)
            last_day_of_month = next_call_date - timedelta(days=1)
            cron.sudo().write({
                'nextcall': last_day_of_month.strftime(f'%Y-%m-%d {hour:02d}:{minute:02d}:00'),
            })

    def _cron_create_monthly_receipt(self):
        if not self.exists() or not self.pos_use_registrierkasse:
            _logger.warning(f"RKSV CRON: Attempted to run for non-existent or non-RKSV POS config (ID: {self.id}). Aborting.")
            return

        _logger.info(f"RKSV CRON: Processing POS Config '{self.name}' (ID: {self.id})")
        pos_session = None
        try:
            # Step 1: Create Session & Order
            pos_session = self._rksv_create_pos_session(self, "Monthly Null Receipt Session")
            receipt_num = int(self.receipt_sequence_id.next_by_id())
            order_date_obj = fields.Datetime.now()

            prev_rksv_order = self.env['pos.order'].search([
                ('config_id', '=', self.id),
                ('registrierkasse_receipt_number', '=', int(receipt_num) - 1),
                ('state', 'in', ['paid', 'done', 'invoiced'])
            ], limit=1, order='registrierkasse_receipt_number desc, id desc')
            prev_order_jws_hash_for_chaining = chain_hash(prev_rksv_order)

            order_sequence_in_session = self.env['pos.order'].search_count([('session_id', '=', pos_session.id)]) + 1

            order = self._rksv_create_null_order(
                self, pos_session, receipt_num, order_date_obj,
                prev_order_jws_hash_for_chaining, order_sequence_in_session)
            order.action_pos_order_paid()

            # Step 2: Perform RKSV Signing
            self._rksv_perform_order_signing(
                self, order,
                self.revenue_counter,  # Prospective revenue for encryption
                prev_order_jws_hash_for_chaining  # Previous hash for JWS payload
            )
            _logger.info(
                f"RKSV CRON: Monthly receipt (Order ID: {order.id}) for POS '{self.name}' signed.")

        except Exception as e:
            _logger.error(f"RKSV CRON: Error processing POS Config '{self.name}': {e}", exc_info=True)
        finally:
            if (pos_session and pos_session.exists()
                    and pos_session.name == f'Monthly Null Receipt Session - {self.name}'
                    and pos_session.state != 'closed'):
                pos_session.write({'state': 'closed', 'stop_at': fields.Datetime.now()})
                _logger.info(f"RKSV CRON: Closed POS Session (ID: {pos_session.id})")

    @api.model
    def write(self, vals):
        res = super(CustomPOSConfig, self).write(vals)
        if "pos_use_registrierkasse" in vals and vals["pos_use_registrierkasse"]:
            for record in self:  # self can be multiple records in write
                if not record.pos_rksv_lock:  # Check if already locked/initialized
                    self._create_starting_receipt(record)
                    record._setup_cron_job()
        return res

    @api.onchange('pos_use_registrierkasse')
    def generate_aes_key(self):
        for record in self:
            if record.pos_use_registrierkasse and not record.registrierkasse_aes_key:  # only if RKSV is true AND key is missing
                record.registrierkasse_aes_key = generate_aes_key()
                record.registrierkasse_aes_key_checksum = generate_aes_checksum(record.registrierkasse_aes_key)
            elif not record.pos_use_registrierkasse:  # Clear keys if RKSV is turned off
                record.registrierkasse_aes_key = False
                record.registrierkasse_aes_key_checksum = False

    def action_download_daten_erfassungs_protokoll(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/download/pos_registrierkasse/{self.id}',
            'target': 'self',
        }

    def _rksv_create_pos_session(self, pos_config_rec, session_name_prefix):
        """
        Checks whether there is already an open POS sessions for the given config.
        If yes, it returns this session. If no, it creates a new one.
        """
        open_sessions = self.env['pos.session'].search([
            ('config_id', '=', pos_config_rec.id),
            ('state', '!=', 'closed')
        ])

        if open_sessions:
            _logger.info(
                f"RKSV: Found {len(open_sessions)} open session(s) for '{pos_config_rec.name}'... Using last one")
            return open_sessions[-1]

        pos_session = self.env['pos.session'].create({
            'name': f'{session_name_prefix} - {pos_config_rec.name}',
            'config_id': pos_config_rec.id,
            'user_id': self.env.user.id,
            'start_at': fields.Datetime.now(),
        })
        _logger.info(f"RKSV: Created POS Session '{pos_session.name}' (ID: {pos_session.id})")
        return pos_session

    def _rksv_create_null_order(self, pos_config_rec, pos_session, receipt_num, order_date_obj,
                                prev_signature_hash_for_order_field, order_sequence_in_session):
        """Helper to create a null POS order for RKSV."""
        order = self.env['pos.order'].create({
            'date_order': order_date_obj,
            'amount_total': 0, 'amount_tax': 0, 'amount_paid': 0, 'amount_return': 0,
            'lines': [(0, 0, {'product_id': self._get_null_product().product_variant_id.id,
                              'price_unit': 0, 'price_subtotal': 0, 'price_subtotal_incl': 0, 'qty': 1})],
            'session_id': pos_session.id,
            'company_id': pos_config_rec.company_id.id or self.env.company.id,
            'registrierkasse_receipt_number': receipt_num,
            'certificate_serial_number': pos_config_rec.certificate_serial_number,
            'prev_order_signature': prev_signature_hash_for_order_field,
            'pos_reference': f"{pos_session.id:05d}-{order_sequence_in_session:03d}-{int(receipt_num):04d}",
            'state': 'done'
        })
        _logger.info(f"RKSV: Created POS Order (ID: {order.id}, Name: {order.name}) with number {receipt_num}.")
        return order

    def _rksv_perform_order_signing(self, pos_config_rec, order_rec,
                                    prospective_revenue_for_encryption,
                                    prev_signature_for_jws_payload):
        """
        Helper to perform the A-Trust signing process for a given order and write results.
        'order_rec' is the pos.order record to be signed and updated.
        'prev_signature_for_jws_payload' is the specific previous hash to include in the JWS.
        """
        _logger.info(
            f"RKSV: Performing signature for Order ID {order_rec.id}, Receipt {order_rec.registrierkasse_receipt_number}")
        encrypted_revenue_val = encrypt_revenue_counter(
            prospective_revenue_for_encryption,
            pos_config_rec.registrierkasse_aes_key,
            pos_config_rec.name,
            order_rec.registrierkasse_receipt_number  # Use number from the order
        )

        a_trust_session_for_signing = SessionData(pos_config_rec.a_trust_session_key, pos_config_rec.a_trust_session_id)

        machine_readable_code = OrderData(
            pos_config_rec.name,
            order_rec.registrierkasse_receipt_number,
            format_order_date(str(order_rec.date_order)),
            0, 0, 0, 0, 0,  # VAT sums are all 0 for null receipts
            encrypted_revenue_val,
            pos_config_rec.certificate_serial_number,
            prev_signature_for_jws_payload  # Use the specific previous hash passed for the JWS
        ).parse()


        try:
            atrust_api = pos_config_rec.get_atrust_provider()
            actual_jws_signature = atrust_api.create_signature(a_trust_session_for_signing, machine_readable_code)
        except PermissionError:
            _logger.warning(f"RKSV: A-Trust re-login needed during signing for POS '{pos_config_rec.name}'.")
            atrust_api = pos_config_rec.get_atrust_provider()
            a_trust_api_session_retry = atrust_api.login(
                LoginData(pos_config_rec.a_trust_user_name, pos_config_rec.a_trust_password))
            pos_config_rec.a_trust_session_key = a_trust_api_session_retry.sessionKey
            pos_config_rec.a_trust_session_id = a_trust_api_session_retry.sessionId
            a_trust_session_for_signing_retry = SessionData(a_trust_api_session_retry.sessionKey,
                                                            a_trust_api_session_retry.sessionId)
            actual_jws_signature = atrust_api.create_signature(a_trust_session_for_signing_retry, machine_readable_code)
        except Exception as e:
            _logger.error(
                f"RKSV CRITICAL: Failed to sign JWS for Order ID {order_rec.id} on POS '{pos_config_rec.name}': {e}",
                exc_info=True)
            raise UserError(
                f"Failed to sign JWS for Order ID {order_rec.id} on POS '{pos_config_rec.name}'. Error: {e}")

        order_rec.encrypted_revenue = encrypted_revenue_val
        order_rec.order_signature = actual_jws_signature
        order_rec.machine_readable_code = machine_readable_code
        _logger.info(f"RKSV: Order ID {order_rec.id} signed. JWS: {actual_jws_signature[:30]}...")
