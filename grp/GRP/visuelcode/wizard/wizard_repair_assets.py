# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.translate import _
import collections
import xlwt 
import base64 
import pandas as pd
from StringIO import StringIO
from dateutil.relativedelta import relativedelta

class ReportErrorr(models.TransientModel):
    _name = 'repair_error_asset.wizard'


    @api.multi
    def remove_acm(self):
        obj_asset = self.env['tjacdmx.repair_asset']
        assets_log = obj_asset.search([])
        for asst in assets_log:
            self.env.cr.execute("UPDATE account_asset_depreciation_line SET move_id=null, move_check='false',move_posted_check='false'  WHERE  asset_id='%s' and name='%s' and sequence='%s' and move_check='%s' and depreciation_date='%s' and amount='%s' and move_posted_check='%s' and move_id='%s' and depreciated_value='%s' and category_asset='%s'" % (asst['asset_id'],asst['name'],asst['sequence'],asst['move_check'],asst['depreciation_date'],asst['amount'],asst['move_posted_check'],asst['move_id'],asst['depreciated_value'],asst['category_asset']))
            # asset={
            #         'asset_id': asst['asset_id'],
            #         'name': asst['name'],
            #         'sequence': asst['sequence'],
            #         'move_check': asst['move_check'],
            #         'depreciation_date': asst['depreciation_date'],
            #         'amount': asst['amount'],
            #         'move_posted_check': asst['move_posted_check'],
            #         'remaining_value': asst['remaining_value'],
            #         'move_id': asst['move_id'],
            #         'depreciated_value': asst['depreciated_value'],
            #         'category_asset': asst['category_asset'],
            #     }
        print (assets_log)

    @api.multi
    def actializa_asset_draft(self):
        obj_asset = self.env['tjacdmx.repair_asset']
        assets_log = obj_asset.search([])
        for asst in assets_log:
            self.env.cr.execute("UPDATE account_asset_asset SET state='draft' WHERE  id='%s';" % (asst['asset_id']))
        print (assets_log)


    @api.multi
    def actializa_asset_open(self):
        obj_asset = self.env['tjacdmx.repair_asset']
        assets_log = obj_asset.search([])
        for asst in assets_log:
            self.env.cr.execute("UPDATE account_asset_asset SET state='open' WHERE  id='%s';" % (asst['asset_id']))
        print (assets_log)

    @api.multi
    def actializa_asset_back_to_move_id(self):
        obj_asset = self.env['tjacdmx.repair_asset']
        assets_log = obj_asset.search([])
        for asst in assets_log:
            self.env.cr.execute("UPDATE account_asset_depreciation_line SET move_id=%s, move_check=true, move_posted_check=true  WHERE  asset_id='%s' and name='%s' and sequence='%s' and move_check='false' and depreciation_date='%s' and amount='%s' and move_posted_check='false' and depreciated_value='%s' and category_asset='%s'" % (asst['move_id'],asst['asset_id'],asst['name'],asst['sequence'],asst['depreciation_date'],asst['amount'],asst['depreciated_value'],asst['category_asset']))
            self.env.cr.execute("UPDATE account_asset_depreciation_line SET move_id=%s, move_check=true, move_posted_check=true  WHERE  asset_id='%s' and name='%s' and sequence='%s' and move_check='false' and depreciation_date='%s' and amount='%s' and move_posted_check='false' and depreciated_value='%s' and category_asset='%s'" % (asst['move_id'],asst['asset_id'],asst['name'],asst['sequence'],asst['depreciation_date'],asst['amount'],asst['depreciated_value'],asst['category_asset']))
            self.env.cr.execute("DELETE FROM tjacdmx_repair_asset WHERE id=%s;" % (asst['id']))
        print (assets_log)
        

