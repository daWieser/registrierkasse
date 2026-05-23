from .order_utils import chain_hash, hash_signature, format_order_date
from .revenue_counter import encrypt_revenue_counter
from ..libs.a_trust.a_trust_library import SessionData, OrderData, LoginData


### This script can be used to rebuild the Datenerfassungsprotokoll from scratch, if the encryption chain is broken.raise RedirectWarning(_('Warning message'), action_id, _('Button text'))
### Usage:
### Run odoo console:
### python3 odoo-bin shell --addons-path=<addons> -d <database-name>
###
### use the following commands:
### from odoo.addons.pos_registrierkasse.models.utils.dep_rebuild import rebuild_dep
### config = env['pos.config'].browse(<pos-config-id>)
### rebuild_dep(config)
### env.cr.commit()

def rebuild_dep(config, rehash_start=False):
    orders = config.env['pos.order'].search([
        ('session_id.config_id', '=', config.id),
        ('registrierkasse_receipt_number', '!=', 0)
    ], order='registrierkasse_receipt_number asc')

    revenue_counter = 0

    for order in orders:
        receipt_number = order.registrierkasse_receipt_number
        if receipt_number == 1:
            if rehash_start:
                order.prev_order_signature = hash_signature(config.name)
            else:
                order.machine_readable_code = split_mrc(order.machine_readable_code)
                continue
        else:
            revenue_counter += int(order.sum_vat_normal * 100.0) \
                + int(order.sum_vat_discounted_1 * 100.0) \
                + int(order.sum_vat_discounted_2 * 100.0) \
                + int(order.sum_vat_null * 100.0) \
                + int(order.sum_vat_special * 100.0)

            prev_order = config.env['pos.order'].search(
                [('registrierkasse_receipt_number', '=', int(receipt_number) - 1),
                 ('config_id', '=', config.id)], limit=1)
            order.prev_order_signature = chain_hash(prev_order)

        if len(order.refunded_order_id) == len(order.lines):
            encrypted_revenue = "U1RP"  # Storno
        else:
            encrypted_revenue = encrypt_revenue_counter(
                revenue_counter,
                config.registrierkasse_aes_key,
                config.name,
                receipt_number
            )

        order.machine_readable_code = OrderData(
            config.name,
            str(receipt_number),
            format_order_date(str(order.date_order)),
            order.sum_vat_normal,
            order.sum_vat_discounted_1,
            order.sum_vat_discounted_2,
            order.sum_vat_null,
            order.sum_vat_special,
            encrypted_revenue,
            config.certificate_serial_number,
            order.prev_order_signature
        ).parse()

        try:
            atrust_api = config.get_atrust_provider()
            a_trust_session_data_obj = SessionData(config.a_trust_session_key, config.a_trust_session_id)
            order_signature = atrust_api.create_signature(a_trust_session_data_obj, order.machine_readable_code)
        except PermissionError:
            atrust_api = config.get_atrust_provider()
            a_trust_login_session = atrust_api.login(LoginData(config.a_trust_user_name, config.a_trust_password))
            config.write({
                'a_trust_session_key': a_trust_login_session.sessionKey,
                'a_trust_session_id': a_trust_login_session.sessionId
            })
            a_trust_session_data_obj_retry = SessionData(a_trust_login_session.sessionKey,
                                                         a_trust_login_session.sessionId)
            order_signature = atrust_api.create_signature(a_trust_session_data_obj_retry, order.machine_readable_code)

        order.order_signature = order_signature
        order.encrypted_revenue = encrypted_revenue
    config.revenue_counter = revenue_counter

def split_mrc(input_str):
    parts = input_str.split("_")
    part1_list = parts[:13]
    part1 = "_".join(part1_list)
    return part1