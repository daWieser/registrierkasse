/** @odoo-module **/


import {PosOrder} from "@point_of_sale/app/models/pos_order";
import {patch} from '@web/core/utils/patch';
import {qrCodeSrc} from "@point_of_sale/utils";

patch(PosOrder.prototype, {
    export_for_printing(baseUrl, headerData) {
        const results = super.export_for_printing(...arguments);
        results.pos_kasse_code = qrCodeSrc(this.machine_readable_code);
        results.kassenidentifikationsnummer = this.config_id.name;
        results.fortlaufendeBelegnummer = this.registrierkasse_receipt_number;

        return results;
    }
});
