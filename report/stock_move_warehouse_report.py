# -*- coding: utf-8 -*-
# Copyright 2016 SYLEAM Info Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import tools
from odoo import models, fields, api
from odoo.addons import decimal_precision as dp


class stock_move_warehouse_report(models.Model):
    _name = 'stock.move.warehouse.report'
    _description = 'Stock Statistics'
    _rec_name = 'date'
    _order = 'date desc'

    categ_id = fields.Many2one(comodel_name='product.category', string='Category', help='Category for this move')
    product_id = fields.Many2one(comodel_name='product.product', string='Product', help='Product move')
    in_out_qty = fields.Float(string='Incoming - Outgoing', digits=dp.get_precision('Product Unit of Measure'))
    uom_id = fields.Many2one(comodel_name='product.uom', string='Unit of measure', help='Current unit of measure')
    warehouse_id = fields.Many2one(comodel_name='stock.warehouse', string='Warehouse', help='Warehouse impact by this move')
    date = fields.Datetime(help='Date for this move')
    qty_available = fields.Float(string='Quantity On Hand', digits=dp.get_precision('Product Unit of Measure'),
                                 help="Current quantity of products.\n"
                                 "In a context with a single Stock Location, this includes "
                                 "goods stored at this Location, or any of its children.\n"
                                 "In a context with a single Warehouse, this includes "
                                 "goods stored in the Stock Location of this Warehouse, or any "
                                 "of its children.\n"
                                 "stored in the Stock Location of the Warehouse of this Shop, "
                                 "or any of its children.\n"
                                 "Otherwise, this includes goods stored in any Stock Location "
                                 "with 'internal' type.")
    virtual_available = fields.Float(string='Forecast Quantity', digits=dp.get_precision('Product Unit of Measure'),
                                     help="Forecast quantity (computed as Quantity On Hand "
                                     "- Outgoing + Incoming)\n"
                                     "In a context with a single Stock Location, this includes "
                                     "goods stored in this location, or any of its children.\n"
                                     "In a context with a single Warehouse, this includes "
                                     "goods stored in the Stock Location of this Warehouse, or any "
                                     "of its children.\n"
                                     "Otherwise, this includes goods stored in any Stock Location "
                                     "with 'internal' type.")
    incoming_qty = fields.Float(string='Incoming', digits=dp.get_precision('Product Unit of Measure'),
                                help="Quantity of products that are planned to arrive.\n"
                                "In a context with a single Stock Location, this includes "
                                "goods arriving to this Location, or any of its children.\n"
                                "In a context with a single Warehouse, this includes "
                                "goods arriving to the Stock Location of this Warehouse, or "
                                "any of its children.\n"
                                "Otherwise, this includes goods arriving to any Stock "
                                "Location with 'internal' type.")
    outgoing_qty = fields.Float(string='Outgoing', digits=dp.get_precision('Product Unit of Measue'),
                                help="Quantity of products that are planned to leave.\n"
                                "In a context with a single Stock Location, this includes "
                                "goods leaving this Location, or any of its children.\n"
                                "In a context with a single Warehouse, this includes "
                                "goods leaving the Stock Location of this Warehouse, or "
                                "any of its children.\n"
                                "Otherwise, this includes goods leaving any Stock "
                                "Location with 'internal' type.")

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'stock_move_warehouse')
        tools.drop_view_if_exists(self.env.cr, 'stock_move_warehouse_view_report')
        self.env.cr.execute("""
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
                    0 AS incoming_qty,
                    product_qty AS outgoing_qty,
                    product_qty * -1 AS in_out_qty,
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
                    product_qty AS incoming_qty,
                    0 AS outgoing_qty,
                    product_qty AS in_out_qty,
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
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW stock_move_warehouse_view_report AS
                SELECT
                    MIN(smw.stock_move_id) AS id,
                    smw.product_id,
                    smw.categ_id,
                    smw.uom_id,
                    (
                        COALESCE((
                            SELECT SUM(qty)
                            FROM stock_quant sq
                            INNER JOIN stock_location sl ON sl.id = sq.location_id AND sl.warehouse_id=smw.warehouse_id
                            WHERE (SELECT usage FROM stock_location WHERE id = sq.location_id) = 'internal'
                                AND sq.product_id = smw.product_id
                            GROUP BY product_id, sq.location_id
                        ), 0)
                    ) AS qty_available,
                    (
                        SELECT SUM(smw2.in_out_qty)
                        FROM stock_move_warehouse smw2
                        WHERE smw2.warehouse_id = smw.warehouse_id
                            AND smw2.product_id = smw.product_id
                    ) + (
                        COALESCE((
                            SELECT SUM(qty)
                            FROM stock_quant sq
                            INNER JOIN stock_location sl ON sl.id = sq.location_id AND sl.warehouse_id=smw.warehouse_id
                            WHERE (SELECT usage FROM stock_location WHERE id = sq.location_id) = 'internal'
                                AND sq.product_id = smw.product_id
                            GROUP BY product_id, sq.location_id
                        ), 0)
                    ) AS virtual_available,
                    SUM(smw.incoming_qty) AS incoming_qty,
                    SUM(smw.outgoing_qty) AS outgoing_qty,
                    SUM(smw.in_out_qty) AS in_out_qty,
                    smw.date,
                    smw.warehouse_id
                FROM stock_move_warehouse smw
                GROUP BY product_id, uom_id, warehouse_id, date, virtual_available, qty_available, categ_id
            """)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        res = super(stock_move_warehouse_report, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

        for index in range(len(res)):
            if res[index]['__count'] > 1 and 'qty_available' in res[index] and '__domain' in res[index]:
                res[index]['qty_available'] = self.search(res[index]['__domain'], order='qty_available ASC', limit=1).qty_available
            if res[index]['__count'] > 1 and 'virtual_available' in res[index] and '__domain' in res[index]:
                res[index]['virtual_available'] = self.search(res[index]['__domain'], order='virtual_available ASC', limit=1).virtual_available

        return res

    @api.model
    def update_report(self):
        self.env.cr.execute("""TRUNCATE TABLE stock_move_warehouse_report""")
        self.env.cr.execute("""
                   INSERT INTO stock_move_warehouse_report
                       (create_date,
                       create_uid,
                       categ_id,
                       product_id,
                       qty_available,
                       virtual_available,
                       incoming_qty,
                       outgoing_qty,
                       in_out_qty,
                       uom_id,
                       warehouse_id,
                       date)
                   SELECT
                       now() AS create_date,
                       1 AS create_uid,
                       categ_id,
                       product_id,
                       qty_available,
                       virtual_available,
                       incoming_qty,
                       outgoing_qty,
                       in_out_qty,
                       uom_id,
                       warehouse_id,
                       date
                   FROM stock_move_warehouse_view_report""")

