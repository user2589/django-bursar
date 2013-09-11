# -*- coding: utf-8 -*-
from bursar import models as bursar_models
from bursar.gateway import base

from . import PROCESSOR_KEY

class PaymentProcessor(base.BasePaymentProcessor):
    """ This is a dummy processor always returning success """
    key = PROCESSOR_KEY
    can_authorize = True

    def authorize(self, form_data):
        self.log.debug('Authorize request: %s', form_data)

        bursar_models.CreditCardDetail(
                payment= self.payment,
                ccv    = form_data['cvc'],
                card_no= form_data['card_no'],
                expiry = form_data['expiry'],
                name   = form_data['name']
            ).save()

        return {
            'status' : 'A',
            'amount' : self.payment.amount
        }

    def capture(self, form_data):
        result = authorize(form_data)
        result['status'] = 'CD'
        return result

    def capture_authorized(self, amount):
        self.log.debug('Capture authorized request: %s, %s', self.payment, amount)
        return {
            'status' : 'CD',
            'amount' : amount,
        }

    def release_authorized(self):
        self.log.debug('Release authorized request: %s', self.payment)
        return { 'status' : 'C' }

    def refund(self, amount):
        assert(amount <= self.payment.amount)
        self.log.debug('Refund request: %s, %s', self.payment, amount)

        new_amount = self.payment.amount - amount
        return {
            'amount' : new_amount,
            'status' : self.payment.status if new_amount > 0 else 'RF'
        }

    def get_payment_status(self):
        return {}
