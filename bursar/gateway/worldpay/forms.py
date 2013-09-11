# -*- coding: utf-8 -*-
from bursar import fields, forms
from bursar import settings as bursar_settings

from django.utils.translation import ugettext as _

from . import PROCESSOR_KEY

CREDITCHOICES = bursar_settings.gateway(PROCESSOR_KEY).get('CREDITCHOICES', [])
accept_cards = [ct[0] for ct in CREDITCHOICES]

class PaymentForm(forms.BaseCreditCardForm):
    """ Subclass form to limit accepted cards """
    card_no = fields.CreditCardField(label=_('Card No'), accept_cards=accept_cards)
