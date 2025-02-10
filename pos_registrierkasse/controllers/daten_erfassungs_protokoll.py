from datetime import datetime
import json
import base64

import pytz
from odoo import http
from odoo.http import request, content_disposition

from odoo.addons.pos_registrierkasse.models.utils.a_trust_library import OrderData


class DatenErfassungsProtokollController(http.Controller):

    @http.route('/download/pos_registrierkasse/<int:record_id>', type='http', auth='user')
    def download_your_file(self, record_id, **kwargs):
        config = request.env['pos.config'].browse(record_id)
        if not config.exists():
            return request.not_found()
        if not config.pos_use_registrierkasse:
            return request.not_found()

        data = self._file_content(request, config)
        json_content = json.dumps(data, indent=4)
        file_data = base64.b64encode(json_content.encode()).decode()

        # Send file as response
        return request.make_response(
            base64.b64decode(file_data),
            headers=[
                ('Content-Type', 'application/json'),
                ('Content-Disposition', content_disposition('Datenerfassungsprotokoll.json'))
            ]
        )

    def _file_content(self, request, config):
        orders = request.env['pos.order'].search([
            ('session_id.config_id', '=', config.id)
        ])

        orders_short = [self._create_short_representation(order, config) for order in orders]

        return {
            "Belege - Gruppe": [
                {
                    'Signaturzertifikat': config.signature_certificate,
                    'Zertifizierungsstellen': json.loads(
                        config.certificate_certification_body) if config.certificate_certification_body else [],
                    'Belege-kompakt': orders_short
                }
            ]

        }
    def _create_short_representation(self, order, config):
        utc_time = order['date_order'].replace(tzinfo=pytz.UTC)

        local_time = utc_time.astimezone(pytz.timezone("Europe/Vienna"))
        iso_date = datetime.strftime(local_time, "%Y-%m-%dT%H:%M:%S")

        order_data = OrderData(config.name,
                               order.registrierkasse_receipt_number,
                               iso_date,
                               order.sum_vat_normal,
                               order.sum_vat_discounted_1,
                               order.sum_vat_discounted_2,
                               order.sum_vat_null,
                               order.sum_vat_special,
                               order.encrypted_revenue,
                               config.certificate_serial_number,
                               order.prev_order_signature)
        return order_data.parse()