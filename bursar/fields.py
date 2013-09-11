# -*- coding: utf-8 -*-
import re, datetime

from django import forms
from django.utils.translation import ugettext as _
from bursar import utils


class Html5EmailInput(forms.widgets.Input):
    input_type = 'email'


class Html5TelInput(forms.widgets.Input):
    input_type = 'tel'


class ExpirationDateWidget(forms.MultiWidget):
    def __init__(self, attrs=None):
        year = datetime.date.today().year
        widgets = (forms.Select(attrs=attrs, choices=((i,i) for i in range(1,13))),
                   forms.Select(attrs=attrs, choices=((i,i) for i in range(year, year+15))))
        super(ExpirationDateWidget, self).__init__(widgets, attrs)

    def decompress(self, value):
        if value:
            return [value.year, value.month]
        return [None, None]



class LatinCharField(forms.CharField):
    """ CharField to be validated against latin chars only """
    def validate(self, value):
        try:
            value.encode('iso-8859-1')
        except:
            raise forms.ValidationError(_("Please use English or transliteration"))
        super(LatinCharField, self).validate(value)

class ExpirationDateField(forms.DateField):
    """ field to combine two inputs to one date object"""
    widget = ExpirationDateWidget()

    def to_python(self, raw_value):
        try:
            month = int(raw_value[0])
            year = int(raw_value[1])
            date = datetime.date(year, month, 1)
        except:
            raise forms.ValidationError(_("Enter a valid date"))
        return date

    def validate(self, date):
        if date<datetime.date.today():
            raise forms.ValidationError(_("Expiration date already passed"))
        super(ExpirationDateField, self).validate(date)

class NumericField(forms.CharField):
    """ field to ignore everything except digits - dashes, spaces etc"""
    def to_python(self, raw_value):
        try:
            raw_value = re.sub('\D', '', raw_value)
        except TypeError:
            pass
        return super(NumericField, self).to_python(raw_value)

class CVCField(NumericField):
    widget = forms.TextInput(attrs={'size':4, 'maxlength':4, 'class':'numeric'})

    def validate(self, value):
        """ note that CVC length should be validated in form clear() method
            because CVC is not required for some card types """
        super(CVCField, self).validate(value)

def check_CVC(card_no, cvc):
    card_type = utils.get_cardtype(card_no)
    cvc = (cvc and unicode(cvc)) or ''
    if card_type == 'AMEX':
        if not cvc:
            return forms.Field.default_error_messages['required']
        elif len(cvc) != 4:
            return forms.Field.default_error_messages['invalid']
    elif card_type in ('VISA', 'VISA ELECTRON', 'MASTERCARD', 'DISCOVER', 'JCB'):
        if not cvc:
            return forms.Field.default_error_messages['required']
        elif len(cvc) != 3:
            return forms.Field.default_error_messages['invalid']

class CreditCardField(NumericField):
    widget = forms.TextInput(attrs={'class':'numeric', 'autocomplete':'off'})
    accept_cards = []

    def __init__(self, accept_cards=None, *args, **kwargs):
        cards_dict = dict(utils.card_types)
        self.accept_cards = cards_dict.keys()
        if accept_cards is not None:
            self.accept_cards = set(self.accept_cards).intersection(set(accept_cards))

        assert(self.accept_cards)

        super(CreditCardField, self).__init__(self, *args, **kwargs)

        self.min_num_length = reduce(lambda x, y: min(x,min(cards_dict[y][0])), self.accept_cards, 20)
        self.max_num_length = reduce(lambda x, y: max(x,max(cards_dict[y][0])), self.accept_cards, self.min_num_length)
        self.widget.attrs['maxlength'] = self.max_num_length

    def validate(self, value):
        if value: # we don't know if this field is required
            card_no = str(value)
            if len(card_no) < self.min_num_length or len(card_no) > self.max_num_length:
                raise forms.ValidationError(_("Card number should be %(min_len)s to %(max_len)s digits long")%{'min_len':self.min_num_length, 'max_len':self.max_num_length})

            if not utils.is_mod10(card_no):
                raise forms.ValidationError(_('Invalid card number'))

            card_type = utils.get_cardtype(card_no)
            if card_type not in self.accept_cards:
                raise forms.ValidationError(_("Sorry, we accept only %(supported_cards)s")%{'supported_cards': ', '.join(self.accept_cards)})

        super(CreditCardField, self).validate(value)
