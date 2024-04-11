# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.translate import _
import collections
import xlwt 
import pytz
import base64 
import pandas as pd
from StringIO import StringIO
from dateutil.relativedelta import relativedelta

PERIODO_SELECT = [(periodo, periodo) for periodo in range(1,13)]
EJERCICIO_SELECT = [ (year, year) for year in range(2018, 2031) ]


class Remanentes(models.TransientModel):
    _name = 'balanza.wizard'

    @api.model
    def _select_anio(self):
        fecha = datetime.today()
        return  fecha.year
    
    @api.model
    def _select_periodo(self):
        fecha = datetime.today()
        return  int(fecha.month)

    cuenta_inicio = fields.Many2one('account.account', string='Cuenta inicio')
    cuenta_fin = fields.Many2one('account.account', string='Cuenta fin')
    anio=fields.Selection(EJERCICIO_SELECT, default=_select_anio)
    periodo = fields.Selection(PERIODO_SELECT, default=_select_periodo)
    periodo_fin=fields.Selection(PERIODO_SELECT, default=_select_periodo)
    fecha_balanza = fields.Date(string='Fecha del periodo')
    fcheck_state=fields.Boolean(string='Mostrar opciones',default=False)
    radio_nivel_valanza=fields.Selection([(1,'Todo'),(2,'Nivel Mayor'),(3,'Nivel Mayor (Rango)'),(4,'Ultimo Nivel'),(5,'Ultimo Nivel (Rango)'),(6,'Rango')], string='Nivel mayor', default=1)
    result_pc_html=fields.Html(string='Resultados',compute='search_pc_button_va')
    csv_urls = fields.Char(compute='search_pc_button_va')

    anio_cal = fields.Char(string='Fecha inicio cla',compute='_onchange_date_cal')
    periodo_cal = fields.Char(string='Fecha fin cal', compute='_onchange_date_cal')
    periodo_fin_cal = fields.Char(string='Fecha fin cal', compute='_onchange_date_cal')
    radio_nivel_valanza_cal = fields.Char(string='Fecha fin cal', compute='_onchange_date_cal')

    anio_cierre=fields.Selection(EJERCICIO_SELECT, default=_select_anio)
    cuenta_saldo = fields.Many2one('account.account', string='Cuenta de cierre')

    @api.multi
    @api.onchange('anio','periodo','periodo_fin','radio_nivel_valanza')
    def _onchange_date_cal(self):
        self.anio_cal=self.anio
        self.periodo_cal=self.periodo
        self.periodo_fin_cal=self.periodo_fin
        self.radio_nivel_valanza_cal=self.radio_nivel_valanza
    
    @api.multi
    def search_cuentas_origen(self):
        datas = {}
        anio=self.anio
        periodo=self.periodo
        periodo_f=self.periodo_fin
        radio_nivel_valanza=self.radio_nivel_valanza
        periodo_inicio=datetime(anio,periodo,01).date()
        periodo_fin=datetime(anio,periodo_f,01).date()
        sql_all_ht="""select * from v_balanza where periodo=%s and anio='%s' and code not like '%s' order by code;"""
        sql_bal_nivel_mayor="""SELECT * from v_balanza
                                where periodo = %s
                                and anio='%s' 
                                and substring(split_part(code::TEXT,'.', 1),3,3)!='0'
                                and split_part(code::TEXT,'.', 1) not in ('114','123') 
                                and split_part(code::TEXT,'.', 2)='0'
                                and split_part(code::TEXT,'.', 3)='0000'
                                and split_part(code::TEXT,'.', 4)='00'
                                and code not like '%s'
                                order by code;"""
        sql_bal_nivel_mayor_rango="""select concat(b.code, ' ', b."name") as cuentas,
                                b.code as code,
                                account_id,
                                sum(a.debe) debe,
                                sum(a.haber) haber
                                from tjacdmx_balanza_comprobacion a
                                inner join account_account b on b.id=a.account_id
                                where periodo between '%s' and  '%s'
                                and substring(split_part(b.code::TEXT,'.', 1),3,3)!='0'
                                and split_part(b.code::TEXT,'.', 1) not in ('114','123') 
                                and split_part(code::TEXT,'.', 2)='0'
                                and split_part(code::TEXT,'.', 3)='0000'
                                and split_part(code::TEXT,'.', 4)='00'
                                and code not like '%s'
                                group by 1,2,3
                                order by b.code;"""
        sql_bal_ultimo_nivel="""select distinct concat(b.code,' ',b."name") as cuentas,b.code,account_id,a.periodo,a.saldo_inicial,a.debe,a.haber,a.saldo_final 
                                from tjacdmx_balanza_comprobacion a
                                inner join account_account b on b.id=a.account_id and  b.code not like '%s'
                                where 
                                split_part(code::TEXT,'.', 1)='322' and account_id not in (2635,320) and periodo='%s'
                                or account_id not in (180,170,171,172,173,2635,320) and split_part(code::TEXT,'.', 1)='126'  and periodo='%s'
                                or split_part(code::TEXT,'.', 1)='115' and periodo='%s'
                                or split_part(code::TEXT,'.', 4)>='01' and periodo='%s'
                                or account_id in (165,162,181,182,174,175,176,177,178,179,141,142,146,158,705,754,877)
                                and periodo='%s' 
                                order by b.code;
                                        """
        sql_bal_ultimo_nivel_rango="""(select concat(b.code,' ',b."name") as cuentas,
                                            a.code,
                                            a.account_id,
                                            c.saldo_inicial as saldo_inicial,
                                            sum(a.debe) as debe,
                                            sum(a.haber) as haber,
                                            c.saldo_inicial + sum(a.debe) - sum(a.haber) as saldo_final
                                        from
                                            v_balanza a
                                            inner join account_account b on b.id = a.account_id
                                            inner join v_balanza c on c.account_id = a.account_id and c.periodo = '%s' and c.anio = '%s'
                                        where
                                            a.code not like '%s'
                                            and split_part(a.code :: text, '.', 4) >= '01'
                                            and a.anio = '%s'
                                            and a.periodo between '%s' and '%s'
                                        group by 1,2,3,4 order by code)
                                        union
                                        (select
                                            b.name as cuentas,
                                            a.code,
                                            a.account_id,
                                            c.saldo_inicial as saldo_inicial,
                                            sum(a.debe) as debe,
                                            sum(a.haber) as haber,
                                            c.saldo_inicial + sum(a.debe) - sum(a.haber) as saldo_final
                                        from
                                            v_balanza a
                                            inner join account_account b on b.id = a.account_id
                                            inner join v_balanza c on c.account_id = a.account_id and c.periodo = '%s' and c.anio = '%s'
                                        where
                                            a.code not like '%s'
                                            and a.code not like '%s'
                                            and a.account_id in (110,111,112,113,114,115,125,141,142,146,158,162,165,174,175,176,177,178,179,181,182,226,321,322,323,324,325,326,327,328,329,330,705,2927)
                                            and a.anio = '%s'
                                            and a.periodo between '%s' and '%s'
                                        group by 1,2,3,4
                                        order by code) order by code;"""
        sql_bal_todo_rango="""SELECT
                                concat(b.code,' ',b."name") as cuentas,
                                a.code,
                                a.account_id,
                                c.saldo_inicial as saldo_inicial,
                                sum(a.debe) as debe,
                                sum(a.haber) as haber,
                                c.saldo_inicial+sum(a.debe)-sum(a.haber) as saldo_final
                            from
                                v_balanza a
                            inner join account_account b on b.id = a.account_id
                            inner join v_balanza c on c.account_id = a.account_id and c.periodo='%s' and c.anio='%s'
                            where
                                a.anio = '%s'
                                and a.periodo between '%s' and '%s'
                                and a.code not like '%s'
                            group by 1,2,3,4 order by code;"""
        if(self.radio_nivel_valanza==1):
            self.env.cr.execute(sql_all_ht % (self.periodo,self.anio,str('8%')))
        elif (self.radio_nivel_valanza==2):
            self.env.cr.execute(sql_bal_nivel_mayor % (self.periodo,self.anio,str('8%')))
        elif (self.radio_nivel_valanza==3):
            self.env.cr.execute(sql_bal_nivel_mayor_rango % (str(periodo_inicio),str(periodo_fin),str('8%')))
        elif (self.radio_nivel_valanza==4):
            self.env.cr.execute(sql_bal_ultimo_nivel % (str('8%'),periodo_inicio,periodo_inicio,periodo_inicio,periodo_inicio,periodo_inicio))
        elif (self.radio_nivel_valanza==5):
            self.env.cr.execute(sql_bal_ultimo_nivel_rango % (periodo,self.anio,str('8%'),self.anio,periodo,periodo_f,periodo,self.anio,str('8%'),str('211.2.0000.00%'),self.anio,periodo,periodo_f))
        elif (self.radio_nivel_valanza==6):
            self.env.cr.execute(sql_bal_todo_rango % (self.periodo,self.anio,self.anio,self.periodo,self.periodo_fin,str('8%')))
        rows_sql = self.env.cr.dictfetchall()
        array_balnaza=[] 
        
        if (radio_nivel_valanza==1 or radio_nivel_valanza==2 or radio_nivel_valanza==4 ):
            for i in rows_sql:
                debe=i['debe']
                haber=i['haber']
                saldo_inicial=i['saldo_inicial']
                saldo_final=i['saldo_final']
                cuentas = {
                    'cuenta': i['cuentas'],
                    'code': i['code'],
                    'periodo': i['periodo'],
                    'periodo_fecha': periodo,
                    'anio': anio,
                    'saldo_inicial': saldo_inicial,
                    'debe': i['debe'],
                    'haber': i['haber'],
                    'saldo': i['saldo_final']}
                array_balnaza.append(cuentas)
        elif (radio_nivel_valanza==3):
            for i in rows_sql:
                sql_si_sf="""SELECT saldo_inicial,saldo_final from v_balanza where periodo in (%s,%s) and account_id=%s and anio='%s' limit 1;"""
                self.env.cr.execute(sql_si_sf % (periodo,periodo_f,i['account_id'],self.anio))
                rows_code =  self.env.cr.dictfetchall()
                debe=i['debe']
                haber=i['haber']
                if(rows_code):
                    saldo_inicial=rows_code[0]['saldo_inicial']
                    saldo_final=rows_code[0]['saldo_final']
                else:
                    saldo_inicial=0
                    saldo_final=0
                
                cuentas = {
                    'cuenta': i['cuentas'],
                    'code': i['code'],
                    'saldo_inicial': saldo_inicial,
                    'periodo_fecha': periodo,
                    'debe': debe,
                    'haber': haber,
                    'saldo': saldo_final}
                array_balnaza.append(cuentas)
        elif (radio_nivel_valanza==6 or radio_nivel_valanza==5):
            for i in rows_sql:
                cuentas = {
                    'cuenta': i['cuentas'],
                    'code': i['code'],
                    'saldo_inicial': i['saldo_inicial'],
                    'periodo_fecha': periodo,
                    'debe': i['debe'],
                    'haber': i['haber'],
                    'saldo': i['saldo_final']}
                array_balnaza.append(cuentas)
        tz_MX = pytz.timezone('America/Mexico_City') 
        datetime_CDMX = datetime.now(tz_MX)
        fechas=datetime_CDMX.strftime("%Y-%m-%d %H:%M:%S")
        if (radio_nivel_valanza==6):
            datas['periodo'] = str(periodo)+'-'+str(periodo_f)
        else:
            datas['periodo'] = array_balnaza[1]['periodo_fecha'] if array_balnaza[1]['periodo_fecha'] else 0
        datas['fecha_reporte'] = str(fechas)
        datas['cuentas'] = array_balnaza
        
        return self.env['report'].get_action([], 'reportes.report_balanza', data=datas)
    
    
    
     

    @api.multi
    def clear_accounts(self):
        self.write({'cuenta_inicio': False})
        self.write({'cuenta_fin': False})

    @api.multi
    def sincronizar_balanza(self):
        anio=self.anio
        periodo=self.periodo
        fecha_balanza_up=datetime(anio,periodo,01).date()
        sql="""
        WITH periodos_registrados AS (
        SELECT 
                DATE(generate_series(MIN(date_trunc('month', a.date)), MAX(a.date), '1 month')) periodo
        FROM account_move_line a)
        SELECT 
        a."id" account_id,
        b.periodo,
        calcular_balanza_2019(a."id", b.periodo)
        FROM account_account a
        CROSS JOIN periodos_registrados b 
        WHERE periodo = '%s'"""
        self.env.cr.execute(sql % (fecha_balanza_up))
        rows_sql = self.env.cr.dictfetchall()
        # raise ValidationError("Proceso terminado")

    @api.multi
    def close_year(self):
        print ('debug')
        
        





       # @api.multi
    # def search_pc_button_va(self):
    #     sql_all_ht="""select * from v_balanza where periodo=%s and anio='%s'  order by code;"""
    #     sql_bal_nivel_mayor="""SELECT * from v_balanza
    #                             where periodo = %s
    #                             and anio='%s' 
    #                             and substring(split_part(code::TEXT,'.', 1),3,3)!='0'
    #                             and split_part(code::TEXT,'.', 1) not in ('114','123') 
    #                             and split_part(code::TEXT,'.', 2)='0'
    #                             and split_part(code::TEXT,'.', 3)='0000'
    #                             and split_part(code::TEXT,'.', 4)='00'
    #                             order by code;"""
    #     if(self.radio_nivel_valanza==1):
    #         self.env.cr.execute(sql_all_ht % (self.periodo, self.anio))
    #     elif (self.radio_nivel_valanza==2):
    #         self.env.cr.execute(sql_bal_nivel_mayor % (self.periodo, self.anio))
            
    #     rows_sqlht = self.env.cr.dictfetchall()
    #     ids=[]
    #     for i in rows_sqlht:
    #         cuentas = {
    #             'cuenta': i['cuentas'],
    #             'code': i['code'],
    #             'periodo': i['periodo'],
    #             'periodo_fecha': i['periodo_fecha'],
    #             'anio': i['anio'],
    #             'saldo_inicial': i['saldo_inicial'],
    #             'debe': i['debe'],
    #             'haber': i['haber'],
    #             'saldo': i['saldo_final']}
    #         ids.append(cuentas)
    #     html_items=""
    #     for i in ids:
    #         cuenta=i['cuenta']
    #         saldo_inicial=i['saldo_inicial']
    #         debe=i['debe']
    #         haber=i['haber']
    #         saldo=i['saldo']
    #         html_items2="""
    #         <tr><td><p>%s</p></td> 
    #         <td><p>%s</p></td>
    #         <td><p>%s</p></td> 
    #         <td><p>%s</p></td> 
    #         <td><p>%s</p></td> 
    #         </tr>""" % (cuenta,saldo_inicial,debe,haber,saldo)
    #         html_items+=html_items2.encode('ascii', 'ignore')
    #     html="""
    #         <table id="tabla_valanza" class="table table-striped">
    #                 <thead class="thead-dark">
    #                 <tr>
    #                 <th>Cuenta</th>
    #                 <th>Saldo inicial</th>
    #                 <th>Debe</th>
    #                 <th>Haber</th>
    #                 <th>Saldo</th>
    #                 </tr>
    #                 </thead>
    #                 %s
    #         </table>""" % (html_items)
    #     self.result_pc_html=html
    #     excel_encode = self.get_decode_excel(ids,self.radio_nivel_valanza)
    #     self.csv_urls = "data:application/octet-stream;charset=utf-16le;base64,"+excel_encode
        
    # @api.multi
    # def get_decode_excel(self, ids,name):
    #     if(name==1):
    #         nombre_balanza='Balanza'
    #     elif (name==2):
    #         nombre_balanza='Nivel Mayor'
    #     elif (name==3):
    #         nombre_balanza='Nivel Mayor (Rango)'
    #     elif (name==4):
    #         nombre_balanza='Ultimo Nivel'
    #     elif (name==5):
    #         nombre_balanza='Ultimo Nivel (Rango)'

    #     style0 = xlwt.easyxf('font: name Arial, bold on;\
    #                             pattern: pattern solid, fore_colour white;\
    #                             borders: top_color black, bottom_color black, right_color black, left_color black,\
    #                             left thin, right thin, top thin, bottom thin;'
    #                             , num_format_str='#,##0.00')
    #     style00 = xlwt.easyxf('font: name Arial, bold on;\
    #                         pattern: pattern solid, fore_colour white;\
    #                         align: vert centre, horiz centre;', num_format_str='#,##0.00')

    #     style1 = xlwt.easyxf('font: name Arial, bold 1,height 250;\
    #                         pattern: pattern solid, fore_colour aqua; \
    #                         borders: top_color black, bottom_color black, right_color black, left_color black,\
    #                         left thin, right thin, top thin, bottom thin;'
    #                         , num_format_str='#,##0.00')
    #     style_item = xlwt.easyxf('font: name Arial, bold off;\
    #                         pattern: pattern solid, fore_colour white;\
    #                         borders: top_color black, bottom_color black, right_color black, left_color black,\
    #                         left thin, right thin, top thin, bottom thin;'
    #                         , num_format_str='#,##0.00')
    #     style_item_money = xlwt.easyxf('font: name Arial, bold off;\
    #                         pattern: pattern solid, fore_colour white;\
    #                         borders: top_color black, bottom_color black, right_color black, left_color black,\
    #                         left thin, right thin, top thin, bottom thin;'
    #                         , num_format_str='[$$-409]#,##0.00;-[$$-409]#,##0.00')
    #     style_item_money_bold = xlwt.easyxf('font: name Arial, bold on;\
    #                         pattern: pattern solid, fore_colour white;\
    #                         borders: top_color black, bottom_color black, right_color black, left_color black,\
    #                         left thin, right thin, top thin, bottom thin;'
    #                         , num_format_str='[$$-409]#,##0.00;-[$$-409]#,##0.00')
    #     workbook = xlwt.Workbook()
    #     sheet = workbook.add_sheet('Balanza contable')
    #     sheet.write_merge(0, 0, 0, 4, 'TRIBUNAL DE JUSTICIA ADMINISTRATIVA.', style00)
    #     sheet.write_merge(1, 1, 0, 4, 'DE LA CIUDAD DE MEXICO.', style00)
    #     sheet.write_merge(2, 2, 0, 4, nombre_balanza, style00)
    #     sheet.write_merge(3, 3, 0, 4, u'Balanza de comprobación', style00)
    #     sheet.write_merge(6, 6, 0, 0, 'Codigo', style1)
    #     sheet.write_merge(6, 6, 1, 1, 'Cuenta', style1)
    #     sheet.write_merge(6, 6, 2, 2,'Saldo inicial', style1)
    #     sheet.write_merge(6, 6, 3, 3,'Debe', style1)
    #     sheet.write_merge(6, 6, 4, 4, 'Haber', style1)
    #     sheet.write_merge(6, 6, 5, 5, 'Saldo', style1)
    #     n = 7
    #     for item in ids:               
    #         sheet.write_merge(n, n, 0, 0, item['code'], style_item)
    #         sheet.write_merge(n, n, 1, 1, item['cuenta'], style_item)
    #         sheet.write_merge(n, n, 2, 2, item['saldo_inicial'], style_item_money)
    #         sheet.write_merge(n, n, 3, 3, item['debe'], style_item_money)
    #         sheet.write_merge(n, n, 4, 4, item['haber'], style_item_money)
    #         sheet.write_merge(n, n, 5, 5, item['saldo'], style_item_money)
    #         n += 1
    #     output = StringIO()
    #     workbook.save(output)
    #     out = base64.encodestring(output.getvalue())
    #     return out
    