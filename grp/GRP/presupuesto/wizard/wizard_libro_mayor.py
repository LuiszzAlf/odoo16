# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.translate import _
# import csv, sys
PERIODO_SELECT = [(periodo, periodo) for periodo in range(1,13)]

def search_code(self,account_id):
    sql_code="""
            SELECT			
                c.id id_hijo,
                ac.account_padre id_padre
            FROM account_account ac
                LEFT JOIN(SELECT * FROM account_account
                ) c ON c.account_padre=ac.id
            WHERE ac.id=%s ORDER BY 1"""
    self.env.cr.execute(sql_code % (account_id))
    sql_row_code_padre = self.env.cr.dictfetchall()
    return sql_row_code_padre

def search_items(self,fecha_inicio,fecha_fin,cuenta_id,ids):
    t_saldo_inicial=0
    t_cargo=0
    t_abono=0
    t_saldo=0
    periodo = datetime.strptime(fecha_inicio, '%Y-%m-%d') if fecha_inicio else datetime.today()
    sql_all="""select distinct
                aml.id,
                aml.account_id,
                aml."date" fecha_mov_det,
                aj."name" diario,
                am."name" nom_movimiento,
                aml."name" nom_movimiento_det,
                aml."ref" referencia,
                aml.debit cargo,
                aml.credit abono,
                aml.balance saldo
                from account_move_line aml
                inner join account_move am on am.id =aml.move_id
                inner join tjacdmx_balanza_comprobacion bc on bc.account_id = aml.account_id
                inner join account_journal aj on aj.id= aml.journal_id
                where aml.account_id=%s and aml.date between '%s' and '%s' and am.state='posted' order by 3"""
    self.env.cr.execute(sql_all % (cuenta_id,fecha_inicio,fecha_fin)) 
    rows_sql = self.env.cr.dictfetchall()


    sql_si_det = """select saldo_inicial from tjacdmx_balanza_comprobacion where account_id=%s and periodo='%s';"""
    self.env.cr.execute(sql_si_det % (cuenta_id,periodo))
    rows_sql_si_det = self.env.cr.dictfetchall()

    rows_sql_si_det_validate=len(rows_sql_si_det)
    if(rows_sql_si_det_validate>0):
        rows_sql_si_det_ok=rows_sql_si_det[0]['saldo_inicial']
        print(rows_sql_si_det_ok)
    else:
        rows_sql_si_det_ok=0
    # if(rows_sql):
    #     vals_=0
    # else:
    #     t_saldo_inicial=rows_sql_si_det_ok
    
    for i in rows_sql:
        sql_si_det = """select saldo_inicial from tjacdmx_balanza_comprobacion where account_id=%s and periodo='%s';"""
        self.env.cr.execute(sql_si_det % (i['account_id'],periodo))
        rows_sql_si_det = self.env.cr.dictfetchall()
        if(rows_sql_si_det_validate>0):
            rows_sql_si_det_ok=rows_sql_si_det[0]['saldo_inicial']
        else:
            rows_sql_si_det_ok=0
        # if(rows_sql_si_det):
        t_saldo_inicial=rows_sql_si_det_ok
        t_cargo=t_cargo+i['cargo']
        t_abono=t_abono+i['abono']
        t_saldo=t_saldo+i['saldo']
        movimientos = {
            'diario': i['diario'],
            'nom_movimiento': i['nom_movimiento'],
            'nom_movimiento_det': i['nom_movimiento_det'],
            'referencia': i['referencia'],
            'fecha_mov_det': i['fecha_mov_det'],
            'cargo': i['cargo'],
            'abono': i['abono'],
            'saldo': i['saldo']
            }
        ids.append(movimientos)
    return {'t_saldo_inicial':t_saldo_inicial,'t_cargo':t_cargo,'t_abono':t_abono,'t_saldo':t_saldo}

def search_items_else(self,fecha_inicio,fecha_fin,cuenta_inicio,ids):
    tot_saldo_inicial=0
    t_saldo_inicial=0
    t_cargo=0
    t_abono=0
    t_saldo=0
    periodo = datetime.strptime(fecha_inicio, '%Y-%m-%d') if fecha_inicio else datetime.today()
    sql_si = """select saldo_inicial from tjacdmx_balanza_comprobacion where account_id=%s and periodo='%s';"""
    self.env.cr.execute(sql_si % (cuenta_inicio,periodo))
    rows_sql_si = self.env.cr.dictfetchall()  
    for i in rows_sql_si:
        tot_saldo_inicial=i['saldo_inicial']
    sql_all="""select distinct
                aml.id,
                aml.account_id,
                aml."date" fecha_mov_det,
                aj."name" diario,
                am."name" nom_movimiento,
                aml."name" nom_movimiento_det,
                aml."ref" referencia,
                aml.debit cargo,
                aml.credit abono,
                aml.balance saldo
                from account_move_line aml
                inner join account_move am on am.id =aml.move_id
                inner join tjacdmx_balanza_comprobacion bc on bc.account_id = aml.account_id
                inner join account_journal aj on aj.id= aml.journal_id
                where aml.account_id=%s and aml.date between '%s' and '%s' and am.state='posted' order by 3;"""
    self.env.cr.execute(sql_all % (cuenta_inicio,fecha_inicio,fecha_fin))
    rows_sql = self.env.cr.dictfetchall()
    for i in rows_sql:
        sql_si_det = """select saldo_inicial from tjacdmx_balanza_comprobacion where account_id=%s and periodo='%s';"""
        self.env.cr.execute(sql_si_det % (i['account_id'],periodo))
        rows_sql_si_det = self.env.cr.dictfetchall()
        if(rows_sql_si_det):
            t_saldo_inicial=rows_sql_si_det[0]['saldo_inicial']
        t_cargo=t_cargo+i['cargo']
        t_abono=t_abono+i['abono']
        t_saldo=t_saldo+i['saldo']
        movimientos = {
            'diario': i['diario'],
            'nom_movimiento': i['nom_movimiento'],
            'nom_movimiento_det': i['nom_movimiento_det'],
            'referencia': i['referencia'],
            'fecha_mov_det': i['fecha_mov_det'],
            'cargo': i['cargo'],
            'abono': i['abono'],
            'saldo': i['saldo']
            }
        ids.append(movimientos)
    
    return {'tot_saldo_inicial':tot_saldo_inicial,'t_saldo_inicial':t_saldo_inicial,'t_cargo':t_cargo,'t_abono':t_abono,'t_saldo':t_saldo}

class auxiliares_wizard(models.TransientModel):
    _name = 'libro_mayor.wizard'

    @api.model
    def get_cuenta(self):
        return self.env['account.account'].search([('code','=','100.0.0000.00')])

    cuenta_inicio = fields.Many2one('account.account', string='Cuenta inicio', default=get_cuenta)
    cuenta_fin = fields.Many2one('account.account', string='Cuenta fin')
    fecha_inicio=fields.Date(string='Fecha inicio', default=datetime.today())
    fecha_fin=fields.Date(string='Fecha fin', default=datetime.today())
    result_pc_html=fields.Html(string='Resultados',compute='search_pc_button')    
    periodo = fields.Selection(PERIODO_SELECT, default=1)
    csv_urls = fields.Char(compute='_get_csv_url')

    @api.multi
    @api.onchange('cuenta_inicio')
    def _onchange_code(self):
        cuenta_fin=self.cuenta_inicio.id
        self.update({'cuenta_fin': cuenta_fin})
    
    @api.multi
    @api.onchange('fecha_inicio')
    def _onchange_date(self):
        date_fin=self.fecha_inicio
        self.update({'fecha_fin': date_fin})

    @api.multi
    def pdf_aux_pc(self):
        datas = {}
        codes_hijo=[] 
        tot_saldo_inicial=0
        tot_cargo=0
        tot_abono=0
        tot_saldo=0
        sql_code="""
        WITH RECURSIVE account_tree AS ( 
            SELECT distinct
                    a."id" 
            FROM account_account a 
            WHERE code between '%s' and '%s'
        UNION  ALL 
            SELECT 
                    a."id"
            FROM account_account a
            JOIN account_tree b ON b.id = a.account_padre
        )
        SELECT
        a.id,
        concat(a.code,' ',a.name) code_padre
        FROM account_account a 
            JOIN account_tree b ON b."id" = a."id"
        group by a.id
        ORDER BY code"""
        self.env.cr.execute(sql_code % (self.cuenta_inicio.code,self.cuenta_fin.code))
        sql_row_code_padre = self.env.cr.dictfetchall()
        periodo = datetime.strptime(self.fecha_inicio, '%Y-%m-%d') if self.fecha_inicio else datetime.today()
        sql_si = """select saldo_inicial from v_balanza where periodo=%s and account_id=%s"""
        self.env.cr.execute(sql_si % (periodo.month,self.cuenta_inicio.id))
        rows_sql_si = self.env.cr.dictfetchall()
        # raise ValidationError("debug---%s"%rows_sql_si)
        if(rows_sql_si):
            tot_saldo_inicial=rows_sql_si[0]['saldo_inicial']
        for it in sql_row_code_padre:
            ids=[]
            tots=[]
            cuenta_id=it['id']
            t_saldo_inicial=0
            t_cargo=0
            t_abono=0
            t_saldo=0
            if(cuenta_id):
                #cuenta_id=search_code(self,code_id)
                busca_items=search_items(self,self.fecha_inicio,self.fecha_fin,cuenta_id,ids)
                t_saldo_inicial=busca_items['t_saldo_inicial']
                t_cargo=busca_items['t_cargo']
                t_abono=busca_items['t_abono']
                t_saldo=t_saldo_inicial+t_cargo-t_abono
                tot_cargo=tot_cargo+busca_items['t_cargo']
                tot_abono=tot_abono+busca_items['t_abono']
                tot_saldo=tot_saldo+busca_items['t_saldo']
            else:
                busca_items_else=search_items_else(self,self.fecha_inicio,self.fecha_fin,cuenta_id,ids)
                #tot_saldo_inicial=busca_items_else['tot_saldo_inicial']
                t_saldo_inicial=busca_items_else['t_saldo_inicial']
                t_cargo=busca_items_else['t_cargo']
                t_abono=busca_items_else['t_abono']
                t_saldo=t_saldo_inicial+t_cargo-t_abono
                tot_cargo=tot_cargo+busca_items_else['t_cargo']
                tot_abono=tot_abono+busca_items_else['t_abono']
                tot_saldo=tot_saldo+busca_items_else['t_saldo'] 
            code = {
                'id_hijo': cuenta_id,
                'code_hijo': it['code_padre'],
                'code_padre': it['code_padre'],
                't_saldo_inicial': t_saldo_inicial,
                't_debe': t_cargo,
                't_haber': t_abono,
                't_saldo': t_saldo,
                'movimientos': ids
                }
            codes_hijo.append(code)
                
        fechas=datetime.today()
        html_nom_c="""<table class="table table-bordered"><tr><td>%s</td></tr><tr><td>%s</td></tr> </table> """ % (self.cuenta_inicio.code,self.cuenta_inicio.name)
        datas['fecha_reporte'] = str(datetime.strftime(fechas,"%Y-%m-%d"))
        datas['rango']=self.fecha_inicio+' a '+self.fecha_fin
        #datas['nombre_cuenta']=html_nom_c
        datas['nombre_cuenta']=self.cuenta_inicio.code+' '+self.cuenta_inicio.name
        datas['tot_saldo_inicial']='{0:,.2f}'.format(float(tot_saldo_inicial))
        datas['tot_cargo']='{0:,.2f}'.format(float(tot_cargo))
        datas['tot_abono']='{0:,.2f}'.format(float(tot_abono))
        datas['tot_saldo']='{0:,.2f}'.format(float(tot_saldo_inicial+tot_cargo-tot_abono))
        datas['cuentas']=codes_hijo
        print(codes_hijo)
        return self.env['report'].get_action([], 'reportes.report_libro_mayor', data=datas)



    @api.multi
    def search_pc_button(self):
        server = self.env['presupuesto.config_auxiliares'].search([('status', '=', 'True')])
        servidor=server.server
        if(servidor>0):
            ###saldo inicial
            periodo = datetime.strptime(self.fecha_inicio, '%Y-%m-%d') if self.fecha_inicio else datetime.today()
            sql_si = """select saldo_inicial from v_balanza where periodo=%s and account_id=%s"""
            self.env.cr.execute(sql_si % (periodo.month,self.cuenta_inicio.id))
            rows_sql_si = self.env.cr.dictfetchall()
            # raise ValidationError("debug---%s"%rows_sql_si)
            tot_saldo_inicial=0
            for i in rows_sql_si:
                tot_saldo_inicial=tot_saldo_inicial+i['saldo_inicial']
            ###saldo inicial fin

            sql_all="""select distinct
                        aml.id,
                        am.id mov_id,
                        aml.account_id,
                        aml."date" fecha_mov_det,
                        aj."name" diario,
                        am."name" nom_movimiento,
                        aml."name" nom_movimiento_det,
                        aml."ref" referencia,
                        aml.debit cargo,
                        aml.credit abono,
                        aml.balance saldo
                        from account_move_line aml
                        inner join account_move am on am.id =aml.move_id
                        inner join tjacdmx_balanza_comprobacion bc on bc.account_id = aml.account_id
                        inner join account_journal aj on aj.id= aml.journal_id
                        where aml.account_id=%s and aml.date between '%s' and '%s' order by 3"""
            self.env.cr.execute(sql_all % (self.cuenta_inicio.id,self.fecha_inicio,self.fecha_fin))
            rows_sql = self.env.cr.dictfetchall()
            ids=[] 
            for i in rows_sql:
                movimientos = {
                    'mov_id': i['mov_id'],
                    'diario': i['diario'],
                    'nom_movimiento': i['nom_movimiento'],
                    'nom_movimiento_det': i['nom_movimiento_det'],
                    'referencia': i['referencia'],
                    'fecha_mov_det': i['fecha_mov_det'],
                    'cargo': i['cargo'],
                    'abono': i['abono'],
                    'saldo': i['saldo']
                    }
                ids.append(movimientos)
            html_items=""
            tot_cargo=0
            tot_abono=0
            tot_saldo=0
            for items in ids:
                mov_id=items['mov_id']
                diario=items['diario']
                nom_movimiento= items['nom_movimiento']
                nom_movimiento_det= items['nom_movimiento_det']
                referencia= items['referencia']
                fecha_mov_det=items['fecha_mov_det']
                cargo='{0:,.2f}'.format(float(items['cargo']))
                abono='{0:,.2f}'.format(float(items['abono']))
                saldo='{0:,.2f}'.format(float(items['saldo']))
                tot_cargo=tot_cargo+items['cargo']
                tot_abono=tot_abono+items['abono']
                tot_saldo=tot_saldo+items['saldo']
                html_items2="""
                <tr><td><p>%s</p></td> 
                <td><p><a target='_blank' href='%s/web#id=%s&view_type=form&model=account.move&menu_id=110&action=166'>%s</a></p></td> 
                <td><p>%s</p></td>
                <td><p>%s</p></td> 
                <td><p>%s</p></td> 
                <td><p>$%s</p></td> 
                <td><p>$%s</p></td>
                <td><p>$%s</p></td> 
                </tr>""" % (diario,server.server,mov_id,nom_movimiento,nom_movimiento_det,referencia,fecha_mov_det,cargo,abono,saldo)
                html_items+=html_items2.encode('ascii', 'ignore')
            html="""
            <div><h3>%s</h3></div>
                <table class="table table-striped">
                        <thead class="thead-dark">
                        <tr>
                        <th>Diario</th>
                        <th>Movimiento</th>
                        <th>Nombre</th>
                        <th>Referencia</th>
                        <th>Fecha</th>
                        <th>Cargo</th>
                        <th>Abono</th>
                        <th>Saldo</th>
                        </tr>
                        </thead>
                        <tr>
                        <th>Saldo inicial: $%s</th>
                        <th> </th>
                        <th> </th>
                        <th> </th>
                        <th>Total: </th>
                        <th>$%s</th>
                        <th>$%s</th>
                        <th>$%s</th>
                        </tr>
                        %s
                </table>""" % (self.cuenta_inicio.code+' '+self.cuenta_inicio.name,'{0:,.2f}'.format(float(tot_saldo_inicial)),'{0:,.2f}'.format(float(tot_cargo)),'{0:,.2f}'.format(float(tot_abono)),'{0:,.2f}'.format(float(tot_saldo_inicial+tot_cargo-tot_abono)),html_items)
            self.result_pc_html=html
        else:
            raise ValidationError("Un no se tiene configuracion de auxiliares")
