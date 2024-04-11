from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import ValidationError,UserError
from odoo.tools.translate import _
from num2words import num2words

PERIODO_SELECT = [(periodo, periodo) for periodo in range(1,13)]
EJERCICIO_SELECT = [ (year, year) for year in range(2019, 2031)]

class wizard_estado_actividades(models.TransientModel):
    _name='tjacdmx_wizard_estado_actividades'
    _description='Wizard Estado de Actividades'
    
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
    

    def _select(self):
        select_str ="""
            SELECT 
                account_id,
                code,
                periodo,
                anio,
                ABS(saldo_final)as mes_consulta,
                ABS(saldo_inicial) as mes_anterior,
                ABS(saldo_final) - ABS(saldo_inicial) importe,
				(ABS(saldo_final) - ABS(saldo_inicial))/ABS(saldo_inicial) * 100 porcentaje
        """
        return select_str
    def _select_sf(self):
        select_str ="""
            SELECT 
                account_id,
                code,
                periodo,
                anio,
                ABS(saldo_final)as saldo_inicial,
                ABS(saldo_inicial) as saldo_final,
                ABS(saldo_final) - ABS(saldo_inicial) importe,
				(ABS(saldo_final) - ABS(saldo_inicial))/ABS(saldo_inicial) * 100 porcentaje
        """
        return select_str

    @api.multi
    def action_estado_actividades(self, values):
        if self.reporte_select.no_reporte == 1:
            datas={}
            arr_activo=[]
            #####activo circulante#####
            
            sql_activo_circulante="""SELECT code,account_id,ABS(saldo_inicial) AS saldo_inicial,ABS(saldo_final) AS saldo_final  FROM v_balanza WHERE anio='%s' AND periodo=%s AND account_id in (38,45,52,62,72,98,105,108,127,137,143,147,151,161,164,167,170)  order by code asc"""
            self.env.cr.execute(sql_activo_circulante % (self.anio_fiscal,self.periodo))
            row_activo_efectivo = self.env.cr.dictfetchall()
            sql_activo_circulante_banco="""SELECT code,account_id,saldo_inicial AS saldo_inicial,saldo_final AS saldo_final  FROM v_balanza WHERE anio='%s' AND periodo=%s AND account_id in (45,52)  order by code asc"""
            self.env.cr.execute(sql_activo_circulante_banco % (self.anio_fiscal,self.periodo))
            row_activo_efectivo_banco = self.env.cr.dictfetchall()
            
            datas['efectivo_saldo']= row_activo_efectivo[0]['saldo_final']
            datas['efectivo_saldo_inicial']= row_activo_efectivo[0]['saldo_inicial']
            datas['bancos_tesoreria_saldo']= row_activo_efectivo_banco[0]['saldo_final']
            datas['bancos_tesoreria_saldo_inicial']= row_activo_efectivo_banco[0]['saldo_inicial']
            datas['inversiones_tesoreria_saldo']= row_activo_efectivo_banco[1]['saldo_final']
            datas['inversiones_tesoreria_saldo_inicial']= row_activo_efectivo[2]['saldo_inicial']
            suma_efectivo_bancos= row_activo_efectivo[0]['saldo_final']+row_activo_efectivo_banco[0]['saldo_final']+row_activo_efectivo[2]['saldo_final']
            suma_efectivo_bancos_si= row_activo_efectivo[0]['saldo_inicial']+row_activo_efectivo_banco[0]['saldo_inicial']+row_activo_efectivo[2]['saldo_inicial']
            datas['suma_efectivo_bancos']= suma_efectivo_bancos
            datas['suma_efectivo_bancos_si']= suma_efectivo_bancos_si
            ####
            datas['cuentas_pccp_saldo']= row_activo_efectivo[3]['saldo_final']
            datas['cuentas_pccp_saldo_inicial']= row_activo_efectivo[3]['saldo_inicial']
            datas['deudores_diversos_saldo']= row_activo_efectivo[4]['saldo_final']
            datas['deudores_diversos_saldo_inicial']= row_activo_efectivo[4]['saldo_inicial']
            datas['ingreso_recuperar_cp_saldo']= row_activo_efectivo[5]['saldo_final']
            datas['ingreso_recuperar_cp_saldo_inicial']= row_activo_efectivo[5]['saldo_inicial']
            suma_derechos_recibir= row_activo_efectivo[3]['saldo_final']+row_activo_efectivo[4]['saldo_final']+row_activo_efectivo[5]['saldo_final']
            suma_derechos_recibir_si= row_activo_efectivo[3]['saldo_inicial']+row_activo_efectivo[4]['saldo_inicial']+row_activo_efectivo[5]['saldo_inicial']
            datas['suma_derechos_recibir']= suma_derechos_recibir
            datas['suma_derechos_recibir_si']=suma_derechos_recibir_si
            ####
            datas['inventario_saldo']= row_activo_efectivo[6]['saldo_final']
            datas['inventario_saldo_inicial']= row_activo_efectivo[6]['saldo_inicial']
            datas['almacen_saldo']= row_activo_efectivo[7]['saldo_final']
            datas['almacen_saldo_inicial']= row_activo_efectivo[7]['saldo_inicial']
            suma_activos_inventario= row_activo_efectivo[6]['saldo_final']+row_activo_efectivo[7]['saldo_final']
            suma_activos_inventario_si= row_activo_efectivo[6]['saldo_inicial']+row_activo_efectivo[7]['saldo_inicial']
            datas['suma_activos_circulantes']= suma_efectivo_bancos+suma_derechos_recibir+suma_activos_inventario
            datas['suma_activos_circulantes_si']= suma_efectivo_bancos_si+suma_derechos_recibir_si+suma_activos_inventario_si
            ####activo no circulante
            datas['mobiliario_equipo_saldo']= row_activo_efectivo[8]['saldo_final']
            datas['mobiliario_equipo_saldo_inicial']= row_activo_efectivo[8]['saldo_inicial']
            datas['mobiliario_recreativo_saldo']= row_activo_efectivo[9]['saldo_final']
            datas['mobiliario_recreativo_saldo_inicial']= row_activo_efectivo[9]['saldo_inicial']
            datas['equipo_instrumental_saldo']= row_activo_efectivo[10]['saldo_final']
            datas['equipo_instrumental_saldo_inicial']= row_activo_efectivo[10]['saldo_inicial']
            datas['equipo_trasporte_saldo']= row_activo_efectivo[11]['saldo_final']
            datas['equipo_trasporte_saldo_inicial']= row_activo_efectivo[11]['saldo_inicial']
            datas['maquinaria_otros_saldo']= row_activo_efectivo[12]['saldo_final']
            datas['maquinaria_otros_saldo_inicial']= row_activo_efectivo[12]['saldo_inicial']
            datas['coleciones_arte_saldo']= row_activo_efectivo[13]['saldo_final']
            datas['coleciones_arte_saldo_inicial']= row_activo_efectivo[13]['saldo_inicial']
            suma_bienes_inmuebles= row_activo_efectivo[8]['saldo_final']+row_activo_efectivo[9]['saldo_final']+row_activo_efectivo[10]['saldo_final']+row_activo_efectivo[11]['saldo_final']+row_activo_efectivo[12]['saldo_final']+row_activo_efectivo[13]['saldo_final']
            suma_bienes_inmuebles_si= row_activo_efectivo[8]['saldo_inicial']+row_activo_efectivo[9]['saldo_inicial']+row_activo_efectivo[10]['saldo_inicial']+row_activo_efectivo[11]['saldo_inicial']+row_activo_efectivo[12]['saldo_inicial']+row_activo_efectivo[13]['saldo_inicial']
            datas['suma_bienes_inmuebles']= suma_bienes_inmuebles
            datas['suma_bienes_inmuebles_si']= suma_bienes_inmuebles_si
            ####
            datas['software_saldo']= row_activo_efectivo[14]['saldo_final']
            datas['software_saldo_inicial']= row_activo_efectivo[14]['saldo_inicial']
            datas['licencias_info_saldo']= row_activo_efectivo[15]['saldo_final']
            datas['licencias_info_saldo_inicial']= row_activo_efectivo[15]['saldo_inicial']
            suma_activos_intangibles= row_activo_efectivo[14]['saldo_final']+row_activo_efectivo[15]['saldo_final']
            suma_activos_intangibles_si= row_activo_efectivo[14]['saldo_inicial']+row_activo_efectivo[15]['saldo_inicial']
            datas['suma_activos_intangibles']= suma_activos_intangibles
            datas['suma_activos_intangibles_si']= suma_activos_intangibles_si
            ####
            suma_depreciaciones= row_activo_efectivo[16]['saldo_final']*-1
            suma_depreciaciones_si= row_activo_efectivo[16]['saldo_inicial']*-1
            datas['suma_depreciaciones']= suma_depreciaciones
            datas['suma_depreciaciones_si']= suma_depreciaciones_si

            datas['suma_activos_no_circulantes']= suma_bienes_inmuebles+suma_activos_intangibles+suma_depreciaciones
            datas['suma_activos_no_circulantes_si']= suma_bienes_inmuebles_si+suma_activos_intangibles_si+suma_depreciaciones_si

            datas['suma_activos']= suma_efectivo_bancos+suma_derechos_recibir+suma_activos_inventario+suma_bienes_inmuebles+suma_activos_intangibles+suma_depreciaciones
            datas['suma_activos_si']= suma_efectivo_bancos_si+suma_derechos_recibir_si+suma_activos_inventario_si+suma_bienes_inmuebles_si+suma_activos_intangibles_si+suma_depreciaciones_si
            #####pasivo circulante#####
            sql_pasivo="""SELECT code,account_id,ABS(saldo_inicial) AS saldo_inicial,ABS(saldo_final) AS saldo_final  FROM v_balanza WHERE anio='%s' AND periodo=%s AND account_id in (186,226,253,275,277,283,291,312,318,2635)"""
            self.env.cr.execute(sql_pasivo % (self.anio_fiscal,self.periodo))
            row_pasivo = self.env.cr.dictfetchall()

            datas['servicios_per_saldo']=row_pasivo[0]['saldo_final']
            datas['servicios_per_saldo_inicial']= row_pasivo[0]['saldo_inicial']
            datas['proveedor_saldo']= row_pasivo[1]['saldo_final']
            datas['proveedor_saldo_inicial']= row_pasivo[1]['saldo_inicial']
            datas['retenciones_contri']= row_pasivo[2]['saldo_final']
            datas['retenciones_contri_inicial']= row_pasivo[2]['saldo_inicial']
            datas['acreedores_dicersos_saldo']= row_pasivo[3]['saldo_final']
            datas['acreedores_dicersos_saldo_inicial']= row_pasivo[3]['saldo_inicial']
            datas['contingencias_saldo']= row_pasivo[4]['saldo_final']
            datas['contingencias_saldo_inicial']= row_pasivo[4]['saldo_inicial']
            suma_cuenta_pagar= row_pasivo[0]['saldo_final']+row_pasivo[1]['saldo_final']+row_pasivo[2]['saldo_final']+row_pasivo[3]['saldo_final']+row_pasivo[4]['saldo_final']
            suma_cuenta_pagar_si= row_pasivo[0]['saldo_inicial']+row_pasivo[1]['saldo_inicial']+row_pasivo[2]['saldo_inicial']+row_pasivo[3]['saldo_inicial']+row_pasivo[4]['saldo_inicial']
            datas['suma_cuenta_pagar']= suma_cuenta_pagar
            datas['suma_cuenta_pagar_si']= suma_cuenta_pagar_si

            datas['suma_pasivo_circulante']= suma_cuenta_pagar
            datas['suma_pasivo_circulante_si']= suma_cuenta_pagar_si

            ####pasivo no circulante
            datas['otras_provisiones_saldo']= row_pasivo[5]['saldo_final']
            datas['otras_provisiones_saldo_inicial']= row_pasivo[5]['saldo_inicial']
            suma_proviciones_lp=row_pasivo[5]['saldo_final']
            suma_proviciones_lp_si=row_pasivo[5]['saldo_inicial']
            datas['suma_proviciones_lp']= suma_proviciones_lp
            datas['suma_proviciones_lp_si']= suma_proviciones_lp_si
            ####
            suma_pasivo_no_cir=row_pasivo[5]['saldo_final']
            suma_pasivo_no_cir_si=row_pasivo[5]['saldo_inicial']
            datas['suma_pasivo_no_cir']= suma_pasivo_no_cir
            datas['suma_pasivo_no_cir_si']= suma_pasivo_no_cir_si
            suma_pasivos=suma_cuenta_pagar+suma_pasivo_no_cir
            suma_pasivos_si=suma_cuenta_pagar_si+suma_pasivo_no_cir_si
            datas['suma_pasivos']= suma_cuenta_pagar+suma_pasivo_no_cir
            datas['suma_pasivos_si']= suma_cuenta_pagar_si+suma_pasivo_no_cir_si

            ####hacienda publica
            datas['aportaciones_saldo']= row_pasivo[6]['saldo_final']
            datas['aportaciones_saldo_inicial']= row_pasivo[6]['saldo_inicial']
            datas['donaciones_capital_saldo']= row_pasivo[7]['saldo_final']
            datas['donaciones_capital_saldo_inicial']= row_pasivo[7]['saldo_inicial']
            suma_hacienda_publica_dona=row_pasivo[6]['saldo_final']+row_pasivo[7]['saldo_final']
            suma_hacienda_publica_dona_si=row_pasivo[6]['saldo_inicial']+row_pasivo[7]['saldo_inicial']
            datas['suma_hacienda_publica_dona']= suma_hacienda_publica_dona
            datas['suma_hacienda_publica_dona_si']= suma_hacienda_publica_dona_si
            ######
            sql_pasivo_ahorro="""SELECT code,account_id,ABS(saldo_inicial) AS saldo_inicial,ABS(saldo_final) AS saldo_final  FROM v_balanza WHERE anio='%s' AND periodo=%s AND account_id in ('333','338','356','472','558','684')"""
            self.env.cr.execute(sql_pasivo_ahorro % (self.anio_fiscal,self.periodo))
            row_pasivo_ahorro = self.env.cr.dictfetchall()
            datas['trans_asig_saldo']= row_pasivo_ahorro[0]['saldo_final']
            datas['trans_asig_saldo_inicial']= row_pasivo_ahorro[0]['saldo_inicial']
            datas['otros_ingresos_saldo']= row_pasivo_ahorro[1]['saldo_final']
            datas['otros_ingresos_saldo_inicial']= row_pasivo_ahorro[1]['saldo_inicial']
            datas['servi_personales_saldo']= row_pasivo_ahorro[2]['saldo_final']
            datas['servi_personales_saldo_inicial']= row_pasivo_ahorro[2]['saldo_inicial']
            datas['materiales_sumi_saldo']= row_pasivo_ahorro[3]['saldo_final']
            datas['materiales_sumi_saldo_inicial']= row_pasivo_ahorro[3]['saldo_inicial']
            datas['servicios_general_saldo']= row_pasivo_ahorro[4]['saldo_final']
            datas['servicios_general_saldo_inicial']= row_pasivo_ahorro[4]['saldo_inicial']
            datas['otros_gastos_p_saldo']= row_pasivo_ahorro[5]['saldo_final']
            datas['otros_gastos_p_saldo_inicial']= row_pasivo_ahorro[5]['saldo_inicial']
            suma_a=row_pasivo_ahorro[0]['saldo_final']+ row_pasivo_ahorro[1]['saldo_final']
            suma_a_inicial=row_pasivo_ahorro[0]['saldo_inicial']+ row_pasivo_ahorro[1]['saldo_inicial']
            suma_b=row_pasivo_ahorro[2]['saldo_final']+ row_pasivo_ahorro[3]['saldo_final']+ row_pasivo_ahorro[4]['saldo_final']+ row_pasivo_ahorro[5]['saldo_final']
            suma_b_inicial=row_pasivo_ahorro[2]['saldo_inicial']+ row_pasivo_ahorro[3]['saldo_inicial']+ row_pasivo_ahorro[4]['saldo_inicial']+ row_pasivo_ahorro[5]['saldo_inicial']
            suma_re=suma_a-suma_b
            suma_re_saldo=suma_a_inicial-suma_b_inicial
            datas['suma_resultado_ejercicio']= suma_re
            datas['suma_resultado_ejercicio_si']=suma_re_saldo
            ###
            datas['resultado_del_ejerci_saldo']= row_pasivo[8]['saldo_final']
            datas['resultado_del_ejerci_saldo_inicial']= row_pasivo[8]['saldo_inicial']
            datas['resultado_ejer_anteriores']= row_pasivo[9]['saldo_final']*-1
            datas['resultado_ejer_anteriores_inicial']= row_pasivo[9]['saldo_inicial']*-1
            suma_hacienda_publica=suma_re+row_pasivo[9]['saldo_final']*-1
            suma_hacienda_publica_si=suma_re_saldo+row_pasivo[9]['saldo_inicial']*-1
            datas['suma_hacienda_publica']= suma_hacienda_publica
            datas['suma_hacienda_publica_si']= suma_hacienda_publica_si
            ###
            suma_hacienda_patrimonio=suma_hacienda_publica_dona+suma_hacienda_publica
            suma_hacienda_patrimonio_si=suma_hacienda_publica_dona_si+suma_hacienda_publica_si
            datas['suma_hacienda_patrimonio']= suma_hacienda_patrimonio
            datas['suma_hacienda_patrimonio_si']= suma_hacienda_patrimonio_si
            ###
            datas['suma_pasivo_hacienda']= suma_pasivos+suma_hacienda_patrimonio
            datas['suma_pasivo_hacienda_si']= suma_pasivos_si+suma_hacienda_patrimonio_si
            datas['anio_fiscal']= self.anio_fiscal
            datas['periodo_fiscal']= self.periodo
            return self.env['report'].get_action([], 'reportes.situacion_financiera', data=datas)
        elif self.reporte_select.no_reporte == 2:
            datas = {}
            res = self.read(['periodo','anio_fiscal'])
            res = res and res[0] or {}
            if self.periodo and self.anio_fiscal:
                self.env.cr.execute("""
                        %s
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
                    """ % (self._select(), self.periodo, self.anio_fiscal))
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
                datas['form'] = res
            return self.env['report'].get_action([], 'reportes.estado_actividades', data=datas)
        if self.reporte_select.no_reporte == 3:
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
                            ABS(saldo_final) - ABS(saldo_inicial) as importe,
                            saldo_inicial - saldo_final as origen
                        FROM v_balanza
                        WHERE periodo = %s
                        AND anio = '%s'
                        AND account_id in (
                            '37',
                            '61',
                            '108',
                            '126',
                            '170',
                            '185',
                            '277',
                            '312',
                            '275',

                            '280',
                            '163',
                            '291',
                            '320',
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
                        'origen': i['origen'],
                    }
                    ids.append(query_r)
                
                datas['query_estado'] = ids
                datas['form'] = res
            return self.env['report'].get_action([], 'reportes.estado_cambios_situacion_financiera', data=datas)
        elif self.reporte_select.no_reporte == 4:
            datas = {}
            sql="""
            select account_id,saldo_final from v_balanza where account_id=277 and periodo=%s;"""
            self.env.cr.execute(sql % (self.periodo))
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
            return self.env['report'].get_action([], 'reportes.report_pasivos_contingentes', data=datas)
        elif self.reporte_select.no_reporte == 5:
            datas = {}
            datas['anio_fiscal']= self.anio_fiscal
            datas['periodo_fiscal']= self.periodo
            #####pasivo circulante#####
            sql_pasivo="""SELECT code,account_id,ABS(saldo_inicial) AS saldo_inicial,ABS(saldo_final) AS saldo_final  FROM v_balanza WHERE anio='%s' AND periodo=%s AND account_id in (186,226,253,275,277,283,291,312,318,2635)"""
            self.env.cr.execute(sql_pasivo % (self.anio_fiscal,self.periodo))
            row_pasivo = self.env.cr.dictfetchall()
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
            return self.env['report'].get_action([], 'reportes.report_esta_deuda_pasivos', data=datas)
        elif self.reporte_select.no_reporte == 6:
            datas = {}
            res = self.read(['periodo','anio_fiscal'])
            res = res and res[0] or {}
            if self.periodo and self.anio_fiscal:
                sql_activo_circulante_banco="""SELECT code,account_id,abs(saldo_inicial) AS saldo_inicial,saldo_final AS saldo_final  FROM v_balanza WHERE anio='%s' AND periodo=%s AND account_id in (45)  order by code asc"""
                self.env.cr.execute(sql_activo_circulante_banco % (self.anio_fiscal,self.periodo))
                row_activo_efectivo_banco = self.env.cr.dictfetchall()
                sql_activo = """SELECT code,account_id, ABS(saldo_inicial) AS saldo_inicial, ABS(saldo_final) AS saldo_final, ABS(debe) AS debe, ABS(haber) AS haber FROM v_balanza WHERE anio='%s' AND periodo=%s AND account_id in (35, 36, 37, 38, 45, 52, 58, 61, 62, 72, 98, 108, 116, 117, 118, 126, 127, 137, 143, 147, 151, 161, 163, 164, 166, 170)"""
                self.env.cr.execute(sql_activo % (self.anio_fiscal,self.periodo))
                rows_sql = self.env.cr.dictfetchall()
                ids=[]
                for i in rows_sql:
                    query_r = {
                        'account_id': i['account_id'],
                        'code': i['code'],
                        'saldo_inicial': i['saldo_inicial'],
                        'saldo_final': i['saldo_final'],
                        'debe': i['debe'],
                        'haber': i['haber']
                    }
                    ids.append(query_r)

                ids_banco=[]
                for i in row_activo_efectivo_banco:
                    query_banco = {
                        'account_id': i['account_id'],
                        'code': i['code'],
                        'saldo_inicial': i['saldo_inicial'],
                        'saldo_final': i['saldo_final']
                    }
                    ids_banco.append(query_banco)
            datas['query_estado'] = ids
            datas['query_bancos'] = ids_banco
            datas['form'] = res
            return self.env['report'].get_action([], 'reportes.estado_analitico_activo', data=datas)
        # Reporte Financiero - Estado de Variaciones en la Hacienda Publica / Patrimonio
        elif self.reporte_select.no_reporte == 7:
            datas = {}
            res = self.read(['periodo','anio_fiscal'])
            res = res and res[0] or {}
            if self.periodo and self.anio_fiscal:
                sql_pasivo="""SELECT code,account_id,ABS(saldo_inicial) AS saldo_inicial,ABS(saldo_final) AS saldo_final  FROM v_balanza WHERE anio='%s' AND periodo=%s AND account_id in (291,312,318,2635,333,338,356,472,558,684)"""
                self.env.cr.execute(sql_pasivo % (self.anio_fiscal,self.periodo))
                rows_sql = self.env.cr.dictfetchall()
                ids=[]
                for i in rows_sql:
                    query_r = {
                        'account_id': i['account_id'],
                        'code': i['code'],
                        'saldo_inicial': i['saldo_inicial'],
                        'saldo_final': i['saldo_final']
                    }
                    ids.append(query_r)
            datas['query_estado'] = ids
            datas['form'] = res
            #raise ValidationError(datas['query_estado'])
            return self.env['report'].get_action([], 'reportes.estado_variaciones_hp', data=datas)
        elif self.reporte_select.no_reporte == 8:
            periodo_anterior=self.periodo-1
            datas = {}
            datas['anio_fiscal']= self.anio_fiscal
            datas['periodo_fiscal']= self.periodo
            sql_pasivo="""SELECT code,account_id,ABS(saldo_final) AS saldo_inicial,ABS(saldo_inicial) AS saldo_final, ABS(saldo_final) - ABS(saldo_inicial) importe  FROM v_balanza 
            WHERE anio='%s' AND periodo=%s AND account_id in (334,338,356,472,558,290,108,312,185,291)"""
            self.env.cr.execute(sql_pasivo % (self.anio_fiscal,self.periodo))
            row_pasivo = self.env.cr.dictfetchall()
            
            sql_pasivo_anterios="""SELECT code,account_id,ABS(saldo_final) AS saldo_inicial,ABS(saldo_inicial) AS saldo_final, ABS(saldo_final) - ABS(saldo_inicial) importe  FROM v_balanza 
            WHERE anio='%s' AND periodo=%s AND account_id in (334,338,356,472,558,290,108,312,185,291)"""
            self.env.cr.execute(sql_pasivo_anterios % (self.anio_fiscal,periodo_anterior))
            row_pasivo_anterior = self.env.cr.dictfetchall()
            sql_bienes_mue="""SELECT code,account_id,ABS(saldo_final) AS saldo_inicial,ABS(saldo_inicial) AS saldo_final, ABS(saldo_final) - ABS(saldo_inicial) importe  FROM v_balanza 
            WHERE anio='%s' AND periodo=%s AND account_id in (126)"""
            self.env.cr.execute(sql_bienes_mue % (self.anio_fiscal,self.periodo))
            row_buenes_mueble = self.env.cr.dictfetchall()
            
            sql_bienes_mueanet="""SELECT code,account_id,ABS(saldo_final) AS saldo_inicial,ABS(saldo_inicial) AS saldo_final, ABS(saldo_final) - ABS(saldo_inicial) importe  FROM v_balanza 
            WHERE anio='%s' AND periodo=%s AND account_id in (126)"""
            self.env.cr.execute(sql_bienes_mueanet % (self.anio_fiscal,periodo_anterior))
            row_buenes_mueble_ante = self.env.cr.dictfetchall()
            
            suma_si_origen=row_pasivo[5]['importe']+row_pasivo[6]['importe']
            datas['suma_si_origen']=suma_si_origen
            suma_sf_origen=row_pasivo_anterior[5]['importe']+row_pasivo_anterior[6]['importe']
            datas['suma_sf_origen']=suma_sf_origen
            
            saldo_inicial_115=row_pasivo[0]['importe']
            datas['almacen_si']=saldo_inicial_115
            saldo_final_115=row_pasivo_anterior[0]['importe']
            datas['almacen_sf']=saldo_final_115
            
            saldo_inicial_211=row_pasivo[1]['importe']
            datas['cuentas_cortop_si']=saldo_inicial_211
            saldo_final_211=row_pasivo_anterior[1]['importe']
            datas['cuentas_cortop_sf']=saldo_final_211
            
            saldo_inicial_310=row_pasivo[2]['importe']
            datas['hacienda_publica_si']=saldo_inicial_310
            saldo_final_310=row_pasivo_anterior[2]['importe']
            datas['hacienda_publica_sf']=saldo_final_310
            
            saldo_inicial_311=row_pasivo[3]['importe']
            datas['aportaciones_saldo_si']=saldo_inicial_311
            saldo_final_311=row_pasivo_anterior[3]['importe']
            datas['aportaciones_saldo_sf']=saldo_final_311
            
            saldo_inicial_312=row_pasivo[4]['importe']
            datas['donaciones_capital_si']=saldo_inicial_312
            saldo_final_312=row_pasivo_anterior[4]['importe']
            datas['donaciones_capital_sf']=saldo_final_312
            
            saldo_inicial_422=row_pasivo[5]['importe']
            datas['transferencias_internas_si']=saldo_inicial_422
            saldo_final_422=row_pasivo_anterior[5]['importe']
            datas['transferencias_internas_sf']=saldo_final_422
            
            saldo_inicial_430=row_pasivo[6]['importe']
            datas['otros_ingresos_si']=saldo_inicial_430
            saldo_final_430=row_pasivo_anterior[6]['importe']
            datas['otros_ingresos_sf']=saldo_final_430
            
            suma_si_aplicacion=row_pasivo[7]['importe']+row_pasivo[8]['importe']+row_pasivo[9]['importe']
            datas['suma_si_aplicacion']=suma_si_aplicacion
            suma_sf_aplicacion=row_pasivo_anterior[7]['importe']+row_pasivo_anterior[8]['importe']+row_pasivo_anterior[9]['importe']
            datas['suma_sf_aplicacion']=suma_sf_aplicacion
            
            saldo_inicial_511=row_pasivo[7]['importe']
            datas['servicios_personales_si']=saldo_inicial_511
            saldo_final_511=row_pasivo_anterior[7]['importe']
            datas['servicios_personales_sf']=saldo_final_511
             
            saldo_inicial_512=row_pasivo[8]['importe']
            datas['materiales_suministros_si']=saldo_inicial_512
            saldo_final_512=row_pasivo_anterior[8]['importe']
            datas['materiales_suministros_sf']=saldo_final_512
            
            saldo_inicial_513=row_pasivo[9]['importe']
            datas['servicios_generales_si']=saldo_inicial_513 
            saldo_final_513=row_pasivo_anterior[9]['importe']
            datas['servicios_generales_sf']=saldo_final_513
            
            resta_si_flujos_netos_si=suma_si_origen-suma_si_aplicacion
            datas['resta_si_flujos_netos_si']=resta_si_flujos_netos_si
            resta_si_flujos_netos_sf=suma_sf_origen-suma_sf_aplicacion
            datas['resta_si_flujos_netos_sf']=resta_si_flujos_netos_sf
            
            suma_dona_apor_si=saldo_inicial_311+saldo_inicial_312
            suma_dona_apor_sf=saldo_final_311+saldo_final_312
            
            resta_si_origen_flujos=saldo_inicial_310
            datas['resta_si_origen_flujos']=resta_si_origen_flujos
            
            
            resta_sf_origen_flujos=saldo_final_310
            datas['resta_sf_origen_flujos']=resta_sf_origen_flujos
            suma_origen_si_1=saldo_inicial_310
            datas['suma_origen_si_1']=suma_origen_si_1
            
            suma_origen_si_2=saldo_final_310
            datas['suma_origen_si_2']=suma_origen_si_2
            
            
            saldo_inicial_124=row_buenes_mueble[0]['importe']
            datas['bienes_muebles_si']=saldo_inicial_124
            saldo_final_124=row_buenes_mueble_ante[0]['importe']
            datas['bienes_muebles_sf']=saldo_final_124
            
            
            sql_aplicacion="""SELECT code,account_id,ABS(saldo_final) AS saldo_inicial,ABS(saldo_inicial) AS saldo_final, ABS(saldo_final) - ABS(saldo_inicial) importe  FROM v_balanza 
            WHERE anio='%s' AND periodo=%s AND account_id in (108,183,283)"""
            self.env.cr.execute(sql_aplicacion % (self.anio_fiscal,self.periodo))
            row_aplicacion = self.env.cr.dictfetchall()
            
            sql_aplicacion_anterior="""SELECT code,account_id,ABS(saldo_final) AS saldo_inicial,ABS(saldo_inicial) AS saldo_final, ABS(saldo_final) - ABS(saldo_inicial) importe  FROM v_balanza 
            WHERE anio='%s' AND periodo=%s AND account_id in (108,183,283)"""
            self.env.cr.execute(sql_aplicacion_anterior % (self.anio_fiscal,periodo_anterior))
            row_aplicacion_anterior = self.env.cr.dictfetchall()
            
            

            saldo_inicial_125=row_aplicacion[0]['importe']
            datas['activos_intangibles_si']=saldo_inicial_125 
            saldo_final_125=row_aplicacion_anterior[0]['importe']
            datas['activos_intangibles_sf']=saldo_final_125
            
            saldo_inicial_almacen=saldo_inicial_125
            datas['saldo_inicial_almacen']=saldo_inicial_almacen
            saldo_final_almacen=saldo_final_125
            datas['saldo_final_almacen']=saldo_final_almacen
            
            resta_saldo_inicial_200=row_aplicacion[1]['importe']
            datas['otros_of_si']=resta_saldo_inicial_200 
            saldo_final_200=row_aplicacion_anterior[1]['importe']
            datas['otros_of_sf']=saldo_final_200
            
            sql_111="""SELECT code,account_id,ABS(saldo_final) AS saldo_inicial,ABS(saldo_inicial) AS saldo_final, ABS(saldo_final) - ABS(saldo_inicial) importe  FROM v_balanza 
            WHERE anio='%s' AND periodo=%s AND account_id in (37)"""
            self.env.cr.execute(sql_111 % (self.anio_fiscal,self.periodo))
            row_1110 = self.env.cr.dictfetchall()
            sql_111_ante="""SELECT code,account_id,ABS(saldo_final) AS saldo_inicial,ABS(saldo_inicial) AS saldo_final, ABS(saldo_final) - ABS(saldo_inicial) importe  FROM v_balanza 
            WHERE anio='%s' AND periodo=%s AND account_id in (37)"""
            self.env.cr.execute(sql_111_ante % (self.anio_fiscal,periodo_anterior))
            row_1110_ante = self.env.cr.dictfetchall()
            
            saldo_inicial_1110=row_1110[0]['saldo_inicial']
            
            datas['1110_si']=saldo_inicial_1110 
            saldo_final_1110=row_1110[0]['importe']
            datas['1110_sf']=saldo_final_1110
            if(self.periodo==1):
                importes = self.env['tjacdmx.ajustes_flujo_efectivo'].search([('periodo', '=',self.periodo),('anio', '=', self.anio_fiscal)], limit=1)
                if(importes):
                    datas['saldo_inicial_otros_apli_fi_si']=float(importes.importe_periodo) 
                    saldo_final_otros_apli_fi=float(importes.importe_periodo_anterior)
                    datas['saldo_inicial_otros_apli_fi_sf']=saldo_final_otros_apli_fi
                else:
                    datas['saldo_inicial_otros_apli_fi_si']=float('0') 
                    saldo_final_otros_apli_fi=float('0')
                    datas['saldo_inicial_otros_apli_fi_sf']=saldo_final_otros_apli_fi
            elif(self.periodo==2):
                importes = self.env['tjacdmx.ajustes_flujo_efectivo'].search([('periodo', '=',self.periodo),('anio', '=', self.anio_fiscal)], limit=1)
                if(importes):
                    datas['saldo_inicial_otros_apli_fi_si']=float(importes.importe_periodo) 
                    saldo_final_otros_apli_fi=float(importes.importe_periodo_anterior)
                    datas['saldo_inicial_otros_apli_fi_sf']=saldo_final_otros_apli_fi
                else:
                    datas['saldo_inicial_otros_apli_fi_si']=float('0') 
                    saldo_final_otros_apli_fi=float('0')
                    datas['saldo_inicial_otros_apli_fi_sf']=saldo_final_otros_apli_fi
            elif(self.periodo==3):
                importes = self.env['tjacdmx.ajustes_flujo_efectivo'].search([('periodo', '=',self.periodo),('anio', '=', self.anio_fiscal)], limit=1)
                if(importes):
                    datas['saldo_inicial_otros_apli_fi_si']=float(importes.importe_periodo) 
                    saldo_final_otros_apli_fi=float(importes.importe_periodo_anterior)
                    datas['saldo_inicial_otros_apli_fi_sf']=saldo_final_otros_apli_fi
                else:
                    datas['saldo_inicial_otros_apli_fi_si']=float('0') 
                    saldo_final_otros_apli_fi=float('0')
                    datas['saldo_inicial_otros_apli_fi_sf']=saldo_final_otros_apli_fi
            elif(self.periodo==4):
                importes = self.env['tjacdmx.ajustes_flujo_efectivo'].search([('periodo', '=',self.periodo),('anio', '=', self.anio_fiscal)], limit=1)
                if(importes):
                    datas['saldo_inicial_otros_apli_fi_si']=float(importes.importe_periodo) 
                    saldo_final_otros_apli_fi=float(importes.importe_periodo_anterior)
                    datas['saldo_inicial_otros_apli_fi_sf']=saldo_final_otros_apli_fi
                else:
                    datas['saldo_inicial_otros_apli_fi_si']=float('0') 
                    saldo_final_otros_apli_fi=float('0')
                    datas['saldo_inicial_otros_apli_fi_sf']=saldo_final_otros_apli_fi
            elif(self.periodo==5):
                importes = self.env['tjacdmx.ajustes_flujo_efectivo'].search([('periodo', '=',self.periodo),('anio', '=', self.anio_fiscal)], limit=1)
                if(importes):
                    datas['saldo_inicial_otros_apli_fi_si']=float(importes.importe_periodo) 
                    saldo_final_otros_apli_fi=float(importes.importe_periodo_anterior)
                    datas['saldo_inicial_otros_apli_fi_sf']=saldo_final_otros_apli_fi
                else:
                    datas['saldo_inicial_otros_apli_fi_si']=float('0') 
                    saldo_final_otros_apli_fi=float('0')
                    datas['saldo_inicial_otros_apli_fi_sf']=saldo_final_otros_apli_fi
            elif(self.periodo==6):
                importes = self.env['tjacdmx.ajustes_flujo_efectivo'].search([('periodo', '=',self.periodo),('anio', '=', self.anio_fiscal)], limit=1)
                if(importes):
                    datas['saldo_inicial_otros_apli_fi_si']=float(importes.importe_periodo) 
                    saldo_final_otros_apli_fi=float(importes.importe_periodo_anterior)
                    datas['saldo_inicial_otros_apli_fi_sf']=saldo_final_otros_apli_fi
                else:
                    datas['saldo_inicial_otros_apli_fi_si']=float('0') 
                    saldo_final_otros_apli_fi=float('0')
                    datas['saldo_inicial_otros_apli_fi_sf']=saldo_final_otros_apli_fi
            elif(self.periodo==7):
                importes = self.env['tjacdmx.ajustes_flujo_efectivo'].search([('periodo', '=',self.periodo),('anio', '=', self.anio_fiscal)], limit=1)
                if(importes):
                    datas['saldo_inicial_otros_apli_fi_si']=float(importes.importe_periodo) 
                    saldo_final_otros_apli_fi=float(importes.importe_periodo_anterior)
                    datas['saldo_inicial_otros_apli_fi_sf']=saldo_final_otros_apli_fi
                else:
                    datas['saldo_inicial_otros_apli_fi_si']=float('0') 
                    saldo_final_otros_apli_fi=float('0')
                    datas['saldo_inicial_otros_apli_fi_sf']=saldo_final_otros_apli_fi
            elif(self.periodo==8):
                importes = self.env['tjacdmx.ajustes_flujo_efectivo'].search([('periodo', '=',self.periodo),('anio', '=', self.anio_fiscal)], limit=1)
                if(importes):
                    datas['saldo_inicial_otros_apli_fi_si']=float(importes.importe_periodo) 
                    saldo_final_otros_apli_fi=float(importes.importe_periodo_anterior)
                    datas['saldo_inicial_otros_apli_fi_sf']=saldo_final_otros_apli_fi
                else:
                    datas['saldo_inicial_otros_apli_fi_si']=float('0') 
                    saldo_final_otros_apli_fi=float('0')
                    datas['saldo_inicial_otros_apli_fi_sf']=saldo_final_otros_apli_fi
            elif(self.periodo==9):
                importes = self.env['tjacdmx.ajustes_flujo_efectivo'].search([('periodo', '=',self.periodo),('anio', '=', self.anio_fiscal)], limit=1)
                if(importes):
                    datas['saldo_inicial_otros_apli_fi_si']=float(importes.importe_periodo) 
                    saldo_final_otros_apli_fi=float(importes.importe_periodo_anterior)
                    datas['saldo_inicial_otros_apli_fi_sf']=saldo_final_otros_apli_fi
                else:
                    datas['saldo_inicial_otros_apli_fi_si']=float('0') 
                    saldo_final_otros_apli_fi=float('0')
                    datas['saldo_inicial_otros_apli_fi_sf']=saldo_final_otros_apli_fi
            elif(self.periodo==10):
                importes = self.env['tjacdmx.ajustes_flujo_efectivo'].search([('periodo', '=',self.periodo),('anio', '=', self.anio_fiscal)], limit=1)
                if(importes):
                    datas['saldo_inicial_otros_apli_fi_si']=float(importes.importe_periodo) 
                    saldo_final_otros_apli_fi=float(importes.importe_periodo_anterior)
                    datas['saldo_inicial_otros_apli_fi_sf']=saldo_final_otros_apli_fi
                else:
                    datas['saldo_inicial_otros_apli_fi_si']=float('0') 
                    saldo_final_otros_apli_fi=float('0')
                    datas['saldo_inicial_otros_apli_fi_sf']=saldo_final_otros_apli_fi
            elif(self.periodo==11):
                importes = self.env['tjacdmx.ajustes_flujo_efectivo'].search([('periodo', '=',self.periodo),('anio', '=', self.anio_fiscal)], limit=1)
                if(importes):
                    datas['saldo_inicial_otros_apli_fi_si']=float(importes.importe_periodo) 
                    saldo_final_otros_apli_fi=float(importes.importe_periodo_anterior)
                    datas['saldo_inicial_otros_apli_fi_sf']=saldo_final_otros_apli_fi
                else:
                    datas['saldo_inicial_otros_apli_fi_si']=float('0') 
                    saldo_final_otros_apli_fi=float('0')
                    datas['saldo_inicial_otros_apli_fi_sf']=saldo_final_otros_apli_fi
            elif(self.periodo==12):
                importes = self.env['tjacdmx.ajustes_flujo_efectivo'].search([('periodo', '=',self.periodo),('anio', '=', self.anio_fiscal)], limit=1)
                if(importes):
                    datas['saldo_inicial_otros_apli_fi_si']=float(importes.importe_periodo) 
                    saldo_final_otros_apli_fi=float(importes.importe_periodo_anterior)
                    datas['saldo_inicial_otros_apli_fi_sf']=saldo_final_otros_apli_fi
                else:
                    datas['saldo_inicial_otros_apli_fi_si']=float('0') 
                    saldo_final_otros_apli_fi=float('0')
                    datas['saldo_inicial_otros_apli_fi_sf']=saldo_final_otros_apli_fi
                

            efectivo_equivalenteinie_sf=row_1110_ante[0]['saldo_final']
            datas['efectivo_equivalenteinie_sf']=efectivo_equivalenteinie_sf
            
            saldo_inicial_226=row_aplicacion[2]['saldo_inicial']
            datas['otras_proviciones_lp_si']=saldo_inicial_226 
            saldo_final_226=row_aplicacion[2]['saldo_final']
            datas['otras_proviciones_lp_sf']=saldo_final_226
            
            #raise UserError(_('Debug: --------------%s' % (saldo_final_almacen)))
            return self.env['report'].get_action([], 'reportes.report_estado_flujos_efectivo', data=datas)
        elif self.reporte_select.no_reporte == 9:
            datas={}
            
            return self.env['report'].get_action([], 'reportes.report_notas_estados_financieros', data=datas)
