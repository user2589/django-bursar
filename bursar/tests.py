# -*- coding: UTF-8 -*-
import random
from django.test import TestCase
from django.conf import settings

from django import forms

from bursar import settings as bursar_settings
from bursar import utils, fields
from bursar.gateway import base

def make_test_purchase(price):
    raise NotImplementedError("""
You should define MAKE_TEST_PURCHASE in bursar settings, eg:
    BURSAR_SETTINGS = {
        ...
        'MAKE_TEST_PURCHASE': 'my_module.tests.make_test_order',
        ...
    } """)

if bursar_settings.working_settings.get('MAKE_TEST_PURCHASE'):
    from django.utils.importlib import import_module
    module_name, func_name = bursar_settings.working_settings['MAKE_TEST_PURCHASE'].rsplit('.', 1)
    try:
        _module = import_module(module_name)
    except ImportError:
        pass
    else:
        make_test_purchase = getattr(_module, func_name, make_test_purchase)


class TestBase(TestCase):
    def tearUp(self):
        pass

    def tearDown(self):
        pass

    def test_settings(self):
        self.assertTrue(bursar_settings.ACTIVE_GATEWAYS)

    def test_utils(self):
        self.assertTrue(utils.card_types)

        self.assertIsNone(utils.get_cardtype('42'))
        self.assertEqual('VISA', utils.get_cardtype('4444333322221111'))
        self.assertEqual('VISA', utils.get_cardtype('4111111111111111'))
        self.assertEqual('MASTERCARD', utils.get_cardtype('5555555555554444'))
        self.assertEqual('MASTERCARD', utils.get_cardtype('5454545454545454'))
        self.assertEqual('SWITCH', utils.get_cardtype('6333333333333333336'))
        self.assertEqual('AMEX', utils.get_cardtype('343434343434343'))
        self.assertEqual('DC', utils.get_cardtype('36700102000000'))
        self.assertEqual('MAESTRO', utils.get_cardtype('6304900017740292441'))
        self.assertEqual('UNIONPAY', utils.get_cardtype('6225880120625588'))
        self.assertEqual('UNIONPAY', utils.get_cardtype('6222000200116010778'))

        gateway = bursar_settings.ACTIVE_GATEWAYS[0][0]
        self.assertIsInstance(utils.get_processor(gateway)(None), base.BasePaymentProcessor)
        self.assertIsInstance(utils.get_form(gateway)(), forms.Form)

    def test_fields(self):
        #Incorrect code length - VISA
        self.assertIsNotNone(fields.check_CVC('4444333322221111', ''))
        self.assertIsNotNone(fields.check_CVC('4444333322221111', '1'))
        self.assertIsNotNone(fields.check_CVC('4444333322221111', '12'))
        self.assertIsNotNone(fields.check_CVC('4444333322221111', '1234'))

        #Incorrect code length - AMEX
        self.assertIsNotNone(fields.check_CVC('343434343434343', ''))
        self.assertIsNotNone(fields.check_CVC('343434343434343', '1'))
        self.assertIsNotNone(fields.check_CVC('343434343434343', '12'))
        self.assertIsNotNone(fields.check_CVC('343434343434343', '123'))

        #Correct code length
        self.assertIsNone(fields.check_CVC('4444333322221111', '123'))
        self.assertIsNone(fields.check_CVC('5555555555554444', '123'))
        self.assertIsNone(fields.check_CVC('343434343434343', '1234'))

        #Diners Club - doesn't have CVC
        self.assertIsNone(fields.check_CVC('36700102000000', ''))
        self.assertIsNone(fields.check_CVC('36700102000000', '1'))
        self.assertIsNone(fields.check_CVC('36700102000000', '123'))
        self.assertIsNone(fields.check_CVC('36700102000000', '1234'))

        cc_field = fields.CreditCardField()
        self.assertRaises(forms.ValidationError, cc_field.validate, '42') #too short value


