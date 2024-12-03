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

        let sum_vat_normal = 0;
        let sum_vat_discounted_1 = 0;
        let sum_vat_discounted_2 = 0;
        let sum_vat_null = 0;
        let sum_vat_special = 0;

        const pos = this.pos;
        const order = this;
        this.orderlines.forEach(function (line) {
            const product_taxes = pos.get_taxes_after_fp(line.product.taxes_id, order.fiscal_position);
            const lineAmount = line.get_price_with_tax();

            switch (product_taxes[0].amount) {
                case 20:
                    sum_vat_normal += lineAmount;
                    break;
                case 10:
                    sum_vat_discounted_1 += lineAmount;
                    break;
                case 13:
                    sum_vat_discounted_2 += lineAmount;
                    break;
                case 0:
                    sum_vat_discounted_2 += lineAmount;
                    break;
                default:
                    sum_vat_special += lineAmount;
            }
        });

        const fancyQrObject = {
            "Kassen-ID": this.pos.config.name,
            "Belegnummer": this.sequence_number,
            "Beleg-Datum-Uhrzeit": serializeDateTime(this.date_order),
            "Betrag-Satz-Normal": sum_vat_normal,
            "Betrag-Satz-Ermaessigt-1": sum_vat_discounted_1,
            "Betrag-Satz-Ermaessigt-2": sum_vat_discounted_2,
            "Betrag-Satz-Null": sum_vat_null,
            "Betrag-Satz-Besonders": sum_vat_special,
            "Stand-Umsatz-Zaehler-AES256-ICM": this.encrypted_revenue,
            "Zertifikat-Seriennummer": this.certificate_serial_number,
            "Sig-Voriger-Beleg": this.prev_order_signature
        }

        const json = JSON.stringify(fancyQrObject);
        const base64 = btoa(json);

        const patchedData = {
            ...originalData,
            pos_kasse_code:
                (this.finalized || ["paid", "done", "invoiced"].includes(this.state)) &&
                qrCodeSrc(
                    json
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
    },

    export_as_JSON() {
        const json = super.export_as_JSON();
        json.encrypted_revenue = this.encrypted_revenue;
        json.certificate_serial_number = this.certificate_serial_number;
        json.prev_order_signature = this.prev_order_signature;
        json.order_signature = this.order_signature;
        return json
    }

});
