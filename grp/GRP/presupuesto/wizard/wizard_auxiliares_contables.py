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

PERIODO_SELECT = [(periodo, periodo) for periodo in range(1,13)]
TYPE_SUM = [('none','Selecciona'),('capitulo','Capitulo'),('partida','Partida'),('indice','Indice')]

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

def search_items(self,periodo,anio,fecha_fin,cuenta_id,ids):
    t_saldo_inicial=0
    t_cargo=0
    t_abono=0
    t_saldo=0
    fecha_inicio=periodo
    anio_get=anio
    sql_all="""select
                    vmc.id,
                    vmc.account_id,
                    vmc.fecha_mov_det,
                    vmc.diario,
                    vmc.nom_movimiento,
                    vmc.nom_movimiento_det,
                    vmc.referencia,
                    COALESCE(vb.saldo_inicial, 0) saldo_inicial,
                    vmc.cargo,
                    vmc.abono,
                    vmc.saldo
                from
                    v_movimientos_cuenta vmc
                    LEFT JOIN v_balanza vb on vb.account_id = vmc.account_id 
                    and vb.periodo_fecha = vmc.fecha_mov_det
                where
                    fecha_mov_det between '%s'
                    and '%s'
                    and vmc.account_id = %s
                order by
                    nom_movimiento;"""
    self.env.cr.execute(sql_all % (fecha_inicio,fecha_fin,cuenta_id)) 
    rows_sql = self.env.cr.dictfetchall()
    sql_si_det = """select saldo_inicial from v_balanza where periodo=%s and account_id=%s and anio='%s'"""
    self.env.cr.execute(sql_si_det % (fecha_inicio.month,cuenta_id,anio_get))
    rows_sql_si_det = self.env.cr.dictfetchall()
    si_acc=rows_sql_si_det[0]['saldo_inicial'] if rows_sql_si_det else 0
    cargo_acc=rows_sql[0]['cargo'] if rows_sql else 0
    abono_acc=rows_sql[0]['abono'] if rows_sql else 0
    t_saldo_inicial=si_acc
    si=0
    if (abs(si_acc)>0):
        si=float(abs(si_acc))
        s_c=float(si_acc)+float(cargo_acc)-float(abono_acc) 
    else:
        si=0
        s_c=0
    saldo_compute=0
    ciclo=0
    for i in rows_sql:
        saldo_inicial=float(saldo_compute)
        if (si>0 and ciclo==0):
            saldo_compute=s_c
            saldo_inicial=float(i['saldo_inicial'])
        else:
            saldo_compute=float(saldo_compute)+float(i['cargo'])-float(i['abono'])
        ciclo=ciclo+1
        t_saldo_inicial=si_acc
        t_cargo=t_cargo+i['cargo']
        t_abono=t_abono+i['abono']
        t_saldo=t_saldo+i['saldo']
        no_clc=i['referencia'] if i['referencia'] else '         '
        movimientos = {
            'diario': i['diario'],
            'nom_movimiento': i['nom_movimiento'],
            'nom_movimiento_det': i['nom_movimiento_det'],
            'referencia': i['referencia'],
            'no_clc': no_clc[:8],
            'fecha_mov_det': i['fecha_mov_det'],
            'saldo_inicial': saldo_inicial,
            'cargo': i['cargo'],
            'abono': i['abono'],
            'saldo': saldo_compute
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
    sql_si = """select saldo_inicial from v_balanza where periodo=%s and account_id=%s and anio='%s'"""
    self.env.cr.execute(sql_si % (periodo.month,cuenta_inicio,periodo.year))
    rows_sql_si = self.env.cr.dictfetchall()  
    sql_all="""select
                    vmc.id,
                    vmc.account_id,
                    vmc.fecha_mov_det,
                    vmc.diario,
                    vmc.nom_movimiento,
                    vmc.nom_movimiento_det,
                    vmc.referencia,
                    COALESCE(vb.saldo_inicial, 0) saldo_inicial,
                    vmc.cargo,
                    vmc.abono,
                    vmc.saldo
                from
                    v_movimientos_cuenta vmc
                    LEFT JOIN v_balanza vb on vb.account_id = vmc.account_id 
                    and vb.periodo_fecha = vmc.fecha_mov_det
                where
                    fecha_mov_det between '%s'
                    and '%s'
                    and vmc.account_id = %s
                order by
                    nom_movimiento;"""
    self.env.cr.execute(sql_all % (fecha_inicio,fecha_fin,cuenta_inicio)) 
    rows_sql = self.env.cr.dictfetchall()
    for i in rows_sql:
        t_cargo=t_cargo+i['cargo']
        t_abono=t_abono+i['abono']
        t_saldo=t_saldo+i['saldo']
        no_clc=i['referencia'] if i['referencia'] else '         '
        movimientos = {
            'diario': i['diario'],
            'nom_movimiento': i['nom_movimiento'],
            'nom_movimiento_det': i['nom_movimiento_det'],
            'referencia': i['referencia'],
            'no_clc': no_clc[:8],
            'fecha_mov_det': i['fecha_mov_det'],
            'cargo': i['cargo'],
            'abono': i['abono'],
            'saldo': i['saldo']
            }
        ids.append(movimientos)
    return {'tot_saldo_inicial':tot_saldo_inicial,'t_saldo_inicial':t_saldo_inicial,'t_cargo':t_cargo,'t_abono':t_abono,'t_saldo':t_saldo}

class axuliares_contables_wizard(models.TransientModel):
    _name = 'axuliares_contables.wizard'

    @api.model
    def get_cuenta(self):
        return self.env['account.account'].search([('code','=','100.0.0000.00')])

    cuenta_inicio = fields.Many2one('account.account', string='Cuenta inicio', default=get_cuenta)
    cuenta_fin = fields.Many2one('account.account', string='Cuenta fin')
    fecha_inicio=fields.Date(string='Fecha inicio', default=datetime.today())
    fecha_fin=fields.Date(string='Fecha fin', default=datetime.today())
    result_pc_html=fields.Html(string='Resultados',compute='search_pc_button')    
    periodo = fields.Selection(PERIODO_SELECT, default=1)
    type_sum = fields.Selection(TYPE_SUM, default='none')
    csv_urls = fields.Char(compute='search_pc_button')

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
        sql_code="""WITH RECURSIVE account_tree AS ( 
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
        sql_si = """select saldo_inicial from v_balanza where periodo=%s and account_id=%s and anio='%s'"""
        self.env.cr.execute(sql_si % (periodo.month,self.cuenta_inicio.id,periodo.year))
        rows_sql_si = self.env.cr.dictfetchall()
        if(rows_sql_si):
            tot_saldo_inicial=rows_sql_si[0]['saldo_inicial']
        elif (rows_sql_si and self.type_sum=='capitulo'):
            code_split=self.cuenta_inicio.code.split('.', 1)
            sql_capitulo="""select sum(saldo_inicial) saldo_inicial from v_balanza where periodo=%s
                            and split_part(code::TEXT,'.', 1)='%s'
                            and split_part(code::TEXT,'.', 3)='0000'
                            and split_part(code::TEXT,'.', 4)='00';"""
            self.env.cr.execute(sql_capitulo % (periodo.month,code_split[0]))
            rows_sql_sic = self.env.cr.dictfetchall()
            tot_saldo_inicial=rows_sql_sic[0]['saldo_inicial']
        for it in sql_row_code_padre:
            ids=[]
            tots=[]
            cuenta_id=it['id']
            t_saldo_inicial=0
            t_cargo=0
            t_abono=0
            t_saldo=0
            if(cuenta_id):
                busca_items=search_items(self,periodo,periodo.year,self.fecha_fin,cuenta_id,ids)
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
        return self.env['report'].get_action([], 'reportes.report_movimientos_pc', data=datas)


    @api.multi
    def search_pc_button(self):
        codes_hijo=[] 
        tot_saldo_inicial=0
        tot_cargo=0
        tot_abono=0
        tot_saldo=0
        sql_code="""WITH RECURSIVE account_tree AS ( 
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
        sql_si = """select saldo_inicial from v_balanza where periodo=%s and account_id=%s and anio='%s'"""
        self.env.cr.execute(sql_si % (periodo.month,self.cuenta_inicio.id,periodo.year))
        rows_sql_si = self.env.cr.dictfetchall()
        html_items_code=""
        if(rows_sql_si and self.type_sum=='none'):
            tot_saldo_inicial=rows_sql_si[0]['saldo_inicial']
        elif (rows_sql_si and self.type_sum=='capitulo'):
            code_split=self.cuenta_inicio.code.split('.', 1)
            sql_capitulo="""select sum(saldo_inicial) saldo_inicial from v_balanza where periodo=%s
                            and split_part(code::TEXT,'.', 1)='%s'
                            and split_part(code::TEXT,'.', 3)='0000'
                            and split_part(code::TEXT,'.', 4)='00';"""
            self.env.cr.execute(sql_capitulo % (periodo.month,code_split[0]))
            rows_sql_sic = self.env.cr.dictfetchall()
            tot_saldo_inicial=rows_sql_sic[0]['saldo_inicial']
        for it in sql_row_code_padre:
            html_items_mov=""
            ids=[]
            tots=[]
            cuenta_id=it['id']
            t_saldo_inicial=0
            t_cargo=0
            t_abono=0
            t_saldo=0
            if(cuenta_id):
                busca_items=search_items(self,periodo,periodo.year,self.fecha_fin,cuenta_id,ids)
                t_saldo_inicial=busca_items['t_saldo_inicial']
                t_cargo=busca_items['t_cargo']
                t_abono=busca_items['t_abono']
                t_saldo=t_saldo_inicial+t_cargo-t_abono
                tot_cargo=tot_cargo+busca_items['t_cargo']
                tot_abono=tot_abono+busca_items['t_abono']
                tot_saldo=tot_saldo+busca_items['t_saldo']
            else:
                busca_items_else=search_items_else(self,self.fecha_inicio,self.fecha_fin,cuenta_id,ids)
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
            if(ids):
                for i in ids:
                    diario=i['diario']
                    nom_movimiento=i['nom_movimiento']
                    fecha_mov_det=i['fecha_mov_det']
                    saldo_inicial='{0:,.2f}'.format(float(i['saldo_inicial']))
                    cargo='{0:,.2f}'.format(float(i['cargo']))
                    abono='{0:,.2f}'.format(float(i['abono']))
                    saldo='{0:,.2f}'.format(float(i['saldo']))

                    html_items_mov2="""
                    <tr><td><p>%s</p></td> 
                    <td><p>%s</p></td>
                    <td><p>%s</p></td> 
                    <td><p>$%s</p></td> 
                    <td><p>$%s</p></td> 
                    <td><p>$%s</p></td> 
                    <td><p>$%s</p></td> 
                    </tr>
                    """ % (diario,nom_movimiento,fecha_mov_det,saldo_inicial,cargo,abono,saldo)
                    html_items_mov+=html_items_mov2.encode('ascii', 'ignore')
            else:
                html_items_mov1="""
                    <tr>
                     <th style="text-align:center; color: red; font-size: 9px;"  colspan="6"><p>Sin Movimientos</p></th>
                    </tr>
                    """
                html_items_mov+=html_items_mov1.encode('ascii', 'ignore')
            codes_hijo.append(code)
            cuenta=it['code_padre']
            saldo_inicial='{0:,.2f}'.format(float(t_saldo_inicial))
            debe='{0:,.2f}'.format(float(t_cargo))
            haber='{0:,.2f}'.format(float(t_abono))
            saldo='{0:,.2f}'.format(float(t_saldo))
            html_items_code2="""
                                <table style="border:solid 2px; border-color:#5f5e97" class="table">
                                <thead  class="thead-dark">
                                            <tr style="color: #5f5e97">
                                            <th scope="col"><h4>Cuenta<h4></th>
                                            <th scope="col"><h4>Saldo inicial<h4></th>
                                            <th scope="col">    </th>
                                            <th scope="col"><h4>Debe<h4></th>
                                            <th scope="col"><h4>Haber<h4></th>
                                            <th scope="col"><h4>Saldo<h4></th>
                                            <th scope="col"><h4><h4></th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                <tr><td><h4>%s</h4></td> 
                                <td><h4>  </h4> </p></td>
                                <td><h4>$%s</h4></td>
                                <td><h4>$%s</h4></td> 
                                <td><h4>$%s</h4></td> 
                                <td><h4>$%s</h4></td> 
                                <td><h4></h4></td> 
                                </tr>
                                </tbody>
                                        <thead class="thead-dark">
                                            <tr>
                                            <th style="text-align:center"  colspan="7">Movimientos</th>
                                            </tr>
                                            <tr>
                                            <th scope="col">Diario</th>
                                            <th scope="col">Nombre</th>
                                            <th scope="col">Fecha</th>
                                            <th scope="col">Saldo inicial</th>
                                            <th scope="col">Debe</th>
                                            <th scope="col">Haber</th>
                                            <th scope="col">Saldo</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                        %s
                                        </tbody>
                                        </table>""" % (cuenta,saldo_inicial,debe,haber,saldo,html_items_mov)
            html_items_code+=html_items_code2.encode('ascii', 'ignore')
 
        fechas=datetime.today()
        fecha_reporte_var  = str(datetime.strftime(fechas,"%Y-%m-%d"))
        rango_var =self.fecha_inicio+' a '+self.fecha_fin
        nombre_cuenta_var =self.cuenta_inicio.code+' '+self.cuenta_inicio.name
        tot_saldo_inicial_var ='{0:,.2f}'.format(float(tot_saldo_inicial))
        tot_cargo_var ='{0:,.2f}'.format(float(tot_cargo))
        tot_abono_var ='{0:,.2f}'.format(float(tot_abono))
        tot_saldo_var ='{0:,.2f}'.format(float(tot_saldo_inicial+tot_cargo-tot_abono))
        cuentas_var =codes_hijo
        html_auc="""
                    <table style="border:solid 2px; border-color: #00000" class="table">
                                <thead class="thead-dark">
                                    <tr>
                                    <th scope="col"><h3>Cuenta Principal</h4></th>
                                    <th scope="col"><h3>Saldo Inicial</h4></th>
                                    <th scope="col"><h3>Debe</h4></th>
                                    <th scope="col"><h3>Haber</h4></th>
                                    <th scope="col"><h3>Saldo</h4></th>
                                    </tr>
                                </thead>
                                <tbody>
                                <tr><td><h4>%s</h4></td> 
                                    <td><h4>$%s</h4></td>
                                    <td><h4>$%s</h4></td> 
                                    <td><h4>$%s</h4></td> 
                                    <td><h4>$%s</h4></td> 
                                </tr>
                                </tbody>
                            </table>
                                <table class="table">
                                %s
                                </table>
                                """ %(nombre_cuenta_var,tot_saldo_inicial_var,tot_cargo_var,tot_abono_var,tot_saldo_var,html_items_code)
        self.result_pc_html=html_auc
        excel_encode = self.get_decode_excel(fecha_reporte_var,rango_var,nombre_cuenta_var,tot_saldo_inicial_var,tot_cargo_var,tot_abono_var,tot_saldo_var, cuentas_var)
        self.csv_urls = "data:application/octet-stream;charset=utf-16le;base64,"+excel_encode
  


    @api.multi
    def search_pc_button1(self):
        server = self.env['presupuesto.config_auxiliares'].search([('status', '=', 'True')])
        servidor=server.server
        if(servidor>0):
            ###saldo inicial
            periodo = datetime.strptime(self.fecha_inicio, '%Y-%m-%d') if self.fecha_inicio else datetime.today()
            sql_si = """select saldo_inicial from v_balanza where periodo=%s and account_id=%s and anio='%s'"""
            self.env.cr.execute(sql_si % (periodo.month,self.cuenta_inicio.id,periodo.year))
            rows_sql_si = self.env.cr.dictfetchall()
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


    @api.one
    def _get_csv_url(self):
        self.csv_urls = "/csv/download/"



    @api.multi
    def get_decode_excel(self,fecha_reporte_var,rango_var,nombre_cuenta_var,tot_saldo_inicial_var,tot_cargo_var,tot_abono_var,tot_saldo_var, cuentas_var):
        style00 = xlwt.easyxf('font: name Arial, bold on;\
                            pattern: pattern solid, fore_colour white;\
                            align: vert centre, horiz centre;', num_format_str='#,##0.00')
        style1 = xlwt.easyxf('font: name Arial, bold 1,height 250;\
                            pattern: pattern solid, fore_colour gray50; \
                            align: vert centre, horiz centre;\
                            borders: top_color black, bottom_color black, right_color black, left_color black,\
                            left thin, right thin, top thin, bottom thin;'
                            , num_format_str='#,##0.00')
        style_mov = xlwt.easyxf('font: name Arial, bold off;\
                            pattern: pattern solid, fore_colour white;\
                            align: vert centre, horiz centre;\
                            borders: top_color black, bottom_color black, right_color black, left_color black,\
                            left thin, right thin, top thin, bottom thin;'
                            , num_format_str='#,##0.00')
        xlwt.easyxf('font: name Arial, bold off,height 250;\
                            pattern: pattern solid; \
                            align: vert centre, horiz centre;\
                            borders: top_color black, bottom_color black, right_color black, left_color black,\
                            left thin, right thin, top thin, bottom thin;'
                            , num_format_str='#,##0.00')
        style_mov_none = xlwt.easyxf('font: name Arial, bold off,height 250;\
                            pattern: pattern solid, fore_colour gray25; \
                            align: vert centre, horiz centre;\
                            borders: top_color black, bottom_color black, right_color black, left_color black,\
                            left thin, right thin, top thin, bottom thin;'
                            , num_format_str='#,##0.00')
        style_item = xlwt.easyxf('font: name Arial, bold off;\
                            pattern: pattern solid, fore_colour white;\
                            borders: top_color black, bottom_color black, right_color black, left_color black,\
                            left thin, right thin, top thin, bottom thin;'
                            , num_format_str='#,##0.00')
        style_item_acc = xlwt.easyxf('font: name Arial, bold 1;\
                            pattern: pattern solid, fore_colour white;\
                            borders: top_color black, bottom_color black, right_color black, left_color black,\
                            left thin, right thin, top thin, bottom thin;'
                            , num_format_str='#,##0.00')
        style_item_money_acc = xlwt.easyxf('font: name Arial, bold 1;\
                            pattern: pattern solid, fore_colour white;\
                            borders: top_color black, bottom_color black, right_color black, left_color black,\
                            left thin, right thin, top thin, bottom thin;'
                            , num_format_str='[$$-409]#,##0.00;-[$$-409]#,##0.00')
        style_item_money = xlwt.easyxf('font: name Arial, bold off;\
                            pattern: pattern solid, fore_colour white;\
                            borders: top_color black, bottom_color black, right_color black, left_color black,\
                            left thin, right thin, top thin, bottom thin;'
                            , num_format_str='[$$-409]#,##0.00;-[$$-409]#,##0.00')
        workbook = xlwt.Workbook()
        sheet = workbook.add_sheet('Auxiliares Contables')
        sheet.write_merge(0, 0, 0, 5, 'TRIBUNAL DE JUSTICIA ADMINISTRATIVA.', style00)
        sheet.write_merge(1, 1, 0, 5, u'DE LA CIUDAD DE MÉXICO.', style00)
        sheet.write_merge(2, 2, 0, 5, rango_var, style00)
        sheet.write_merge(3, 3, 0, 5, u'Auxiliar', style00)
        sheet.write_merge(5, 5, 0, 0, 'Cuenta', style1)
        sheet.write_merge(5, 5, 1, 1, '', style1)
        sheet.write_merge(5, 5, 2, 2, '', style1)
        sheet.write_merge(5, 5, 3, 3, '', style1)
        sheet.write_merge(5, 5, 4, 4, '', style1)
        sheet.write_merge(5, 5, 5, 5,'Saldo inicial', style1)
        sheet.write_merge(5, 5, 6, 6,'Debe', style1)
        sheet.write_merge(5, 5, 7, 7, 'Haber', style1)
        sheet.write_merge(5, 5, 8, 8, 'Saldo', style1)
        sheet.write_merge(6, 6, 0, 0, nombre_cuenta_var, style_item_acc)
        sheet.write_merge(6, 6, 1, 1, '', style_item)
        sheet.write_merge(6, 6, 2, 2, '', style_item)
        sheet.write_merge(6, 6, 3, 3, '', style_item)
        sheet.write_merge(6, 6, 4, 4, '', style_item)
        sheet.write_merge(6, 6, 5, 5, tot_saldo_inicial_var, style_item_money_acc)
        sheet.write_merge(6, 6, 6, 6, tot_cargo_var, style_item_money_acc)
        sheet.write_merge(6, 6, 7, 7, tot_abono_var, style_item_money_acc)
        sheet.write_merge(6, 6, 8, 8, tot_saldo_var, style_item_money_acc)
        n = 7
        for item in cuentas_var:       
            sheet.write_merge(n, n, 0, 0, 'Cuenta', style1)
            sheet.write_merge(n, n, 1, 1, '', style1)
            sheet.write_merge(n, n, 2, 2, '', style1)
            sheet.write_merge(n, n, 3, 3, '', style1)
            sheet.write_merge(n, n, 4, 4, '', style1)
            sheet.write_merge(n, n, 5, 5,'Saldo inicial', style1)
            sheet.write_merge(n, n, 6, 6,'Debe', style1)
            sheet.write_merge(n, n, 7, 7, 'Haber', style1)
            sheet.write_merge(n, n, 8, 8, 'Saldo', style1)       
            n += 1
            sheet.write_merge(n, n, 0, 0, item['code_hijo'], style_item_acc)
            sheet.write_merge(n, n, 1, 1, '', style_item)
            sheet.write_merge(n, n, 2, 2, '', style_item)
            sheet.write_merge(n, n, 3, 3, '', style_item)
            sheet.write_merge(n, n, 4, 4, '', style_item)
            sheet.write_merge(n, n, 5, 5, item['t_saldo_inicial'], style_item_money_acc)
            sheet.write_merge(n, n, 6, 6, item['t_debe'], style_item_money_acc)
            sheet.write_merge(n, n, 7, 7, item['t_haber'], style_item_money_acc)
            sheet.write_merge(n, n, 8, 8, item['t_saldo'], style_item_money_acc)
            n += 1
            sheet.write_merge(n,n, 0, 7, 'Movimientos', style_mov)
            n += 1
            sheet.write_merge(n,n, 0, 0, 'Diario', style_mov)
            sheet.write_merge(n,n, 1, 1, 'Nombre', style_mov)
            sheet.write_merge(n,n, 2, 2, 'Referencia', style_mov)
            sheet.write_merge(n,n, 3, 3, 'No. CLC', style_mov)
            sheet.write_merge(n,n, 4, 4, 'Fecha', style_mov)
            sheet.write_merge(n,n, 5, 5, 'Saldo inicial', style_mov)
            sheet.write_merge(n,n, 6, 6, 'Cargo', style_mov)
            sheet.write_merge(n,n, 7, 7, 'Abono', style_mov)
            sheet.write_merge(n,n, 8, 8, 'Saldo', style_mov)
            n += 1
            if(item['movimientos']):
                for i in item['movimientos']:
                    sheet.write_merge(n, n, 0, 0, i['diario'], style_item)
                    sheet.write_merge(n, n, 1, 1, i['nom_movimiento'], style_item)
                    sheet.write_merge(n, n, 2, 2, i['referencia'], style_item)
                    sheet.write_merge(n, n, 3, 3, i['no_clc'], style_item)
                    sheet.write_merge(n, n, 4, 4, i['fecha_mov_det'], style_item_money)
                    sheet.write_merge(n, n, 5, 5, i['saldo_inicial'], style_item_money)
                    sheet.write_merge(n, n, 6, 6, i['cargo'], style_item_money)
                    sheet.write_merge(n, n, 7, 7, i['abono'], style_item_money)
                    sheet.write_merge(n, n, 8, 8, i['saldo'], style_item_money)
                    n += 1
            else:
                sheet.write_merge(n,n, 0, 5, 'Sin Movimientos', style_mov_none)
                n += 1 
            n += 1    
        output = StringIO()
        workbook.save(output)
        out = base64.encodestring(output.getvalue())
        return out

