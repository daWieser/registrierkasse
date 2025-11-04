/** @odoo-module **/


import {PaymentScreen} from "@point_of_sale/app/screens/payment_screen/payment_screen";
import {patch} from '@web/core/utils/patch';


patch(PaymentScreen.prototype, {
    async _finalizeValidation() {

        let sum_vat_normal = 0;
        let sum_vat_discounted_1 = 0;
        let sum_vat_discounted_2 = 0;
        let sum_vat_null = 0;
        let sum_vat_special = 0;

        const order = this.currentOrder;
        // order.recomputeOrderData()
        order.orderlines.forEach(function (line) {
            const lineAmount = line.get_price_with_tax();
            const taxPercentage = line.tax_ids?.[0]?.amount ?? 0;

            switch (taxPercentage) {
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
                    sum_vat_null += lineAmount;
                    break;
                default:
                    sum_vat_special += lineAmount;
            }
        });
        order.sum_vat_normal = sum_vat_normal;
        order.sum_vat_discounted_1 = sum_vat_discounted_1;
        order.sum_vat_discounted_2 = sum_vat_discounted_2;
        order.sum_vat_null = sum_vat_null;
        order.sum_vat_special = sum_vat_special;

        const signature = await this.orm.call(
            "pos.order",
            "sign_order",
            [this.currentOrder.export_as_JSON()]
        );
        order.certificate_serial_number = signature.certificate_serial_number
        order.prev_order_signature = signature.prev_order_signature
        order.machine_readable_code = signature.machine_readable_code
        order.order_signature = signature.order_signature
        order.encrypted_revenue = signature.encrypted_revenue
        order.registrierkasse_receipt_number = signature.registrierkasse_receipt_number

        return super._finalizeValidation();
    }
})