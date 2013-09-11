# -*- coding: utf-8 -*-
import sys, re

from django.conf import settings
from django import forms
from django.utils import importlib

from bursar import settings as bursar_settings

card_types = (
    # ('<type>', (<tuple of possible num length>, 'regexp to match beginning')),
    ('VISA ELECTRON' , ((16,), '4(026|17500|508|844|913|917)')),
    ('VISA'          , ((16,), '4')), #old issues had 13 digits but now all migrated to 16
    ('SWITCH'        , ((16,18,19), '(4903|4905|4911|4936|564182|633110|6333|6759)')),
    ('AMEX'          , ((15,), '3[4-7]')),
    ('MASTERCARD'    , ((16,), '5[1-5]')),
    ('UNIONPAY'      , ((16,17,18,19), '62([4-6]|2[126-925]|8[2-8])')),  #622126-622925 are served by Discover internationally
    ('DISCOVER'      , ((16,), '6(5|4[4-9]|011|2[126-925])')),
    ('JCB'           , ((16,), '35[28-89]')),                            # served by Discover internationally
    ('SWITCH'        , ((16,17,18,19), '(4903|4905|4911|4936|564182|633110|6333|6759)')), #now branded as Maestro
    ('MAESTRO'       , ((12,13,14,15,16,17,18,19), '(5018|5020|5038|6304|6759|6761|6763)')),
    ('DC'            , ((14,), '(30[0-5]|36|38)')),         #new diners club are 16 digits long and served by MC
)

def get_cardtype(card_num):
    """ Identifies the credit card type """
    card_no = str(card_num)
    card_len= len(card_no)

    for type, (lens, pattern) in card_types:
        if card_len in lens and re.match(pattern, card_no):
            return type

def is_mod10(cc):
    """ Check if credit card number passes mod10 validation """
    total = 0
    for i, d in enumerate(map(int, cc[::-1])):
        total += d if i % 2 == 0 else (2*d if d <= 4 else 2*d - 9)
    return (total % 10) == 0

def get_processor(gateway):
    """ Accepts module name eg 'worldpay' or bursar.gateway.worldpay
        Returns PaymentProcessor instance """
    appname = dict(bursar_settings.ACTIVE_GATEWAYS).get(gateway) or gateway
    payment_processor_module = importlib.import_module(appname + ".processor") #might throw ImportError
    return payment_processor_module.PaymentProcessor

def get_form(gateway):
    """ Accepts module name eg 'worldpay' or bursar.gateway.worldpay
        Returns gateway specific PaymentForm instance """
    appname = dict(bursar_settings.ACTIVE_GATEWAYS).get(gateway) or gateway
    try:
        payment_form_module = importlib.import_module(appname + ".forms")
    except ImportError: #some processors don't provide form
        return None
    return payment_form_module.PaymentForm
