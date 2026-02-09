/** @odoo-module **/


import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from '@web/core/utils/patch';


patch(PaymentScreen.prototype, {
    async _finalizeValidation() {

        const order = this.currentOrder;
        order.recomputeOrderData()

        const has_lines = order.lines.some((line) => line.get_quantity() !== 0);

        if (navigator.onLine && has_lines) {
            try {
                let sum_vat_normal = 0;
                let sum_vat_discounted_1 = 0;
                let sum_vat_discounted_2 = 0;
                let sum_vat_null = 0;
                let sum_vat_special = 0;
                let isRefund = true;

                const order = this.currentOrder;
                order.recomputeOrderData()
                order.lines.forEach(function (line) {
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
                            // Gift cards should be ignored for the purpose of the RKSV
                            const program_type = line?.reward_id?.program_id?.program_type;
                            if (program_type !== "gift_card" && program_type !== "ewallet") {
                                sum_vat_null += lineAmount;
                            }
                            break;
                        default:
                            sum_vat_special += lineAmount;
                    }
                    if (!line.refunded_orderline_id)
                        isRefund = false
                });
                order.sum_vat_normal = sum_vat_normal;
                order.sum_vat_discounted_1 = sum_vat_discounted_1;
                order.sum_vat_discounted_2 = sum_vat_discounted_2;
                order.sum_vat_null = sum_vat_null;
                order.sum_vat_special = sum_vat_special;
                order.sum_total_rksv = sum_vat_normal + sum_vat_discounted_1 + sum_vat_discounted_2 + sum_vat_null + sum_vat_special;

                const signature = await this.pos.data.call("pos.order", "sign_order", [order.serialize(), isRefund]);


                order.certificate_serial_number = signature.certificate_serial_number
                order.prev_order_signature = signature.prev_order_signature
                order.machine_readable_code = signature.machine_readable_code
                order.order_signature = signature.order_signature
                order.encrypted_revenue = signature.encrypted_revenue
                order.registrierkasse_receipt_number = signature.registrierkasse_receipt_number
                order.date_order = signature.date_order;
            } catch (error) {
                console.error("RKSV Signing failed:", error);
            }
        }

        return super._finalizeValidation();
    }
})