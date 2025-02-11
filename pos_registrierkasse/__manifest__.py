# -*- coding: utf-8 -*-
{
    'name': "RKSV compliant Registrierkasse (POS)",

    'summary': "POS Extention to comply with Austrian Registrierkassenpflicht (RKSV)",

    'description': """
    This module implements tapmer proofness and cryptography requirements in accordance with Austrian Law.
    """,

    'author': "Vorstieg Software FlexCo",
    'website': "https://registrierkasse.vorstieg.eu",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Sales',
    'version': '0.1',
    'license': 'LGPL-3',
    'images': ['images/registrierkasse_thumbnail.png'],

    # any module necessary for this one to work correctly
    'depends': ['base', 'point_of_sale', 'l10n_at'],

    'assets': {
        'point_of_sale._assets_pos': [
            '/pos_registrierkasse/static/src/**/*',
        ],
    },
    'data': [
        'views/pos_config.xml',
        'views/point_of_sale_dashboard.xml',
    ],
}
