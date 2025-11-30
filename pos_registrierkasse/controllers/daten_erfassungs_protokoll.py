import json
import base64

from odoo import http
from odoo.http import request, content_disposition

from odoo.addons.pos_registrierkasse.models.utils.order_utils import jws_signature_compact


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
            ('session_id.config_id', '=', config.id),
            ('registrierkasse_receipt_number', '!=', 0)
        ], order='registrierkasse_receipt_number asc')

        orders_short = [jws_signature_compact(order.machine_readable_code, order.order_signature) for order in orders]

        return {
            "Belege-Gruppe": [
                {
                    'Signaturzertifikat': config.signature_certificate,
                    'Zertifizierungsstellen': json.loads(
                        config.certificate_certification_body) if config.certificate_certification_body else [],
                    'Belege-kompakt': orders_short
                }
            ]
        }

    @http.route('/download/pos_registrierkasse/cryptographic_container/<int:record_id>', type='http', auth='user')
    def download_cryptographic_container(self, record_id, **kwargs):
        config = request.env['pos.config'].browse(record_id)
        if not config.exists():
            return request.not_found()
        if not config.pos_use_registrierkasse:
            return request.not_found()

        data = self._cryptographic_container(config)
        json_content = json.dumps(data, indent=4)

        return request.make_response(
            json_content,
            headers=[
                ('Content-Type', 'application/json'),
                ('Content-Disposition', content_disposition('cryptographicMaterialContainer.json'))
            ]
        )

    def _cryptographic_container(self, config):
        return {
            "base64AESKey": config.registrierkasse_aes_key,
            "certificateOrPublicKeyMap": {
                config.certificate_serial_number: {
                    "id": config.certificate_serial_number,
                    "signatureDeviceType": "CERTIFICATE",
                    "signatureCertificateOrPublicKey": config.signature_certificate
                }
            }
        }
