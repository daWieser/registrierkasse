from odoo import models


class PosMakePayment(models.TransientModel):
    _inherit = 'pos.make.payment'

    def check(self):
        res = super().check()
        order = self.env['pos.order'].browse(self.env.context.get('active_id', False))
        if order.state in {'paid', 'done', 'invoiced'}:
            order.action_retry_signing()
        return res