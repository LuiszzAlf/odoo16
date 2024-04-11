# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
import calendar
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import dateutil.relativedelta
from calendar import monthrange

from odoo.exceptions import ValidationError,UserError
import logging
_logger = logging.getLogger(__name__)



class AssetDepreciationConfirmationWizard(models.TransientModel):
    _name = "asset.depreciation.confirmation.wizard"
    _description = "asset.depreciation.confirmation.wizard"

    date = fields.Date('Account Date', required=True, help="Choose the period for which you want to automatically post the depreciation lines of running assets", default=fields.Date.context_today)

    
    def asset_compute(self):
        self.ensure_one()
        context = self._context
        created_move_ids = self.env['account.asset.asset'].compute_generated_entries(self.date, asset_type=context.get('asset_type'))

        return {
            'name': _('Created Asset Moves') if context.get('asset_type') == 'purchase' else _('Created Revenue Moves'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'view_id': False,
            'domain': "[('id','in',[" + ','.join(map(str, created_move_ids)) + "])]",
            'type': 'ir.actions.act_window',
        }




class administracionActivos(models.TransientModel):
    _inherit = "asset.depreciation.confirmation.wizard"

    mes = fields.Selection( 
        [(str(1),'Enero'),
        (str(2),'Febrero'),
        (str(3),'Marzo'),
        (str(4),'Abril'),
        (str(5),'Mayo'),
        (str(6),'Junio'),
        (str(7),'Julio'),
        (str(8),'Agosto'),
        (str(9),'Septiembre'),
        (str(10),'Octubre'),
        (str(11),'Noviembre'),
        (str(12),'Diciembre')], required=True, help="Mes")

    anio = fields.Selection([            
            (str(2019), '2019'),
            (str(2020), '2020'),
            (str(2021), '2021'),
            (str(2022), '2022'),
            (str(2023), '2023'),
            (str(2024), '2024'),
            (str(2025), '2025'),
            (str(2026), '2026'),
            (str(2027), '2027'),            
        ], required=True, help="Año")    

    
    def asset_compute(self):
        self.ensure_one()
        context = self._context

        query = """
                SELECT
                    * 
                FROM
                    (
                SELECT A
                    .ID,
                    A.method_number :: INT,
                    b.total_depreciadas :: INT,
                    ( CASE WHEN ( A.method_number = b.total_depreciadas ) THEN 0 ELSE 1 END ) estan_mal 
                FROM
                    account_asset_asset
                    A LEFT JOIN ( SELECT "count" ( * ) total_depreciadas, asset_id FROM account_asset_depreciation_line GROUP BY asset_id ORDER BY asset_id ) b ON A.ID = b.asset_id 
                    ) A 
                WHERE
                    estan_mal = 1 
                ORDER BY
                ID;
        """

        self.env.cr.execute(query)
        response = self.env.cr.dictfetchall()        

        days = monthrange(self.anio, self.mes)[1]        

        if len(response) == 0:    
            date_min = '%s-%s-%s' % (self.anio, self.mes, '01')
            date_max = '%s-%s-%s' % (self.anio, self.mes, days)
            _logger.debug(date_min)
            _logger.debug(date_max)
            lines_depreciation =  self.env['account.asset.depreciation.line'].search([
                ('depreciation_date', '<=', date_max), ('depreciation_date', '>=', date_min),
                ('move_check', '=', False)])

            created_move_ids = lines_depreciation.compute_generated_entries_range(date_min,
                date_max,
                asset_type=context.get('asset_type')
            )

            return {
                'name': _('Created Asset Moves') if context.get('asset_type') == 'purchase' else _('Created Revenue Moves'),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.move',
                'view_id': False,
                'domain': "[('id','in',[" + ','.join(map(str, created_move_ids)) + "])]",
                'type': 'ir.actions.act_window',
                'flags': {'action_buttons': False},
            }      

        if len(response) > 0:
            lista = [d['id'] for d in response]
            line_depre=[]
            obj_asset = self.env['tjacdmx.repair_asset']
            for asst in response:
                sql="""select * from account_asset_depreciation_line where move_id>0  
                and move_check=true and move_posted_check and asset_id=%s;"""
                self.env.cr.execute(sql % (asst['id']))
                rows = self.env.cr.dictfetchall()
                for it in rows:
                    asset=obj_asset.create({
                            'asset_id': it['asset_id'],
                            'name': it['name'],
                            'sequence': it['sequence'],
                            'move_check': it['move_check'],
                            'depreciation_date': it['depreciation_date'],
                            'amount': it['amount'],
                            'move_posted_check': it['move_posted_check'],
                            'remaining_value': it['remaining_value'],
                            'move_id': it['move_id'],
                            'depreciated_value': it['depreciated_value'],
                            'category_asset': it['category_asset'],
                        })
                    print (asset)
                    
            return {
                'name': _('Error!!!  Favor de corregir los errores encontrados e intente de nuevo este proceso'),

                'view_mode': 'tree',

                'view_id': self.env.ref('account_asset_update.view_tjacdmx_repair_asset_tree').id,
                'res_model': 'tjacdmx.repair_asset',
                'context': "",
                'type': 'ir.actions.act_window',

                'flags': {'action_buttons': True},
            }

            raise ValidationError("Ocurrió un error, favor de checar los siguientes activos: \n %s" % response)
            return False              
