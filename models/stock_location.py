# -*- coding: utf-8 -*-
# Copyright 2016 SYLEAM Info Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api, fields


class StockLocation(models.Model):
    _inherit = 'stock.location'

    warehouse_id = fields.Many2one(comodel_name='stock.warehouse', string='Warehouse', store=True, compute='_compute_warehouse_id', help='Warehouse where this location is located.')
    warehouse_ids = fields.One2many(comodel_name='stock.warehouse', inverse_name='lot_stock_id', string='Warehouses')

    @api.multi
    @api.depends('location_id', 'warehouse_ids', 'location_id.warehouse_id')
    def _compute_warehouse_id(self):
        StockWarehouse = self.env['stock.warehouse']
        for location in self:
            parent_location = location
            warehouses = []
            while parent_location.location_id:
                warehouses = StockWarehouse.search([
                    ('lot_stock_id', '=', parent_location.id),
                ], limit=1)
                if warehouses:
                    break
                parent_location = parent_location.location_id
            location.warehouse_id = warehouses and warehouses[0].id or False

