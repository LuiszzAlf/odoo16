# -*- coding: utf-8 -*-
from datetime import datetime
import calendar
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


class BalanzaV2(models.TransientModel):
    _name = 'balanza_v2.wizard'

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
        # V2 
        if(periodo==1):
            periodo_inicio_anterior=12
            anio_inicio_anterior=anio-1
        else:
            periodo_inicio_anterior=periodo-1
            anio_inicio_anterior=anio
        last_day = calendar.monthrange(anio,periodo)[1] #obtine el ultimo dia del mes
        last_dayf = calendar.monthrange(anio,periodo_f)[1] #obtine el ultimo dia del mes
        periodo_inicio_dia_fin = datetime(anio,periodo,last_day).date()#obtiene el ultimo dia del mes 
        periodo_fin_dia_fin = datetime(anio,periodo_f,last_dayf).date()#obtiene el ultimo dia del mes 
        if(periodo==1):
            sql_all_ht = """select 
                                    aa.id,
                                    aa.code,
                                    concat(aa.code, ' ', aa."name") cuentas,
                                    coalesce(vb.saldo_inicial, 0) saldo_inicial,
                                    coalesce(sum(vb.debe),0)  AS debe,
                                    coalesce(sum(vb.haber),0) AS haber,
                                    coalesce(vb.saldo_inicial, 0)+coalesce(sum(vb.debe),0)-coalesce(sum(vb.haber),0) AS saldo_final,
                                    coalesce(vb.saldo_inicial, 0)-coalesce(sum(vb.haber),0)+coalesce(sum(vb.debe),0) AS saldo_final_deudora
                                from account_account aa
                                    left join v_balanza vb on  vb.account_id=aa.id and vb.periodo=%s and vb.anio='%s'
                                where aa.code not like '%s'
                                GROUP by 1,2,3,4
                                order by aa.code;"""
        else:
            sql_all_ht = """select 
                                    aa.id,
                                    aa.code,
                                    concat(aa.code, ' ', aa."name") cuentas,
                                    (CASE WHEN aa.code like '%s' THEN 0 ELSE  COALESCE(vb.saldo_final, 0) END) saldo_inicial,
                                    coalesce(sum(mp.debit),0)  AS debe,
                                    coalesce(sum(mp.credit),0) AS haber,
                                    (CASE WHEN aa.code like '%s' THEN 0 ELSE  COALESCE(vb.saldo_final, 0) END)+coalesce(sum(mp.debit),0)-coalesce(sum(mp.credit),0) AS saldo_final,
                                    (CASE WHEN aa.code like '%s' THEN 0 ELSE  COALESCE(vb.saldo_final, 0) END)-coalesce(sum(mp.credit),0)+coalesce(sum(mp.debit),0) AS saldo_final_deudora
                                from account_account aa
                                    left join movimientos_polizas mp on mp.account_id = aa.id and mp.date between '%s' and '%s'
                                    left join v_balanza vb on  vb.account_id=aa.id and vb.periodo=%s and vb.anio='%s'
                                where aa.code not like '%s'
                                GROUP by 1,2,3,4
                                order by aa.code;"""
            
        sql_bal_nivel_mayor="""select 
                                aa.id,
                                aa.code,
                                concat(aa.code, ' ', aa."name") cuentas,
                                (CASE WHEN aa.code like '%s' THEN 0 ELSE  COALESCE(vb.saldo_final, 0) END) saldo_inicial,
                                coalesce(sum(mp.debit),0)  AS debe,
                                coalesce(sum(mp.credit),0) AS haber,
                                (CASE WHEN aa.code like '%s' THEN 0 ELSE  COALESCE(vb.saldo_final, 0) END)+coalesce(sum(mp.debit),0)-coalesce(sum(mp.credit),0) AS saldo_final,
                                (CASE WHEN aa.code like '%s' THEN 0 ELSE  COALESCE(vb.saldo_final, 0) END)-coalesce(sum(mp.credit),0)+coalesce(sum(mp.debit),0) AS saldo_final_deudora
                            from account_account aa
                                left join movimientos_polizas mp on mp.account_id = aa.id and mp.date between '%s' and '%s'
                                left join v_balanza vb on  vb.account_id=aa.id and vb.periodo=%s and vb.anio='%s'
                            where 
                                substring(split_part(aa.code::TEXT,'.', 1),3,3)!='0'
                                and split_part(aa.code::TEXT,'.', 1) not in ('114','123') 
                                and split_part(aa.code::TEXT,'.', 2)='0'
                                and split_part(aa.code::TEXT,'.', 3)='0000'
                                and split_part(aa.code::TEXT,'.', 4)='00'
                            GROUP by 1,2,3,4
                            order by aa.code;"""
        sql_bal_nivel_mayor_rango="""select b."name" as cuentas,
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
                                and b.code not like '%s'
                                group by 1,2,3
                                order by b.code;"""
        sql_bal_ultimo_nivel="""select distinct concat(b.code,' ',b."name") as cuentas,b.code,account_id,a.periodo,a.saldo_inicial,a.debe,a.haber,a.saldo_final 
                                from tjacdmx_balanza_comprobacion a
                                inner join account_account b on b.id=a.account_id
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
            if(periodo==1):
                self.env.cr.execute(sql_all_ht % (periodo,str(anio),str('8%')))
            else:
                self.env.cr.execute(sql_all_ht % (str('8%'),str('8%'),str('8%'),periodo_inicio,periodo_inicio_dia_fin,periodo_inicio_anterior,anio_inicio_anterior,str('8%')))
        elif (self.radio_nivel_valanza==2):
            self.env.cr.execute(sql_bal_nivel_mayor % (str('8%'),str('8%'),str('8%'),periodo_inicio,periodo_inicio_dia_fin,periodo_inicio_anterior,anio_inicio_anterior))
        elif (self.radio_nivel_valanza==3):
            self.env.cr.execute(sql_bal_nivel_mayor_rango % (str(periodo_inicio),str(periodo_fin),str('8%')))
        elif (self.radio_nivel_valanza==4):
            self.env.cr.execute(sql_bal_ultimo_nivel % (periodo_inicio,periodo_inicio,periodo_inicio,periodo_inicio,periodo_inicio))
        elif (self.radio_nivel_valanza==5):
            self.env.cr.execute(sql_bal_ultimo_nivel_rango % (periodo,self.anio,str('8%'),self.anio,periodo,periodo_f,periodo,self.anio,str('8%'),str('211.2.0000.00%'),self.anio,periodo,periodo_f))
        elif (self.radio_nivel_valanza==6):
            self.env.cr.execute(sql_bal_todo_rango % (periodo,self.anio,self.anio,periodo,periodo_f,str('8%')))
        # elif (self.radio_nivel_valanza==6):
        #     self.env.cr.execute(sql_all_ht % (periodo_inicio,periodo_fin_dia_fin,periodo_inicio_anterior,anio_inicio_anterior))
                                            #  (self.periodo,self.periodo_fin,self.anio,self.anio,self.periodo,self.periodo_fin))
            
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
                    'periodo': str(periodo_inicio),
                    'periodo_fecha': periodo,
                    'anio': anio,
                    'saldo_inicial': saldo_inicial,
                    'debe': i['debe'],
                    'haber': i['haber'],
                    'saldo': i['saldo_final']}
                # raise ValidationError("debug: %s" %(cuentas))
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
    def sincronizar_balanza(self):
        anio=self.anio
        periodo=self.periodo
        periodo_inicio=datetime(anio,periodo,01).date()#obtiene el primer dia del mes 
        if(periodo==1):
            periodo_inicio_anterior=12
            anio_inicio_anterior=anio-1
        else:
            periodo_inicio_anterior=periodo-1
            anio_inicio_anterior=anio
        last_day = calendar.monthrange(anio,periodo)[1] #obtine el ultimo dia del mes
        periodo_inicio_dia_fin = datetime(anio,periodo,last_day).date()#obtiene el ultimo dia del mes 
        account_account = self.env['account.account'].search([])
        if(periodo==1):
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
        else:
            sql_search_account="""select 
                                    aa.id,
                                    aa.code,
                                    concat(aa.code, ' ', aa."name") nombre,
                                    (CASE WHEN aa.code like '%s' THEN 0 ELSE  COALESCE(vb.saldo_final, 0) END) saldo_inicial,
                                    coalesce(sum(mp.debit),0)  AS cargo,
                                    coalesce(sum(mp.credit),0) AS abono,
                                    (CASE WHEN aa.code like '%s' THEN 0 ELSE  COALESCE(vb.saldo_final, 0) END)+coalesce(sum(mp.debit),0)-coalesce(sum(mp.credit),0) AS saldo_final,
                                    (CASE WHEN aa.code like '%s' THEN 0 ELSE  COALESCE(vb.saldo_final, 0) END)-coalesce(sum(mp.credit),0)+coalesce(sum(mp.debit),0) AS saldo_final_deudora
                                from account_account aa
                                    left join movimientos_polizas mp on mp.account_id = aa.id and mp.date between '%s' and '%s'
                                    left join v_balanza vb on  vb.account_id=aa.id and vb.periodo=%s and vb.anio='%s'
                                GROUP by 1,2,3,4
                                order by aa.code;"""
            self.env.cr.execute(sql_search_account%(str('8%'),str('8%'),str('8%'),periodo_inicio,periodo_inicio_dia_fin,periodo_inicio_anterior,anio_inicio_anterior))

        results = self.env.cr.fetchall()
        for cuenta in results:
            sql_update_balance = """INSERT INTO  "tjacdmx_balanza_comprobacion"(account_id, periodo, saldo_inicial, debe, haber, saldo_final)
                                    VALUES(
                                        %s,'%s','%s','%s','%s','%s'
                                    )
                                    ON CONFLICT (account_id, periodo) DO UPDATE SET
                                        saldo_inicial = EXCLUDED.saldo_inicial,
                                        debe = EXCLUDED.debe,
                                        haber = EXCLUDED.haber,
                                        saldo_final = EXCLUDED.saldo_final
                                    RETURNING 1;""" % (cuenta[0],periodo_inicio,cuenta[3],cuenta[4],cuenta[5],cuenta[6])
            self.env.cr.execute(sql_update_balance)
            results_insert = self.env.cr.fetchall()

        