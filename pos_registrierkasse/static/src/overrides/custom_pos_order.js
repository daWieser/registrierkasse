/** @odoo-module **/


import {Order} from "@point_of_sale/app/store/models";
import {patch} from '@web/core/utils/patch';
import {qrCodeSrc} from "@point_of_sale/utils";
import {
    serializeDateTime,
} from "@web/core/l10n/dates";

patch(Order.prototype, {
    export_for_printing() {
        // Call the original method
        const originalData = super.export_for_printing();


        let formatted = new Intl.NumberFormat('de-DE', {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        })

        const machine_readable_code = "_R1-AT0_" +
            this.pos.config.name + '_' +
            this.registrierkasse_receipt_number + '_' +
            serializeDateTime(this.date_order) + '_' +
            formatted.format(this.sum_vat_normal) + '_' +
            formatted.format(this.sum_vat_discounted_1) + '_' +
            formatted.format(this.sum_vat_discounted_1) + '_' +
            formatted.format(this.sum_vat_null) + '_' +
            formatted.format(this.sum_vat_special) + '_' +
            this.encrypted_revenue + '_' +
            this.certificate_serial_number + '_' +
            this.prev_order_signature + '_' +
            this.order_signature;

        console.log(machine_readable_code)
        const patchedData = {
            ...originalData,
            pos_kasse_code:
                (this.finalized || ["paid", "done", "invoiced"].includes(this.state)) &&
                qrCodeSrc(
                    machine_readable_code
                ),
        };
        return patchedData;
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
        return json
    }

});
