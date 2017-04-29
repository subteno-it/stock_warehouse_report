# -*- coding: utf-8 -*-
# Copyright 2016 SYLEAM Info Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Stock Warehouse Report',
    'version': '1.0',
    'category': 'Warehouse',
    'description': """Stock Statistics per Warehouse""",
    'author': 'SYLEAM',
    'website': 'http://www.syleam.fr/',
    'depends': [
        'base',
        'stock',
    ],
    'images': [],
    'data': [
        'report/stock_move_warehouse_report_view.xml',
        'data/ir_cron_data.xml',
    ],
    'installable': True,
    'license': 'AGPL-3',
}

