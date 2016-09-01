# -*- coding: utf-8 -*-
##############################################################################
#
#    stock_warehouse_report module for OpenERP, Stock Statistics per Warehouse
#    Copyright (C) 2015 SYLEAM Info Services (<http://www.Syleam.fr/>)
#              Alexandre MOREAU <alexandre.moreau@syleam.fr>
#              Sylvain Garancher <sylvain.garancher@syleam.fr>
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

from openerp import tools
from openerp import models, fields, api
from openerp.addons import decimal_precision as dp


class stock_move_warehouse_report(models.Model):
    _name = 'stock.move.warehouse.report'
    _description = 'Stock Statistics'
    _rec_name = 'date'
    _order = 'date desc'

    categ_id = fields.Many2one(comodel_name='product.category', string='Category', help='Category for this move')
    product_id = fields.Many2one(comodel_name='product.product', string='Product', help='Product move')
    total = fields.Float(digits_compute=dp.get_precision('Product Unit of Measure'), help='Stock at this date')
    product_qty = fields.Float(string='Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), help='Qty signed (+ in and - out)')
    uom_id = fields.Many2one(comodel_name='product.uom', string='Unit of measure', help='Current unit of measure')
    warehouse_id = fields.Many2one(comodel_name='stock.warehouse', string='Warehouse', help='Warehouse impact by this move')
    date = fields.Datetime(help='Date for this move')

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'stock_move_warehouse')
        tools.drop_view_if_exists(cr, 'stock_move_warehouse_view_report')
        cr.execute("""
            CREATE OR REPLACE VIEW stock_move_warehouse AS
                SELECT
                    (
                        SELECT product_template.categ_id
                        FROM product_product
                        LEFT JOIN product_template ON product_template.id = product_product.product_tmpl_id
                        WHERE product_product.id = stock_move.product_id
                    ),
                    product_id,
                    stock_move.product_uom AS uom_id,
                    date_expected AS date,
                    product_qty * -1 AS product_qty,
                    (
                        SELECT warehouse_id
                        FROM stock_location
                        WHERE stock_location.id = stock_move.location_id
                    ) AS warehouse_id,
                    stock_move.id AS stock_move_id
                    FROM stock_move
                    INNER JOIN stock_location sl ON sl.id = stock_move.location_id AND sl.warehouse_id IS NOT NULL
                    WHERE stock_move.state NOT IN ('draft', 'done', 'cancel')
                UNION
                SELECT
                    (
                        SELECT product_template.categ_id
                        FROM product_product
                        LEFT JOIN product_template ON product_template.id = product_product.product_tmpl_id
                        WHERE product_product.id = stock_move.product_id
                    ),
                    product_id,
                    stock_move.product_uom AS uom_id,
                    date_expected AS date,
                    product_qty AS product_qty,
                    (
                        SELECT warehouse_id
                        FROM stock_location
                        WHERE stock_location.id = stock_move.location_dest_id
                    ) AS warehouse_id,
                    stock_move.id AS stock_move_id
                    FROM stock_move
                    INNER JOIN stock_location sl ON sl.id = stock_move.location_dest_id AND sl.warehouse_id IS NOT NULL
                    WHERE stock_move.state NOT IN ('draft', 'done', 'cancel')
            """)
        cr.execute("""
            CREATE OR REPLACE VIEW stock_move_warehouse_view_report AS
                SELECT
                    MIN(smw.stock_move_id) AS id,
                    smw.product_id,
                    smw.categ_id,
                    smw.uom_id,
                    (
                        SELECT SUM(smw2.product_qty)
                        FROM stock_move_warehouse smw2
                        WHERE smw2.warehouse_id = smw.warehouse_id
                            AND smw2.product_id = smw.product_id
                            AND smw2.date <= smw.date
                    ) + (
                        COALESCE((
                            SELECT SUM(qty)
                            FROM stock_quant sq
                            INNER JOIN stock_location sl ON sl.id = sq.location_id AND sl.warehouse_id=smw.warehouse_id
                            WHERE (SELECT usage FROM stock_location WHERE id = sq.location_id) = 'internal'
                                AND sq.product_id = smw.product_id
                            GROUP BY product_id, sq.location_id
                        ), 0)
                    ) AS total,
                    SUM(smw.product_qty) AS product_qty,
                    smw.date,
                    smw.warehouse_id
                FROM stock_move_warehouse smw
                GROUP BY product_id, uom_id, warehouse_id, date, total, categ_id
            """)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        res = super(stock_move_warehouse_report, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

        for index in range(len(res)):
            if res[index]['__count'] > 1 and 'total' in res[index] and '__domain' in res[index]:
                res[index]['total'] = self.search(res[index]['__domain'], order='total ASC', limit=1).total

        return res

    @api.model
    def update_report(self):
        self.env.cr.execute("""
                   INSERT INTO stock_move_warehouse_report
                       (create_date,
                       create_uid,
                       categ_id,
                       product_id,
                       total,
                       product_qty,
                       uom_id,
                       warehouse_id,
                       date)
                   SELECT
                       now() AS create_date,
                       1 AS create_uid,
                       categ_id,
                       product_id,
                       total,
                       product_qty,
                       uom_id,
                       warehouse_id,
                       date
                   FROM stock_move_warehouse_view_report""")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
