import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _logger.info("RKSV: Running migration script for version 0.3.")
    configs = env['pos.config'].search([('pos_use_registrierkasse', '=', True)])
    _logger.info(f"RKSV: Found {len(configs)} RKSV-enabled POS configs to process.")
    for config in configs:
        _logger.info(f"RKSV: Creating/updating cron job for POS config '{config.name}' (ID: {config.id}).")
        orders = env['pos.order'].search([('config_id', '=', config.id), ('registrierkasse_receipt_number', '!=', None)])
        config.revenue_counter = sum(int(order.sum_total_rksv * 100.0) for order in orders)
    _logger.info("RKSV: Finished migration script for version 0.3.")
