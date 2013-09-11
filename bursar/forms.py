# -*- coding: utf-8 -*-
import datetime

from . import fields, utils
from . import settings as bursar_settings

from countries import models as countries

from django import forms
from django.utils.translation import ugettext_lazy as _

class BasePaymentForm(forms.Form):
    """ All payment forms should inherit from this form """
    def inject_errors(self, error, field = None):
        """ method to inject errors into validated form if payment failed """
        if field is None:
            field = self.fields.keyOrder[0]
        self._errors.setdefault(field, self.error_class()).append(error)

class BaseCreditCardForm(BasePaymentForm):
    name    = fields.LatinCharField(label=_('Name on card'), max_length=50)
    address = fields.LatinCharField(label=_('Street address'), max_length=200)
    city    = fields.LatinCharField(label=_('City'), max_length=50)
    zip     = fields.LatinCharField(label=_('ZIP or postal code'), max_length=8)
    country = forms.ModelChoiceField(label=_('Country'), queryset=countries.Country.objects.filter(visible=True))
    phone   = fields.LatinCharField(label=_('Phone'), max_length=20, widget=fields.Html5TelInput())
    email   = forms.EmailField(widget=fields.Html5EmailInput())

    card_no = fields.CreditCardField(label=_('Card No'))
    expiry  = fields.ExpirationDateField(label=_('Expiration date'))
    cvc     = fields.CVCField(label=_('CVC/CVV2'), required=False)

    def clean(self):
        data = self.cleaned_data

        if data.get('card_no'):
            err = fields.check_CVC(data['card_no'], data.get('cvc', ''))
            if err:
                self._errors["cvc"] = self.error_class([err])

            if not data.get('card_type'):
                data['card_type'] = utils.get_cardtype(data['card_no'])

        if self._errors:
            raise forms.ValidationError('')

        return data

    def inject_errors(self, error):
        return super(BaseCreditCardForm, self).inject_errors(error, 'card_no')
