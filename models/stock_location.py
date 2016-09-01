# -*- coding: utf-8 -*-
##############################################################################
#
#    stock_warehouse_report module for OpenERP, Stock Statistics per Warehouse
#    Copyright (C) 2016 SYLEAM Info Services (<http://www.syleam.fr>)
#              Sebastien LANGE <sebastien.lange@syleam.fr>
#
#    This file is a part of stock_warehouse_report
#
#    stock_warehouse_report is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    stock_warehouse_report is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, api, fields


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


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
