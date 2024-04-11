# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import ValidationError,UserError
from odoo.tools.translate import _
# import csv, sys
PERIODO_SELECT = [(periodo, periodo) for periodo in range(1,13)]

class libro_diario_wizard(models.TransientModel):
    _name = 'libro_diario.wizard'

    diario=fields.Many2one('account.journal', string='Diario')
    fecha_inicio=fields.Date(string='Fecha inicio', default=datetime.today())
    fecha_fin=fields.Date(string='Fecha fin', default=datetime.today())
    # result_pc_html=fields.Html(string='Resultados',compute='search_pc_button')    
    
    @api.multi
    @api.onchange('fecha_inicio')
    def _onchange_date(self):
        date_fin=self.fecha_inicio
        self.update({'fecha_fin': date_fin})

    @api.multi
    def pdf_aux_pc(self):
        datas = {}
        movimientos=[]
        tot_cargo=0
        tot_abono=0
        sql_journal="""
        select  aml.id,
                aml."date" fecha_mov_det,
                aml."name" nom_movimiento_det,
                am."name" nom_movimiento,
                acc.code code_name,
				acc."name" nombre_cuenta,
                accp.code code_name_p,
				accp."name" nombre_cuenta_p,
                aml.debit cargo,
                aml.credit abono,
                aml.balance saldo
                from account_move_line aml
                inner join account_move am on am.id =aml.move_id
                inner join account_journal aj on aj.id= aml.journal_id
                inner join account_account acc on acc.id= aml.account_id
                left join account_account accp on accp.id= acc.account_presupuesto
                where aml.journal_id=%s and aml.date between '%s' and '%s' and am.state='posted' order by 3;"""
        self.env.cr.execute(sql_journal % (self.diario.id,self.fecha_inicio,self.fecha_fin))
        sql_row_journal = self.env.cr.dictfetchall()
        for it in sql_row_journal:
            movim=it['id']
            tot_cargo=tot_cargo+it['cargo']
            tot_abono=tot_abono+it['abono']
            datos = {
            'id': it['id'],
            'fecha_mov_det': it['fecha_mov_det'],
            'nom_movimiento_det': it['nom_movimiento_det'],
            'nom_movimiento': it['nom_movimiento'],
            'code_name': it['code_name'],
            'nombre_cuenta': it['nombre_cuenta'],
            'code_name_p': it['code_name_p'],
            'nombre_cuenta_p': it['nombre_cuenta_p'],
            'cargo': it['cargo'],
            'abono': it['abono'],
            'saldo': it['saldo'],
            }  
            movimientos.append(datos)
                
        fechas=datetime.today()
        # html_nom_c="""<table class="table table-bordered"><tr><td>%s</td></tr><tr><td>%s</td></tr> </table> """ % (self.cuenta_inicio.code,self.cuenta_inicio.name)
        datas['fecha_reporte'] = str(datetime.strftime(fechas,"%Y-%m-%d"))
        datas['rango']=self.fecha_inicio+' A '+self.fecha_fin
        datas['movimientos']=movimientos
        datas['tot_cargo']='{0:,.2f}'.format(float(tot_cargo))
        datas['tot_abono']='{0:,.2f}'.format(float(tot_abono))
        return self.env['report'].get_action([], 'reportes.report_libro_diario', data=datas)



    # @api.multi
    # def search_pc_button(self):
    #     server = self.env['presupuesto.config_auxiliares'].search([('status', '=', 'True')])
    #     servidor=server.server
    #     if(servidor>0):
    #         ###saldo inicial
    #         periodo = datetime.strptime(self.fecha_inicio, '%Y-%m-%d') if self.fecha_inicio else datetime.today()
    #         sql_si = """select saldo_inicial from v_balanza where periodo=%s and account_id=%s"""
    #         self.env.cr.execute(sql_si % (periodo.month,self.cuenta_inicio.id))
    #         rows_sql_si = self.env.cr.dictfetchall()
    #         tot_saldo_inicial=0
    #         for i in rows_sql_si:
    #             tot_saldo_inicial=tot_saldo_inicial+i['saldo_inicial']
    #         ###saldo inicial fin

    #         sql_all="""select distinct
    #                     aml.id,
    #                     am.id mov_id,
    #                     aml.account_id,
    #                     aml."date" fecha_mov_det,
    #                     aj."name" diario,
    #                     am."name" nom_movimiento,
    #                     aml."name" nom_movimiento_det,
    #                     aml."ref" referencia,
    #                     aml.debit cargo,
    #                     aml.credit abono,
    #                     aml.balance saldo
    #                     from account_move_line aml
    #                     inner join account_move am on am.id =aml.move_id
    #                     inner join tjacdmx_balanza_comprobacion bc on bc.account_id = aml.account_id
    #                     inner join account_journal aj on aj.id= aml.journal_id
    #                     where aml.account_id=%s and aml.date between '%s' and '%s' order by 3"""
    #         self.env.cr.execute(sql_all % (self.cuenta_inicio.id,self.fecha_inicio,self.fecha_fin))
    #         rows_sql = self.env.cr.dictfetchall()
    #         ids=[] 
    #         for i in rows_sql:
    #             movimientos = {
    #                 'mov_id': i['mov_id'],
    #                 'diario': i['diario'],
    #                 'nom_movimiento': i['nom_movimiento'],
    #                 'nom_movimiento_det': i['nom_movimiento_det'],
    #                 'referencia': i['referencia'],
    #                 'fecha_mov_det': i['fecha_mov_det'],
    #                 'cargo': i['cargo'],
    #                 'abono': i['abono'],
    #                 'saldo': i['saldo']
    #                 }
    #             ids.append(movimientos)
    #         html_items=""
    #         tot_cargo=0
    #         tot_abono=0
    #         tot_saldo=0
    #         for items in ids:
    #             mov_id=items['mov_id']
    #             diario=items['diario']
    #             nom_movimiento= items['nom_movimiento']
    #             nom_movimiento_det= items['nom_movimiento_det']
    #             referencia= items['referencia']
    #             fecha_mov_det=items['fecha_mov_det']
    #             cargo='{0:,.2f}'.format(float(items['cargo']))
    #             abono='{0:,.2f}'.format(float(items['abono']))
    #             saldo='{0:,.2f}'.format(float(items['saldo']))
    #             tot_cargo=tot_cargo+items['cargo']
    #             tot_abono=tot_abono+items['abono']
    #             tot_saldo=tot_saldo+items['saldo']
    #             html_items2="""
    #             <tr><td><p>%s</p></td> 
    #             <td><p><a target='_blank' href='%s/web#id=%s&view_type=form&model=account.move&menu_id=110&action=166'>%s</a></p></td> 
    #             <td><p>%s</p></td>
    #             <td><p>%s</p></td> 
    #             <td><p>%s</p></td> 
    #             <td><p>$%s</p></td> 
    #             <td><p>$%s</p></td>
    #             <td><p>$%s</p></td> 
    #             </tr>""" % (diario,server.server,mov_id,nom_movimiento,nom_movimiento_det,referencia,fecha_mov_det,cargo,abono,saldo)
    #             html_items+=html_items2.encode('ascii', 'ignore')
    #         html="""
    #         <div><h3>%s</h3></div>
    #             <table class="table table-striped">
    #                     <thead class="thead-dark">
    #                     <tr>
    #                     <th>Diario</th>
    #                     <th>Movimiento</th>
    #                     <th>Nombre</th>
    #                     <th>Referencia</th>
    #                     <th>Fecha</th>
    #                     <th>Cargo</th>
    #                     <th>Abono</th>
    #                     <th>Saldo</th>
    #                     </tr>
    #                     </thead>
    #                     <tr>
    #                     <th>Saldo inicial: $%s</th>
    #                     <th> </th>
    #                     <th> </th>
    #                     <th> </th>
    #                     <th>Total: </th>
    #                     <th>$%s</th>
    #                     <th>$%s</th>
    #                     <th>$%s</th>
    #                     </tr>
    #                     %s
    #             </table>""" % (self.cuenta_inicio.code+' '+self.cuenta_inicio.name,'{0:,.2f}'.format(float(tot_saldo_inicial)),'{0:,.2f}'.format(float(tot_cargo)),'{0:,.2f}'.format(float(tot_abono)),'{0:,.2f}'.format(float(tot_saldo_inicial+tot_cargo-tot_abono)),html_items)
    #         self.result_pc_html=html
    #     else:
    #         raise ValidationError("Un no se tiene configuracion de auxiliares")
