from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import ValidationError,UserError
from odoo.tools.translate import _
from num2words import num2words

PERIODO_SELECT = [(periodo, periodo) for periodo in range(1,13)]
EJERCICIO_SELECT = [ (year, year) for year in range(2020, 2031)]

class wizard_reportes_financieros(models.TransientModel):
    _name='tjacdmx_wizard_reportes_financierosv2'
    _description='Reportes financieros v2'
    
    @api.model
    def _select_anio(self):
        fecha = datetime.today()
        return  fecha.year
    
    @api.model
    def _select_periodo(self):
        fecha = datetime.today()
        return  int(fecha.month)

    reporte_select = fields.Many2one('reportes.clase_reportes', required=True, domain="[('tipo_reporte', '=', 3)]")
    periodo = fields.Selection(PERIODO_SELECT,required = True, default=_select_periodo)
    anio_fiscal = fields.Selection(EJERCICIO_SELECT,required = True, default=_select_anio)
    

    @api.multi
    def action_reportes_financieros(self, values):

        if self.reporte_select.no_reporte == 1:
            datas={}
            res = self.read(['periodo','anio_fiscal'])
            sql_cuentas="""
                        with saldos_anterior as (
                        select
                            b.saldo_final,
                            b.account_id
                        from
                            v_balanza b
                        where
                            periodo = 12
                            and anio = '%s')
                        select
                            a.code,
                            a.account_id,
                            ABS(a.saldo_inicial) as saldo_inicial,
                            ABS(a.saldo_final) as saldo_final,
                            ABS(b.saldo_final) as saldo_anterior,
                            ABS(a.saldo_final) -ABS(b.saldo_final) importe,
                            (case
                                when ABS((ABS(a.saldo_final)-ABS(b.saldo_final))) > 0 then nullif((ABS(a.saldo_final)-ABS(b.saldo_final))/nullif(ABS(b.saldo_final), 0), 0)*100
                                else 0
                            end) porcentaje
                        from
                            v_balanza a
                        join saldos_anterior b on
                            b.account_id = a.account_id
                        where
                            a.anio = '%s'
                            and a.periodo = %s
                            and a.account_id in (38, 45, 52, 62, 72, 98, 105, 117, 108, 127, 137, 143, 147, 151, 161, 164, 167, 170,186, 226, 253, 275, 277, 283, 291, 312, 318, 2635,333,338,356,472,558,684);"""
            self.env.cr.execute(sql_cuentas % (int(self.anio_fiscal-1),self.anio_fiscal,self.periodo))
            row_cuentas = self.env.cr.dictfetchall()
            items=[]
            for item in row_cuentas:
                it={
                'account_id':item['account_id'],
                'saldo_final':float(item['saldo_final']),
                'saldo_anterior':float(item['saldo_anterior']),
                'importe':float(item['importe']),
                'porcentaje':item['porcentaje'] if item['porcentaje'] else 0,
                }
                items.append(it)
            # raise ValidationError("debug: %s"  % (items))
            datas['items']=items
            datas['anio_fiscal']= self.anio_fiscal
            datas['anio_fiscal_anterior']= self.anio_fiscal-1
            datas['periodo_fiscal']= self.periodo
            return self.env['report'].get_action([], 'reportes.sfcompv2', data=datas)
        elif self.reporte_select.no_reporte == 2:
            datas = {}
            res = self.read(['periodo','anio_fiscal'])
            res = res and res[0] or {}
            if self.periodo and self.anio_fiscal:
                self.env.cr.execute("""
                        SELECT 
                        account_id,
                        code,
                        periodo,
                        anio,
                        ABS(saldo_final)as mes_consulta,
                        ABS(saldo_inicial) as mes_anterior,
                        ABS(saldo_final) - ABS(saldo_inicial) importe,
                        CASE WHEN (saldo_inicial = 0) THEN ((ABS(saldo_final) - ABS(saldo_inicial)) * 100) ELSE ((ABS(saldo_final) - ABS(saldo_inicial))/ABS(saldo_final)) * 100 END porcentaje
                        FROM v_balanza
                        WHERE periodo = %s
                        AND anio = '%s'
                        AND account_id in (
                            '333',
                            '338',
                            '356',
                            '472',
                            '558',
                            '684'
                        )
                    """ % (self.periodo, self.anio_fiscal))
                rows_sql = self.env.cr.dictfetchall()
                ids=[]
                for i in rows_sql:
                    query_r = {
                        'account_id': i['account_id'],
                        'code': i['code'],
                        'periodo': i['periodo'],
                        'anio': i['anio'],
                        'mes_consulta': i['mes_consulta'],
                        'mes_anterior': i['mes_anterior'],
                        'importe': i['importe'],
                        'porcentaje': i['porcentaje']
                    }
                    ids.append(query_r)
    
                datas['query_estado'] = ids            
            if self.periodo and self.anio_fiscal:
                if(self.anio_fiscal==2019):
                    self.env.cr.execute("""
                    select
                        id,
                        coalesce (cuenta,
                        0) as cuenta ,
                        importe,
                        cuenta_str,
                        anio
                    from
                        tjacdmx_contabilidad_saldos_anuales
                    where
                        id_reporte = 21
                        and anio = %s
                        and cuenta in (
                        '333',
                        '338',
                        '356',
                        '472',
                        '558',
                        '684') order by cuenta;
                    """ % (self.anio_fiscal-1))
                    rows_sql_dic = self.env.cr.dictfetchall()
                    ids_dic=[]
                    for i in rows_sql_dic:
                        query_r_dic = {
                            'id': i['id'],
                            'cuenta': i['cuenta'],
                            'importe': i['importe'],
                            'cuenta_str': i['cuenta_str']
                        }
                        ids_dic.append(query_r_dic)
                    datas['dic'] = ids_dic
                else:
                    self.env.cr.execute("""
                        SELECT 
                        account_id,
                        code,
                        periodo,
                        anio,
                        ABS(saldo_final)as mes_consulta,
                        ABS(saldo_inicial) as mes_anterior,
                        ABS(saldo_final) - ABS(saldo_inicial) importe,
                        CASE WHEN (saldo_inicial = 0) THEN ((ABS(saldo_final) - ABS(saldo_inicial)) * 100) ELSE ((ABS(saldo_final) - ABS(saldo_inicial))/ABS(saldo_final)) * 100 END porcentaje
                        FROM v_balanza
                        WHERE periodo = 12
                        AND anio = '%s'
                        AND account_id in (
                            '333',
                            '338',
                            '356',
                            '472',
                            '558',
                            '684'
                        )
                    """ % (self.anio_fiscal-1))
                    rows_sql_dic = self.env.cr.dictfetchall()
                    ids_dic=[]
                    for i in rows_sql_dic:
                        query_r_dic = {
                            'id': i['account_id'],
                            'cuenta': i['account_id'],
                            'importe': i['mes_consulta']
                        }
                        ids_dic.append(query_r_dic)
                    datas['dic'] = ids_dic

            datas['form'] = res
            return self.env['report'].get_action([], 'reportes.estado_actividades_v3', data=datas)
        if self.reporte_select.no_reporte == 3:
            datas = {}
            if self.periodo and self.anio_fiscal:
                self.env.cr.execute("""
                        WITH saldos_anterior AS (
                        select
                                b.saldo_final,
                                b.account_id
                            from
                                v_balanza b
                            where periodo = 12
                                and anio = '%s'
                        )
                        select
                             a.account_id,
                            a.code,
                            a.periodo,
                            a.anio,
                            (a.saldo_final)as mes_consulta,
                            (b.saldo_final) as mes_anterior,
                            (a.saldo_final) - ((b.saldo_final)) as importe,
                            (b.saldo_final) - (a.saldo_final) as origen
                        from
                            v_balanza a
                        join saldos_anterior b on
						b.account_id = a.account_id
                        where
                            a.periodo = %s
                            and a.anio = '%s'
                            and a.account_id in ('37','61','108','126','170','185','277','312','275','280','163','291','320','333','338','356','472','558','684','186','226','253','275','277','283','291','312','318','2635');  
                    """ % (int(self.anio_fiscal)-1,self.periodo, self.anio_fiscal))
                rows_sql = self.env.cr.dictfetchall()
                ids=[]
                for i in rows_sql:
                    query_r = {
                        'account_id': i['account_id'],
                        'code': i['code'],
                        'periodo': i['periodo'],
                        'anio': i['anio'],
                        'mes_consulta': i['mes_consulta'],
                        'mes_anterior': i['mes_anterior'],
                        'importe': i['importe'],
                        'origen': i['origen'],
                    }
                    ids.append(query_r)
                # raise ValidationError("debug: %s"  % (ids))

                sql_pasivo="""SELECT code,account_id,ABS(saldo_inicial) AS saldo_inicial,ABS(saldo_final) AS saldo_final  FROM v_balanza WHERE anio='%s' AND periodo=%s AND account_id in (186,226,253,275,277,283,291,312,318,2635)"""
                self.env.cr.execute(sql_pasivo % (self.anio_fiscal,self.periodo))
                row_pasivo = self.env.cr.dictfetchall()
                sql_pasivo_before="""SELECT code,account_id,ABS(saldo_inicial) AS saldo_inicial,ABS(saldo_final) AS saldo_final  FROM v_balanza WHERE anio='%s' AND periodo=12 AND account_id in (186,226,253,275,277,283,291,312,318,2635)"""
                self.env.cr.execute(sql_pasivo_before % (int(self.anio_fiscal)-1))
                row_pasivo_before = self.env.cr.dictfetchall()
                sql_pasivo_ahorro="""SELECT code,account_id,ABS(saldo_inicial) AS saldo_inicial,ABS(saldo_final) AS saldo_final  FROM v_balanza WHERE anio='%s' AND periodo=%s AND account_id in ('333','338','356','472','558','684')"""
                self.env.cr.execute(sql_pasivo_ahorro % (self.anio_fiscal,self.periodo))
                row_pasivo_ahorro = self.env.cr.dictfetchall()
                sql_pasivo_ahorro_before="""SELECT code,account_id,ABS(saldo_inicial) AS saldo_inicial,ABS(saldo_final) AS saldo_final  FROM v_balanza WHERE anio='%s' AND periodo=12 AND account_id in ('333','338','356','472','558','684')"""
                self.env.cr.execute(sql_pasivo_ahorro_before % (self.anio_fiscal-1))
                row_pasivo_ahorro_before = self.env.cr.dictfetchall()
                suma_a=row_pasivo_ahorro[0]['saldo_final']+ row_pasivo_ahorro[1]['saldo_final']
                suma_a_inicial=row_pasivo_ahorro_before[0]['saldo_final']+ row_pasivo_ahorro_before[1]['saldo_final']
                suma_b=row_pasivo_ahorro[2]['saldo_final']+ row_pasivo_ahorro[3]['saldo_final']+ row_pasivo_ahorro[4]['saldo_final']+ row_pasivo_ahorro[5]['saldo_final']
                suma_b_inicial=row_pasivo_ahorro_before[2]['saldo_final']+ row_pasivo_ahorro_before[3]['saldo_final']+ row_pasivo_ahorro_before[4]['saldo_final']+ row_pasivo_ahorro_before[5]['saldo_final']
                suma_re=suma_a-suma_b
                suma_re_saldo=suma_a_inicial-suma_b_inicial
                datas['resultado_del_ejerci_saldo']= suma_re
                datas['resultado_del_ejerci_saldo_inicial']= suma_re_saldo
                datas['query_estado'] = ids
                datas['form_data'] = {
                        'anio': int(self.anio_fiscal),
                        'anio_anterior': int(self.anio_fiscal)-1,
                        'periodo': self.periodo,
                        'periodo_anterior': 12 }
            return self.env['report'].get_action([], 'reportes.report_estado_cambios_situacion_financierav2', data=datas)
        elif self.reporte_select.no_reporte == 4:
            datas = {}
            sql="""
            select account_id,saldo_final from v_balanza where account_id=277 and periodo=%s and anio='%s'"""
            self.env.cr.execute(sql % (self.periodo,self.anio_fiscal))
            row_sql = self.env.cr.dictfetchall()
            cantidad = abs(row_sql[0]['saldo_final'])
            cantidad = '{0:.2f}'.format(float(cantidad))
            importe = cantidad.split('.')[0]
            centavos = cantidad.split('.')[1]
            importe = (num2words(importe, lang='es').split(' punto ')[0])
            moneda = ' pesos '
            leyenda = '/100 m.n.'.upper()
            total_letra = importe + moneda + centavos + leyenda
            datas['cantidad']=float(cantidad)
            datas['total_letra']=total_letra
            datas['anio_fiscal']= self.anio_fiscal
            datas['periodo_fiscal']= self.periodo
            return self.env['report'].get_action([], 'reportes.report_v2_pasivos_contingentes', data=datas)
        elif self.reporte_select.no_reporte == 5:
            datas = {}
            datas['anio_fiscal']= self.anio_fiscal
            datas['periodo_fiscal']= self.periodo
            #####pasivo circulante#####
            if(self.anio_fiscal==2019):
                sql_pasivo="""SELECT code,account_id,ABS(saldo_inicial) AS saldo_inicial,ABS(saldo_final) AS saldo_final  FROM v_balanza WHERE anio='%s' AND periodo=%s AND account_id in (186,226,253,275,277,283,291,312,318,2635)"""
                self.env.cr.execute(sql_pasivo % (self.anio_fiscal,self.periodo))
                row_pasivo = self.env.cr.dictfetchall()

                sql_pasivo_si_before="""SELECT * FROM tjacdmx_contabilidad_saldos_anuales WHERE id_reporte=24 AND cuenta in (183) AND anio='%s';"""
                self.env.cr.execute(sql_pasivo_si_before % (self.anio_fiscal-1))
                row_pasivopasivo_si_before = self.env.cr.dictfetchall()

                suma_cuenta_pagar= row_pasivo[0]['saldo_final']+row_pasivo[1]['saldo_final']+row_pasivo[2]['saldo_final']+row_pasivo[3]['saldo_final']+row_pasivo[4]['saldo_final']
                suma_cuenta_pagar_si= row_pasivopasivo_si_before[0]['importe']
                
                suma_pasivo_no_cir=row_pasivo[5]['saldo_final']
                suma_pasivo_no_cir_si=0
                datas['suma_pasivo_no_cir']= suma_pasivo_no_cir
                datas['suma_pasivo_no_cir_si']= suma_pasivo_no_cir_si
                suma_pasivos=suma_cuenta_pagar+suma_pasivo_no_cir
                suma_pasivos_si=suma_cuenta_pagar_si+suma_pasivo_no_cir_si
                datas['suma_pasivos']= suma_cuenta_pagar+suma_pasivo_no_cir
                datas['suma_pasivos_si']= suma_cuenta_pagar_si+suma_pasivo_no_cir_si
                
            else:
                sql_pasivo="""WITH saldos_anterior AS (
                            SELECT
                                    b.saldo_final,
                                    b.account_id
                                from
                                    v_balanza b
                                where periodo = 12
                                    and anio = '%s'
                            )
                            SELECT
                                a.code,
                                a.account_id,
                                ABS((select saldo_final from saldos_anterior where account_id=a.account_id)) as saldo_inicial,
                                ABS(a.saldo_final) as saldo_final
                            from
                                v_balanza a
                            where
                                a.anio = '%s'
                                and a.periodo =%s
                                and a.account_id in (186, 226, 253, 275, 277, 283, 291, 312, 318, 2635)"""
                self.env.cr.execute(sql_pasivo % (int(self.anio_fiscal)-1,self.anio_fiscal,self.periodo))
                row_pasivo = self.env.cr.dictfetchall()

                sql_pasivo_si_before="""SELECT code,account_id,ABS(saldo_inicial) AS saldo_inicial,ABS(saldo_final) AS saldo_final  FROM v_balanza WHERE anio='%s' AND periodo=12 AND account_id in (186,226,253,275,277,283,291,312,318,2635)"""
                self.env.cr.execute(sql_pasivo_si_before % (self.anio_fiscal-1))
                row_pasivopasivo_si_before = self.env.cr.dictfetchall()
            
                suma_cuenta_pagar= row_pasivo[0]['saldo_final']+row_pasivo[1]['saldo_final']+row_pasivo[2]['saldo_final']+row_pasivo[3]['saldo_final']+row_pasivo[4]['saldo_final']
                suma_cuenta_pagar_si= row_pasivo[0]['saldo_inicial']+row_pasivo[1]['saldo_inicial']+row_pasivo[2]['saldo_inicial']+row_pasivo[3]['saldo_inicial']+row_pasivo[4]['saldo_inicial']
                ####pasivo no circulante
                suma_pasivo_no_cir=row_pasivo[5]['saldo_final']
                suma_pasivo_no_cir_si=row_pasivo[5]['saldo_inicial']
                datas['suma_pasivo_no_cir']= suma_pasivo_no_cir
                datas['suma_pasivo_no_cir_si']= suma_pasivo_no_cir_si
                suma_pasivos=suma_cuenta_pagar+suma_pasivo_no_cir
                suma_pasivos_si=suma_cuenta_pagar_si+suma_pasivo_no_cir_si
                datas['suma_pasivos']= suma_cuenta_pagar+suma_pasivo_no_cir
                datas['suma_pasivos_si']= suma_cuenta_pagar_si+suma_pasivo_no_cir_si

            return self.env['report'].get_action([], 'reportes.report_v2_esta_deuda_pasivos', data=datas)
        elif self.reporte_select.no_reporte == 6:
            datas = {}
            res = self.read(['periodo','anio_fiscal'])
            res = res and res[0] or {}
            if self.periodo and self.anio_fiscal:
                sql_activo_circulante_banco="""SELECT code,account_id,sum(debe) AS debe, sum(haber) AS haber  FROM v_balanza 
                                                WHERE anio='%s' AND periodo between 1 and %s AND account_id in (45) group by 1,2;"""
                self.env.cr.execute(sql_activo_circulante_banco % (self.anio_fiscal,self.periodo))
                row_activo_efectivo_banco = self.env.cr.dictfetchall()
                sql_activo = """with saldos_anterior as (
                                select
                                    b.saldo_final,
                                    b.account_id
                                from
                                    v_balanza b
                                where
                                    periodo = 12
                                    and anio = '%s' )
                                select
                                    a.code,
                                    a.account_id,
                                    (b.saldo_final) saldo_inicial,
                                    sum(a.debe) as debe,
                                    sum(a.haber) as haber,
                                    (b.saldo_final)+sum(a.debe)-sum(a.haber) saldo_final 
                                from
                                    v_balanza a
                                join saldos_anterior b on b.account_id = a.account_id
                                where
                                    a.anio = '%s'
                                    and a.periodo between 1 and %s
                                    and a.account_id in (35, 36, 37, 38, 45, 52, 58, 61, 62, 72, 98, 108, 116, 117, 118, 126, 127, 137, 143, 147, 151, 161, 163, 164, 166, 170)
                                group by 1,2,3;"""
                self.env.cr.execute(sql_activo % (self.anio_fiscal-1,self.anio_fiscal,self.periodo))
                rows_sql = self.env.cr.dictfetchall()
                ids=[]
                for i in rows_sql:
                    query_r = {
                        'account_id': i['account_id'],
                        'code': i['code'],
                        'saldo_inicial': i['saldo_inicial'],
                        'saldo_final':i['saldo_final'],
                        'debe': i['debe'],
                        'haber': i['haber']
                    }
                    ids.append(query_r)
            datas['query_estado'] = ids
            datas['form'] = res
            return self.env['report'].get_action([], 'reportes.report_v2_estado_analitico_activov2', data=datas)
        # Reporte Financiero - Estado de Variaciones en la Hacienda Publica / Patrimonio
        elif self.reporte_select.no_reporte == 7:
            datas = {}
            res = self.read(['periodo','anio_fiscal'])
            res = res and res[0] or {}
            if self.periodo and self.anio_fiscal:
                if(self.anio_fiscal==2019):
                    sql_pasivo="""SELECT code,account_id,ABS(saldo_inicial) AS saldo_inicial,ABS(saldo_final) AS saldo_final,(saldo_final)-(saldo_final) importe  FROM v_balanza WHERE anio='%s' AND periodo=%s AND account_id in (291,312,318,2635,333,338,356,472,558,684)"""
                    self.env.cr.execute(sql_pasivo % (self.anio_fiscal,self.periodo))
                    rows_sql = self.env.cr.dictfetchall()
                    ids=[]
                    for i in rows_sql:
                        query_r = {
                            'account_id': i['account_id'],
                            'code': i['code'],
                            'saldo_inicial': i['saldo_inicial'],
                            'saldo_final': i['saldo_final'],
                            'importe': i['importe']
                        }
                        ids.append(query_r)
                else:
                    sql_pasivo="""with saldos_anterior as (
                                select
                                    b.saldo_final,
                                    b.account_id
                                from
                                    v_balanza b
                                where
                                    periodo = 12
                                    and anio = '%s' )
                                select
                                    a.code,
                                    a.account_id,
                                    ABS(b.saldo_final) as saldo_inicial,
                                    ABS(a.saldo_final) as saldo_final,
                                    (b.saldo_final)-(a.saldo_final) importe
                                from
                                    v_balanza a
                                join saldos_anterior b on b.account_id = a.account_id
                                where
                                    a.anio = '%s'
                                    and a.periodo = %s
                                    and a.account_id in (291, 312, 318, 2635, 333, 338, 356, 472, 558, 684,186,226,253,275,277,283);"""
                    self.env.cr.execute(sql_pasivo % (int(self.anio_fiscal)-1,self.anio_fiscal,self.periodo))
                    rows_sql = self.env.cr.dictfetchall()
                    ids=[]
                    for i in rows_sql:
                        query_r = {
                            'account_id': i['account_id'],
                            'code': i['code'],
                            'saldo_inicial': i['saldo_inicial'],
                            'saldo_final': i['saldo_final'],
                            'importe': i['importe']
                        }
                        ids.append(query_r)
                if (self.anio_fiscal==2019):
                    sql_pasivo_before="""SELECT acc.code,csa.cuenta as account_id,csa.importe as saldo_final FROM tjacdmx_contabilidad_saldos_anuales csa
                                        inner join account_account acc on acc.id=csa.cuenta
                                        WHERE id_reporte=31 and anio='%s' and cuenta in (186,226,253,275,277,283,291,312,318,2635)
                                        order by acc.code asc;"""
                    self.env.cr.execute(sql_pasivo_before % (int(self.anio_fiscal)-1))
                    row_pasivo_before = self.env.cr.dictfetchall()

                    sql_pasivo="""SELECT code,account_id,ABS(saldo_final) AS saldo_final  FROM v_balanza WHERE anio='%s' AND periodo=%s AND account_id in (186,226,253,275,277,283,291,312,318,2635);"""
                    self.env.cr.execute(sql_pasivo % (self.anio_fiscal,self.periodo))
                    row_pasivo = self.env.cr.dictfetchall()
                else:
                    sql_pasivo="""SELECT code,account_id,ABS(saldo_inicial) AS saldo_inicial,ABS(saldo_final) AS saldo_final  FROM v_balanza WHERE anio='%s' AND periodo=%s AND account_id in (186,226,253,275,277,283,291,312,318,2635)"""
                    self.env.cr.execute(sql_pasivo % (self.anio_fiscal,self.periodo))
                    row_pasivo = self.env.cr.dictfetchall()

                    sql_pasivo_before="""SELECT code,account_id,ABS(saldo_inicial) AS saldo_inicial,ABS(saldo_final) AS saldo_final  FROM v_balanza WHERE anio='%s' AND periodo=12 AND account_id in (186,226,253,275,277,283,291,312,318,2635)"""
                    self.env.cr.execute(sql_pasivo_before % (int(self.anio_fiscal)-1))
                    row_pasivo_before = self.env.cr.dictfetchall()
                if(self.anio_fiscal==2019):
                    sql_pasivo_ahorro="""SELECT code,account_id,ABS(saldo_inicial) AS saldo_inicial,ABS(saldo_final) AS saldo_final  FROM v_balanza WHERE anio='%s' AND periodo=%s AND account_id in ('333','338','356','472','558','684')"""
                    self.env.cr.execute(sql_pasivo_ahorro % (self.anio_fiscal,self.periodo))
                    row_pasivo_ahorro = self.env.cr.dictfetchall()
                    suma_a=row_pasivo_ahorro[0]['saldo_final']+ row_pasivo_ahorro[1]['saldo_final']
                    suma_a_inicial=row_pasivo_ahorro[0]['saldo_inicial']+ row_pasivo_ahorro[1]['saldo_inicial']
                    suma_b=row_pasivo_ahorro[2]['saldo_final']+ row_pasivo_ahorro[3]['saldo_final']+ row_pasivo_ahorro[4]['saldo_final']+ row_pasivo_ahorro[5]['saldo_final']
                    suma_b_inicial=row_pasivo_ahorro[2]['saldo_inicial']+ row_pasivo_ahorro[3]['saldo_inicial']+ row_pasivo_ahorro[4]['saldo_inicial']+ row_pasivo_ahorro[5]['saldo_inicial']
                else:
                    sql_pasivo_ahorro="""SELECT code,account_id,ABS(saldo_inicial) AS saldo_inicial,ABS(saldo_final) AS saldo_final  FROM v_balanza WHERE anio='%s' AND periodo=%s AND account_id in ('333','338','356','472','558','684')"""
                    self.env.cr.execute(sql_pasivo_ahorro % (self.anio_fiscal,self.periodo))
                    row_pasivo_ahorro = self.env.cr.dictfetchall()

                    sql_pasivo_ahorro_before="""SELECT code,account_id,ABS(saldo_inicial) AS saldo_inicial,ABS(saldo_final) AS saldo_final  FROM v_balanza WHERE anio='%s' AND periodo=12 AND account_id in ('333','338','356','472','558','684')"""
                    self.env.cr.execute(sql_pasivo_ahorro_before % (self.anio_fiscal-1))
                    row_pasivo_ahorro_before = self.env.cr.dictfetchall()
                    suma_a=row_pasivo_ahorro[0]['saldo_final']+ row_pasivo_ahorro[1]['saldo_final']
                    suma_a_inicial=row_pasivo_ahorro_before[0]['saldo_final']+ row_pasivo_ahorro_before[1]['saldo_final']
                    suma_b=row_pasivo_ahorro[2]['saldo_final']+ row_pasivo_ahorro[3]['saldo_final']+ row_pasivo_ahorro[4]['saldo_final']+ row_pasivo_ahorro[5]['saldo_final']
                    suma_b_inicial=row_pasivo_ahorro_before[2]['saldo_final']+ row_pasivo_ahorro_before[3]['saldo_final']+ row_pasivo_ahorro_before[4]['saldo_final']+ row_pasivo_ahorro_before[5]['saldo_final']

                suma_re=suma_a-suma_b
                suma_re_saldo=suma_a_inicial-suma_b_inicial
                datas['suma_resultado_ejercicio']= suma_re
                datas['suma_resultado_ejercicio_si']=suma_re_saldo
                ###
                datas['resultado_del_ejerci_saldo']= suma_re
                if(self.anio_fiscal==2019):
                    datas['resultado_del_ejerci_saldo_inicial']= row_pasivo_before[8]['saldo_final']
                else:
                    datas['resultado_del_ejerci_saldo_inicial']= suma_re_saldo
                datas['resultado_ejer_anteriores']= row_pasivo[9]['saldo_final']*-1
                datas['resultado_ejer_anteriores_inicial']= row_pasivo_before[9]['saldo_final']*-1
                

            datas['query_estado'] = ids
            datas['form'] = res
            #
            return self.env['report'].get_action([], 'reportes.estado_variaciones_hpv2', data=datas)
        elif self.reporte_select.no_reporte == 8:
            periodo_anterior=self.periodo
            datas = {}
            datas['anio_fiscal']= self.anio_fiscal
            datas['periodo_fiscal']= self.periodo
            datas['anio_fiscal_anterior']= self.anio_fiscal-1
            cuantas="""with saldos_anterior as (
                        select
                            b.saldo_final,
                            b.account_id
                        from
                            v_balanza b
                        where
                            periodo = 12
                            and anio = '%s' )
                        select
                            a.account_id,
                            '' suma,
                            (a.saldo_final) as saldo,
                            (b.saldo_final) saldo_anterior,
                            (a.saldo_final-b.saldo_final) saldo_total
                        from
                            v_balanza a
                        join saldos_anterior b on b.account_id = a.account_id
                        where
                            a.anio = '%s'
                            and a.periodo =%s
                            and a.account_id in (334, 338, 356, 472, 558, 290, 108, 312, 185, 291,62,72,98,108,186,226,253,275,277,283,38,45,52,126);"""
            self.env.cr.execute(cuantas % (self.anio_fiscal-1,self.anio_fiscal,self.periodo))
            row_cuentas = self.env.cr.dictfetchall()
            cuantas_bmoa="""(with saldos_anterior_ampli as (
                                select
                                    b.account_id,
                                    sum(b.debe-b.haber) saldo
                                from
                                    v_balanza b
                                where
                                    b.anio = '%s'
                                    and b.periodo between 1 and 12
                                group by 1)
                                select
                                    a.account_id,
                                    'bienes_muebles_ampliacion' suma,
                                    sum(a.debe-haber) saldo,
                                    ((b.saldo)) saldo_anterior,
                                    0 saldo_total
                                from
                                    v_balanza a
                                join saldos_anterior_ampli b on b.account_id = a.account_id
                                where
                                    a.anio = '%s'
                                    and a.periodo between 1 and %s
                                    and a.account_id = 126 group by 1,4
                                )union
                                (
                                with saldos_anterior as (
                                select
                                    b.account_id,
                                    sum(b.debe) saldo
                                from
                                    v_balanza b
                                where
                                    b.anio = '%s'
                                    and b.periodo between 1 and 12
                                group by 1)
                                select
                                    a.account_id,
                                    'bienes_muebles_origen' suma,
                                    sum(a.debe-haber) saldo,
                                    ((b.saldo)) saldo_anterior,
                                    0 saldo_total
                                from
                                    v_balanza a
                                join saldos_anterior b on b.account_id = a.account_id
                                where
                                    a.anio = '%s'
                                    and a.periodo between 1 and %s
                                    and a.account_id = 126 group by 1,4)"""
            self.env.cr.execute(cuantas_bmoa % (self.anio_fiscal-1,self.anio_fiscal,self.periodo,self.anio_fiscal-1,self.anio_fiscal,self.periodo))
            row_bmoa = self.env.cr.dictfetchall()
            cuantas_feao="""(with saldos_anterior as (
                            select
                                b.saldo_final,
                                (b.saldo_inicial) saldo_inicial,
                                b.account_id
                            from
                                v_balanza b
                            where
                                periodo = 12
                                and anio = '%s' )
                            select
                                ( CASE WHEN (sum(b.saldo_final-a.saldo_final)>0 ) THEN 'flujos_efectivo_origen' ELSE 'flujos_efectivo_aplicacion' END ) tipo,
                                sum(b.saldo_final-a.saldo_final) saldo_inicial
                            from
                                v_balanza a
                            join saldos_anterior b on
                                b.account_id = a.account_id
                            where
                                a.anio = '%s'
                                and a.periodo = %s
                                and a.account_id in (62, 72, 98, 108)) 
                        union ( with saldos_anterior as (
                            select
                                b.saldo_final,
                                (b.saldo_inicial) saldo_inicial,
                                b.account_id
                            from
                                v_balanza b
                            where
                                periodo = 12
                                and anio = '%s' )
                            select
                                ( CASE WHEN (sum(b.saldo_final-a.saldo_final)>0 ) THEN 'flujos_efectivo_origen' ELSE 'flujos_efectivo_aplicacion' END ) tipo,
                                sum(b.saldo_final-a.saldo_final) saldo_inicial
                            from
                                v_balanza a
                            join saldos_anterior b on
                                b.account_id = a.account_id
                            where
                                a.anio = '%s'
                                and a.periodo = %s
                                and a.account_id in (186, 226, 253, 275, 277, 283))"""
            self.env.cr.execute(cuantas_feao % (self.anio_fiscal-1,self.anio_fiscal,self.periodo,self.anio_fiscal-1,self.anio_fiscal,self.periodo))
            row_feao = self.env.cr.dictfetchall()
            cuantas_deudas="""select 'aplicaciones_financiamiento' tipo,
                            (with saldos_anterior as (
                            select
                                b.saldo_final,
                                (b.saldo_inicial) saldo_inicial,
                                b.account_id
                            from
                                v_balanza b
                            where
                                periodo = 12
                                and anio = '%s' )
                            select
                                sum(b.saldo_final-a.saldo_final) saldo_inicial
                            from
                                v_balanza a
                            join saldos_anterior b on
                                b.account_id = a.account_id
                            where
                                a.anio = '%s'
                                and a.periodo = 12
                                and a.account_id in (62, 72, 98, 108)) +( with saldos_anterior as (
                            select
                                b.saldo_final,
                                (b.saldo_inicial) saldo_inicial,
                                b.account_id
                            from
                                v_balanza b
                            where
                                periodo = 12
                                and anio = '%s' )
                            select
                                sum(b.saldo_final-a.saldo_final) saldo_inicial
                            from
                                v_balanza a
                            join saldos_anterior b on
                                b.account_id = a.account_id
                            where
                                a.anio = '%s'
                                and a.periodo = 12
                                and a.account_id in (186, 226, 253, 275, 277, 283)) as saldo_inicial;"""
            self.env.cr.execute(cuantas_deudas % (self.anio_fiscal-2,self.anio_fiscal-1,self.anio_fiscal-2,self.anio_fiscal-1))
            row_deudas = self.env.cr.dictfetchall()
            cuantas_anio_anterior="""select
                                'efectivo_equivalente_2' tipo,
                                saldo_final as saldo_inicial
                                from
                                    v_balanza
                                where
                                    anio = '%s'
                                    and periodo = 12
                                    and account_id = 37;"""
            self.env.cr.execute(cuantas_anio_anterior % (self.anio_fiscal-2))
            row_cuantas_anio_anterior = self.env.cr.dictfetchall()
            otras_inversiones="""with saldos_anterior as (
                                select
                                    b.debe saldo_anterior,
                                    b.account_id
                                from
                                    v_balanza b
                                where
                                    periodo between 1 and 12
                                    and anio = '%s' )
                            select
                                'otras_inversiones' tipo,
                                SUM((a.debe)) as saldo,
                                SUM((b.saldo_anterior)) as saldo_inicial
                            from
                                v_balanza a
                            join saldos_anterior b on
                                    b.account_id = a.account_id
                            where
                                a.anio = '%s'
                                and a.periodo = %s
                                and a.account_id in (289);"""
            self.env.cr.execute(otras_inversiones % (self.anio_fiscal-1,self.anio_fiscal,self.periodo))
            row_otras_inversiones = self.env.cr.dictfetchall()
            saldos=[]
            saldos_flujos=[]
            for i in row_cuentas:
                query_r = {
                    'cuenta': i['account_id'],
                    'suma': i['suma'],
                    'saldo': i['saldo'],
                    'saldo_anterior': i['saldo_anterior'],
                    'saldo_total': i['saldo_total']
                }
                saldos.append(query_r)
            for i in row_bmoa:
                query_r = {
                    'cuenta': i['account_id'],
                    'suma': i['suma'],
                    'saldo': i['saldo'],
                    'saldo_anterior': i['saldo_anterior'],
                    'saldo_total': i['saldo_total']
                }
                saldos.append(query_r)
            for i in row_feao:
                query_r = {
                    'tipo': i['tipo'],
                    'saldo': i['saldo_inicial'],
                    'saldo_anterior':0,
                    'saldo_total': 0
                }
                saldos_flujos.append(query_r)
            for i in row_deudas:
                query_r = {
                    'tipo': i['tipo'],
                    'saldo': 0,
                    'saldo_anterior': i['saldo_inicial'],
                    'saldo_total': 0
                }
                saldos_flujos.append(query_r)
            for i in row_cuantas_anio_anterior:
                query_r = {
                    'tipo': i['tipo'],
                    'saldo': 0,
                    'saldo_anterior': i['saldo_inicial'],
                    'saldo_total': 0
                }
                saldos_flujos.append(query_r)
            for i in row_otras_inversiones:
                query_r = {
                    'tipo': i['tipo'],
                    'saldo': i['saldo'],
                    'saldo_anterior': i['saldo_inicial'],
                    'saldo_total': 0
                }
                saldos_flujos.append(query_r)
            datas['saldos']= saldos
            datas['saldos_flujos']= saldos_flujos
            #raise ValidationError("debug: %s -----%s"  % (saldos,saldos_flujos))
            return self.env['report'].get_action([], 'reportes.report_v2_estado_flujos_efectivov2', data=datas)
        elif self.reporte_select.no_reporte == 9:
            datas={}
        elif self.reporte_select.no_reporte == 10:
            datas={}
            sql_activo_circulante="""
            with saldos_anterior as (
            select
                b.saldo_final,
                b.account_id
            from
                v_balanza b
            where
                periodo = 12
                and anio = '%s' )
            select
                a.code,
                a.account_id,
                ABS(b.saldo_final) as saldo_inicial,
                ABS(a.saldo_final) as saldo_final
            from
                v_balanza a
            join saldos_anterior b on b.account_id = a.account_id
            where
                a.anio = '%s'
                and a.periodo =%s
                and a.account_id in (38, 45, 52, 62, 72, 98, 105, 108, 127, 137, 143, 147, 151, 161, 164, 167, 170, 186, 226, 253, 275, 277, 283, 291, 312, 318, 2635, 333, 338, 356, 472, 558, 684)
            order by
                code asc;"""
            self.env.cr.execute(sql_activo_circulante % (self.anio_fiscal-1,self.anio_fiscal,self.periodo))
            row_activo_efectivo = self.env.cr.dictfetchall()
            ids=[]
            for i in row_activo_efectivo:
                query_r = {
                    'account_id': i['account_id'],
                    'code': i['code'],
                    'saldo_inicial': i['saldo_inicial'],
                    'saldo_final':i['saldo_final'],
                }
                ids.append(query_r)
            datas['query_estado'] = ids
            datas['anio_fiscal']= self.anio_fiscal
            datas['periodo_fiscal']= self.periodo
            return self.env['report'].get_action([], 'reportes.report_sfv2', data=datas)