/** @odoo-module **/


import {Order} from "@point_of_sale/app/store/models";
import {patch} from '@web/core/utils/patch';
import {qrCodeSrc} from "@point_of_sale/utils";

patch(Order.prototype, {
    export_for_printing(baseUrl, headerData) {
        const results = super.export_for_printing(...arguments);
        const code = this.machine_readable_code + "_" + this._base64UrlToBase64(this.order_signature);
        results.pos_kasse_code = qrCodeSrc(code);
        results.kassenidentifikationsnummer = this.pos.config.name;
        results.fortlaufendeBelegnummer = this.registrierkasse_receipt_number;

        return results;
    },

    _base64UrlToBase64(str){
          const base64Encoded = str.replace(/-/g, '+').replace(/_/g, '/');
          const padding = str.length % 4 === 0 ? '' : '='.repeat(4 - (str.length % 4));
          return  base64Encoded + padding;
    },

    init_from_JSON(json) {
        super.init_from_JSON(json);
        this.encrypted_revenue = json.encrypted_revenue;
        this.certificate_serial_number = json.certificate_serial_number;
        this.prev_order_signature = json.prev_order_signature;
        this.order_signature = json.order_signature;
        this.registrierkasse_receipt_number = json.registrierkasse_receipt_number;
        this.sum_vat_normal = json.sum_vat_normal;
        this.sum_vat_discounted_1 = json.sum_vat_discounted_1;
        this.sum_vat_discounted_2 = json.sum_vat_discounted_2;
        this.sum_vat_null = json.sum_vat_null;
        this.sum_vat_special = json.sum_vat_special;
        this.machine_readable_code = json.machine_readable_code;
    },

    export_as_JSON() {
        const json = super.export_as_JSON();
        json.encrypted_revenue = this.encrypted_revenue;
        json.certificate_serial_number = this.certificate_serial_number;
        json.prev_order_signature = this.prev_order_signature;
        json.order_signature = this.order_signature;
        json.registrierkasse_receipt_number = this.registrierkasse_receipt_number;
        json.sum_vat_normal = this.sum_vat_normal;
        json.sum_vat_discounted_1 = this.sum_vat_discounted_1;
        json.sum_vat_discounted_2 = this.sum_vat_discounted_2;
        json.sum_vat_null = this.sum_vat_null;
        json.sum_vat_special = this.sum_vat_special;
        json.is_refund = this._isRefundOrder();
        json.machine_readable_code = this.machine_readable_code;
        return json
    }
});
