# -*- coding: UTF-8 -*-
"""Bursar Autosucess Gateway Tests."""
from bursar.gateway.autosuccess import processor
from bursar.tests import make_test_purchase
from decimal import Decimal
from django.conf import settings
from django.test import TestCase
from django.test.client import Client

class TestGateway(TestCase):
    def setUp(self):
        self.client = Client()
        self.gateway = processor.PaymentProcessor()

    def tearDown(self):
        pass

    def test_capture(self):
        """Test making a direct payment using AUTOSUCCESS."""
        purchase = make_test_purchase(sub_total=Decimal('10.00'))
        self.assertEqual(purchase.total, Decimal('10.00'))
        result = self.gateway.capture_payment(purchase=purchase)
        self.assert_(result.success)
        payment = result.payment
        self.assertEqual(payment.amount, Decimal('10.00'))
        self.assertEqual(purchase.total_payments, Decimal('10.00'))
        self.assertEqual(purchase.authorized_remaining, Decimal('0.00'))
