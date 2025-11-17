/** @odoo-module **/


import {PosOrder} from "@point_of_sale/app/models/pos_order";
import {patch} from '@web/core/utils/patch';
import {qrCodeSrc} from "@point_of_sale/utils";

patch(PosOrder.prototype, {
    export_for_printing(baseUrl, headerData) {
        const results = super.export_for_printing(...arguments);
        if(this.machine_readable_code) {
            const code = this.machine_readable_code + "_" + this._base64UrlToBase64(this.order_signature);
            results.pos_kasse_code = qrCodeSrc(code);
            results.kassenidentifikationsnummer = this.config_id.name;
            results.fortlaufendeBelegnummer = this.registrierkasse_receipt_number;
        }
        return results;
    },

    _base64UrlToBase64(str){
          const base64Encoded = str.replace(/-/g, '+').replace(/_/g, '/');
          const padding = str.length % 4 === 0 ? '' : '='.repeat(4 - (str.length % 4));
          return  base64Encoded + padding;
    },
});
