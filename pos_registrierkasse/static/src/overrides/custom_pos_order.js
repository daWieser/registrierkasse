/** @odoo-module **/


import {PosOrder} from "@point_of_sale/app/models/pos_order";
import {patch} from '@web/core/utils/patch';
import {qrCodeSrc} from "@point_of_sale/utils";
import {formatDateTime, parseDateTime} from "@web/core/l10n/dates";

patch(PosOrder.prototype, {
    export_for_printing(baseUrl, headerData) {
        const results = super.export_for_printing(...arguments);

        const date = parseDateTime(this.date_order);
        let formatted = new Intl.NumberFormat('de-DE', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        })
        const machine_readable_code = "_R1-AT0_" +
            this.session_id.config_id.name + '_' +
            this.registrierkasse_receipt_number + '_' +
            formatDateTime(date, {format: "yyyy-MM-dd'T'HH:mm:ss", tz: "Europe/Vienna"}) + '_' +
            formatted.format(this.sum_vat_normal) + '_' +
            formatted.format(this.sum_vat_discounted_1) + '_' +
            formatted.format(this.sum_vat_discounted_1) + '_' +
            formatted.format(this.sum_vat_null) + '_' +
            formatted.format(this.sum_vat_special) + '_' +
            this.encrypted_revenue + '_' +
            this.certificate_serial_number + '_' +
            this.prev_order_signature + '_' +
            this.order_signature;
        results.pos_kasse_code = qrCodeSrc(machine_readable_code)

        return results;
    }
});
