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
        const pos = order.pos;
        order.orderlines.forEach(function (line) {
            const product_taxes = pos.get_taxes_after_fp(line.product.taxes_id, order.fiscal_position);
            const lineAmount = line.get_price_with_tax();

            const taxAmount = product_taxes[0]?.amount ?? 0;

            switch (taxAmount) {
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
        this.currentOrder.sum_vat_normal = sum_vat_normal;
        this.currentOrder.sum_vat_discounted_1 = sum_vat_discounted_1;
        this.currentOrder.sum_vat_discounted_2 = sum_vat_discounted_2;
        this.currentOrder.sum_vat_null = sum_vat_null;
        this.currentOrder.sum_vat_special = sum_vat_special;

        const signature = await this.orm.call(
            "pos.order",
            "sign_order",
            [this.currentOrder.export_as_JSON()]
        );
        this.currentOrder.certificate_serial_number = signature.certificate_serial_number
        this.currentOrder.prev_order_signature = signature.prev_order_signature
        this.currentOrder.order_signature = signature.order_signature
        this.currentOrder.encrypted_revenue = signature.encrypted_revenue
        this.currentOrder.registrierkasse_receipt_number = signature.registrierkasse_receipt_number


        return super._finalizeValidation();
    }
})