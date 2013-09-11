# -*- coding: utf-8 -*-

PROCESSOR_KEY = __name__.rsplit(".", 1)[-1].upper()
DEFAULT_SETTINGS = {
    'CREDITCHOICES': (
        ('VISA', 'Visa'),
        ('MASTERCARD', 'MasterCard'),
        ('MAESTRO', 'Maestro'),
        ('SWITCH', 'Switch'),
        ('AMEX', 'American Express'),
        ('DC', 'Diners Club'),
    ),
}
