/** @odoo-module **/


import {PaymentScreen} from "@point_of_sale/app/screens/payment_screen/payment_screen";
import {patch} from '@web/core/utils/patch';


patch(PaymentScreen.prototype, {
    async _finalizeValidation() {
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

        console.log(signature)

        return super._finalizeValidation();
    }
})