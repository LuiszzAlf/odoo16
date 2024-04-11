from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import ValidationError,UserError
from odoo.tools.translate import _
from num2words import num2words

PERIODO_SELECT = [(periodo, periodo) for periodo in range(1,13)]
EJERCICIO_SELECT = [ (year, year) for year in range(2019, 2031)]

class wizard_reportes_financieros(models.TransientModel):
    _name='tjacdmx_wizard_reportes_financieros'
    _description='Reportes financieros'
    
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
    def action_reportes_financieros(self, values):
        if self.reporte_select.no_reporte == 10:
            datas={}
            arr_activo=[]
            #####activo circulante#####
            sql_activo_circulante="""SELECT code,account_id,ABS(saldo_inicial) AS saldo_inicial,ABS(saldo_final) AS saldo_final  FROM v_balanza WHERE anio='%s' AND periodo=%s AND account_id in (38,45,52,62,72,98,105,108,127,137,143,147,151,161,164,167,170)  order by code asc"""
            self.env.cr.execute(sql_activo_circulante % (self.anio_fiscal,self.periodo))
            row_activo_efectivo = self.env.cr.dictfetchall()

            if (self.anio_fiscal==2019):
                saldos_anio_anterior="""SELECT acc.code,csa.cuenta as account_id,csa.importe as saldo_final FROM tjacdmx_contabilidad_saldos_anuales csa
                                        inner join account_account acc on acc.id=csa.cuenta
                                        WHERE id_reporte=31 and anio='2018' and cuenta in (38,45,52,62,72,98,105,108,127,137,143,147,151,161,164,167,170)
                                        order by acc.code asc;"""
                self.env.cr.execute(saldos_anio_anterior)
            else:
                saldos_anio_anterior="""SELECT code,account_id,ABS(saldo_inicial) AS saldo_inicial,ABS(saldo_final) AS saldo_final  FROM v_balanza WHERE anio='%s' AND periodo=12 AND account_id in (38,45,52,62,72,98,105,108,127,137,143,147,151,161,164,167,170)  order by code asc"""
                # self.env.cr.execute(saldos_anio_anterior % (int(self.anio_fiscal)-1))

                saldos_anio_anterior_inv="""SELECT code,account_id,ABS(saldo_inicial) AS saldo_inicial,ABS(saldo_final) AS saldo_final  FROM v_balanza WHERE anio='%s' AND periodo=12 AND account_id in (38,45,52,62,72,98,105,108,127,137,143,147,151,161,164,167,170)  order by code asc"""
                self.env.cr.execute(saldos_anio_anterior_inv % (int(self.anio_fiscal)-1))
            row_saldos_anio_anterior_activo = self.env.cr.dictfetchall()

            # sql_activo_circulante_anio_anterior="""SELECT * FROM tjacdmx_contabilidad_saldos_anuales WHERE id_reporte=31 and anio='%s' order by create_date asc;"""
            # self.env.cr.execute(sql_activo_circulante_anio_anterior % (int(self.anio_fiscal)-1))
            # row_activo_efectivo_anio_anterior = self.env.cr.dictfetchall()
            
            if (self.anio_fiscal==2019):
                sql_activo_circulante_banco="""SELECT code,account_id,saldo_inicial AS saldo_inicial,saldo_final AS saldo_final  FROM v_balanza WHERE anio='%s' AND periodo=%s AND account_id in (45)  order by code asc"""
                self.env.cr.execute(sql_activo_circulante_banco % (self.anio_fiscal,self.periodo))
                row_activo_efectivo_banco = self.env.cr.dictfetchall()

                sql_activo_circulante_banco_before="""SELECT acc.code,csa.cuenta as account_id,csa.importe as saldo_final FROM tjacdmx_contabilidad_saldos_anuales csa
                                                        inner join account_account acc on acc.id=csa.cuenta
                                                        WHERE id_reporte=31 and anio='2018' and cuenta in (45)
                                                        order by acc.code asc;"""
                self.env.cr.execute(sql_activo_circulante_banco_before)
                row_activo_efectivo_banco_before = self.env.cr.dictfetchall()
            else:
                sql_activo_circulante_banco="""SELECT code,account_id,saldo_inicial AS saldo_inicial,saldo_final AS saldo_final  FROM v_balanza WHERE anio='%s' AND periodo=%s AND account_id in (45,52)  order by code asc"""
                self.env.cr.execute(sql_activo_circulante_banco % (self.anio_fiscal,self.periodo))
                row_activo_efectivo_banco = self.env.cr.dictfetchall()

                sql_activo_circulante_banco_before="""SELECT code,account_id,saldo_inicial AS saldo_inicial,saldo_final AS saldo_final  FROM v_balanza WHERE anio='%s' AND periodo=12 AND account_id in (45,52)  order by code asc"""
                self.env.cr.execute(sql_activo_circulante_banco_before % (int(self.anio_fiscal-1)))
                row_activo_efectivo_banco_before = self.env.cr.dictfetchall()
            
            datas['efectivo_saldo']= row_activo_efectivo[0]['saldo_final'] if row_activo_efectivo[0]['saldo_final'] else 0 
            datas['efectivo_saldo_inicial']= row_saldos_anio_anterior_activo[0]['saldo_final']
            datas['bancos_tesoreria_saldo']= row_activo_efectivo_banco[0]['saldo_final']
            datas['bancos_tesoreria_saldo_inicial']= row_activo_efectivo_banco_before[0]['saldo_final']
            datas['inversiones_tesoreria_saldo']= row_activo_efectivo_banco[1]['saldo_final']
            datas['inversiones_tesoreria_saldo_inicial']= row_activo_efectivo_banco_before[1]['saldo_final']
            suma_efectivo_bancos= row_activo_efectivo[0]['saldo_final']+row_activo_efectivo_banco[0]['saldo_final']+row_activo_efectivo_banco[1]['saldo_final']
            suma_efectivo_bancos_si= row_saldos_anio_anterior_activo[0]['saldo_final']+row_activo_efectivo_banco_before[0]['saldo_final']+row_activo_efectivo_banco_before[1]['saldo_final']
            datas['suma_efectivo_bancos']= suma_efectivo_bancos
            datas['suma_efectivo_bancos_si']= suma_efectivo_bancos_si
            ####
            datas['cuentas_pccp_saldo']= row_activo_efectivo[3]['saldo_final']
            datas['cuentas_pccp_saldo_inicial']= row_saldos_anio_anterior_activo[3]['saldo_final']
            datas['deudores_diversos_saldo']= row_activo_efectivo[4]['saldo_final']
            datas['deudores_diversos_saldo_inicial']= row_saldos_anio_anterior_activo[4]['saldo_final']
            datas['ingreso_recuperar_cp_saldo']= row_activo_efectivo[5]['saldo_final']
            datas['ingreso_recuperar_cp_saldo_inicial']= row_saldos_anio_anterior_activo[5]['saldo_final']
            suma_derechos_recibir= row_activo_efectivo[3]['saldo_final']+row_activo_efectivo[4]['saldo_final']+row_activo_efectivo[5]['saldo_final']
            suma_derechos_recibir_si= row_saldos_anio_anterior_activo[3]['saldo_final']+row_saldos_anio_anterior_activo[4]['saldo_final']+row_saldos_anio_anterior_activo[5]['saldo_final']
            datas['suma_derechos_recibir']= suma_derechos_recibir
            datas['suma_derechos_recibir_si']=suma_derechos_recibir_si
            ####
            datas['inventario_saldo']= row_activo_efectivo[6]['saldo_final']
            datas['inventario_saldo_inicial']= row_saldos_anio_anterior_activo[6]['saldo_final']
            datas['almacen_saldo']= row_activo_efectivo[7]['saldo_final']
            datas['almacen_saldo_inicial']= row_saldos_anio_anterior_activo[7]['saldo_final']
            suma_activos_inventario= row_activo_efectivo[6]['saldo_final']+row_activo_efectivo[7]['saldo_final']
            suma_activos_inventario_si= row_saldos_anio_anterior_activo[7]['saldo_final']
            datas['suma_activos_circulantes']= suma_efectivo_bancos+suma_derechos_recibir+suma_activos_inventario
            datas['suma_activos_circulantes_si']= suma_efectivo_bancos_si+suma_derechos_recibir_si+suma_activos_inventario_si
            ####activo no circulante
            datas['mobiliario_equipo_saldo']= row_activo_efectivo[8]['saldo_final']
            datas['mobiliario_equipo_saldo_inicial']= row_saldos_anio_anterior_activo[8]['saldo_final']
            datas['mobiliario_recreativo_saldo']= row_activo_efectivo[9]['saldo_final']
            datas['mobiliario_recreativo_saldo_inicial']= row_saldos_anio_anterior_activo[9]['saldo_final']
            datas['equipo_instrumental_saldo']= row_activo_efectivo[10]['saldo_final']
            datas['equipo_instrumental_saldo_inicial']= row_saldos_anio_anterior_activo[10]['saldo_final']
            datas['equipo_trasporte_saldo']= row_activo_efectivo[11]['saldo_final']
            datas['equipo_trasporte_saldo_inicial']= row_saldos_anio_anterior_activo[11]['saldo_final']
            datas['maquinaria_otros_saldo']= row_activo_efectivo[12]['saldo_final']
            datas['maquinaria_otros_saldo_inicial']= row_saldos_anio_anterior_activo[12]['saldo_final']
            datas['coleciones_arte_saldo']= row_activo_efectivo[13]['saldo_final']
            datas['coleciones_arte_saldo_inicial']= row_saldos_anio_anterior_activo[13]['saldo_final']
            suma_bienes_inmuebles= row_activo_efectivo[8]['saldo_final']+row_activo_efectivo[9]['saldo_final']+row_activo_efectivo[10]['saldo_final']+row_activo_efectivo[11]['saldo_final']+row_activo_efectivo[12]['saldo_final']+row_activo_efectivo[13]['saldo_final']
            suma_bienes_inmuebles_si= row_saldos_anio_anterior_activo[8]['saldo_final']+row_saldos_anio_anterior_activo[9]['saldo_final']+row_saldos_anio_anterior_activo[10]['saldo_final']+row_saldos_anio_anterior_activo[11]['saldo_final']+row_saldos_anio_anterior_activo[12]['saldo_final']+row_saldos_anio_anterior_activo[13]['saldo_final']
            datas['suma_bienes_inmuebles']= suma_bienes_inmuebles
            datas['suma_bienes_inmuebles_si']= suma_bienes_inmuebles_si
            ####
            datas['software_saldo']= row_activo_efectivo[14]['saldo_final']
            datas['software_saldo_inicial']= row_saldos_anio_anterior_activo[14]['saldo_final']
            datas['licencias_info_saldo']= row_activo_efectivo[15]['saldo_final']
            datas['licencias_info_saldo_inicial']= row_saldos_anio_anterior_activo[15]['saldo_final']
            suma_activos_intangibles= row_activo_efectivo[14]['saldo_final']+row_activo_efectivo[15]['saldo_final']
            suma_activos_intangibles_si= row_saldos_anio_anterior_activo[14]['saldo_final']+row_saldos_anio_anterior_activo[15]['saldo_final']
            datas['suma_activos_intangibles']= suma_activos_intangibles
            datas['suma_activos_intangibles_si']= suma_activos_intangibles_si
            ####
            suma_depreciaciones= row_activo_efectivo[16]['saldo_final']*-1
            suma_depreciaciones_si= row_saldos_anio_anterior_activo[16]['saldo_final']*-1
            datas['suma_depreciaciones']= suma_depreciaciones
            datas['suma_depreciaciones_si']= suma_depreciaciones_si

            datas['suma_activos_no_circulantes']= suma_bienes_inmuebles+suma_activos_intangibles+suma_depreciaciones
            datas['suma_activos_no_circulantes_si']= suma_bienes_inmuebles_si+suma_activos_intangibles_si+suma_depreciaciones_si

            datas['suma_activos']= suma_efectivo_bancos+suma_derechos_recibir+suma_activos_inventario+suma_bienes_inmuebles+suma_activos_intangibles+suma_depreciaciones
            datas['suma_activos_si']= suma_efectivo_bancos_si+suma_derechos_recibir_si+suma_activos_inventario_si+suma_bienes_inmuebles_si+suma_activos_intangibles_si+suma_depreciaciones_si
            #####pasivo circulante#####

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

            datas['servicios_per_saldo']=row_pasivo[0]['saldo_final']
            datas['servicios_per_saldo_inicial']= row_pasivo_before[0]['saldo_final']
            datas['proveedor_saldo']= row_pasivo[1]['saldo_final']
            datas['proveedor_saldo_inicial']= row_pasivo_before[1]['saldo_final']
            datas['retenciones_contri']= row_pasivo[2]['saldo_final']
            datas['retenciones_contri_inicial']= row_pasivo_before[2]['saldo_final']
            datas['acreedores_dicersos_saldo']= row_pasivo[3]['saldo_final']
            datas['acreedores_dicersos_saldo_inicial']= row_pasivo_before[3]['saldo_final']
            datas['contingencias_saldo']= 0
            datas['contingencias_saldo_inicial']= 0
            suma_cuenta_pagar= row_pasivo[0]['saldo_final']+row_pasivo[1]['saldo_final']+row_pasivo[2]['saldo_final']+row_pasivo[3]['saldo_final']
            suma_cuenta_pagar_si= row_pasivo_before[0]['saldo_final']+row_pasivo_before[1]['saldo_final']+row_pasivo_before[2]['saldo_final']+row_pasivo_before[3]['saldo_final']+0
            datas['suma_cuenta_pagar']= suma_cuenta_pagar
            datas['suma_cuenta_pagar_si']= suma_cuenta_pagar_si
            datas['provisiones_cp_saldo']= row_pasivo[4]['saldo_final']
            datas['provisiones_cp_saldo_inicial']= row_pasivo_before[4]['saldo_final']
            datas['suma_pasivo_circulante']= suma_cuenta_pagar+row_pasivo[4]['saldo_final']
            datas['suma_pasivo_circulante_si']= suma_cuenta_pagar_si+row_pasivo_before[4]['saldo_final']

            ####pasivo no circulante
            datas['otras_provisiones_saldo']= row_pasivo[5]['saldo_final']
            datas['otras_provisiones_saldo_inicial']= row_pasivo_before[5]['saldo_final']
            suma_proviciones_lp=row_pasivo[5]['saldo_final']
            suma_proviciones_lp_si=row_pasivo_before[5]['saldo_final']
            datas['suma_proviciones_lp']= suma_proviciones_lp
            datas['suma_proviciones_lp_si']= suma_proviciones_lp_si
            ####
            suma_pasivo_no_cir=row_pasivo[5]['saldo_final']
            suma_pasivo_no_cir_si=row_pasivo_before[5]['saldo_final']
            datas['suma_pasivo_no_cir']= suma_pasivo_no_cir
            datas['suma_pasivo_no_cir_si']= suma_pasivo_no_cir_si
            suma_pasivos=suma_cuenta_pagar+suma_pasivo_no_cir+row_pasivo[4]['saldo_final']
            suma_pasivos_si=suma_cuenta_pagar_si+suma_pasivo_no_cir_si
            datas['suma_pasivos']= suma_cuenta_pagar+suma_pasivo_no_cir+row_pasivo[4]['saldo_final']
            suma_pasivo_tot_si=suma_cuenta_pagar_si+suma_pasivo_no_cir_si+row_pasivo_before[4]['saldo_final']
            datas['suma_pasivos_si']= suma_pasivo_tot_si

            ####hacienda publica
            datas['aportaciones_saldo']= row_pasivo[6]['saldo_final']
            datas['aportaciones_saldo_inicial']= row_pasivo_before[6]['saldo_final']
            datas['donaciones_capital_saldo']= row_pasivo[7]['saldo_final']
            datas['donaciones_capital_saldo_inicial']= row_pasivo_before[7]['saldo_final']
            suma_hacienda_publica_dona=row_pasivo[6]['saldo_final']+row_pasivo[7]['saldo_final']
            suma_hacienda_publica_dona_si=row_pasivo_before[6]['saldo_final']+row_pasivo_before[7]['saldo_final']
            datas['suma_hacienda_publica_dona']= suma_hacienda_publica_dona
            datas['suma_hacienda_publica_dona_si']= suma_hacienda_publica_dona_si
            ######
            if(self.anio_fiscal==2019):
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
            else:
                sql_pasivo_ahorro="""SELECT code,account_id,ABS(saldo_inicial) AS saldo_inicial,ABS(saldo_final) AS saldo_final  FROM v_balanza WHERE anio='%s' AND periodo=%s AND account_id in ('333','338','356','472','558','684')"""
                self.env.cr.execute(sql_pasivo_ahorro % (self.anio_fiscal,self.periodo))
                row_pasivo_ahorro = self.env.cr.dictfetchall()

                sql_pasivo_ahorro_before="""SELECT code,account_id,ABS(saldo_inicial) AS saldo_inicial,ABS(saldo_final) AS saldo_final  FROM v_balanza WHERE anio='%s' AND periodo=12 AND account_id in ('333','338','356','472','558','684')"""
                self.env.cr.execute(sql_pasivo_ahorro_before % (self.anio_fiscal-1))
                row_pasivo_ahorro_before = self.env.cr.dictfetchall()

                datas['trans_asig_saldo']= row_pasivo_ahorro[0]['saldo_final']
                datas['trans_asig_saldo_inicial']= row_pasivo_ahorro_before[0]['saldo_final']
                datas['otros_ingresos_saldo']= row_pasivo_ahorro[1]['saldo_final']
                datas['otros_ingresos_saldo_inicial']= row_pasivo_ahorro_before[1]['saldo_final']
                datas['servi_personales_saldo']= row_pasivo_ahorro[2]['saldo_final']
                datas['servi_personales_saldo_inicial']= row_pasivo_ahorro_before[2]['saldo_final']
                datas['materiales_sumi_saldo']= row_pasivo_ahorro[3]['saldo_final']
                datas['materiales_sumi_saldo_inicial']= row_pasivo_ahorro_before[3]['saldo_final']
                datas['servicios_general_saldo']= row_pasivo_ahorro[4]['saldo_final']
                datas['servicios_general_saldo_inicial']= row_pasivo_ahorro_before[4]['saldo_final']
                datas['otros_gastos_p_saldo']= row_pasivo_ahorro[5]['saldo_final']
                datas['otros_gastos_p_saldo_inicial']= row_pasivo_ahorro_before[5]['saldo_final']
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
            suma_hacienda_publica=suma_re+row_pasivo[9]['saldo_final']*-1
            suma_hacienda_publica_si=row_pasivo_before[8]['saldo_final']+row_pasivo_before[9]['saldo_final']*-1
            datas['suma_hacienda_publica']= suma_hacienda_publica
            datas['suma_hacienda_publica_si']= suma_hacienda_publica_si
            ###
            suma_hacienda_patrimonio=suma_hacienda_publica_dona+suma_hacienda_publica
            suma_hacienda_patrimonio_si=suma_hacienda_publica_dona_si+suma_hacienda_publica_si
            datas['suma_hacienda_patrimonio']= suma_hacienda_patrimonio
            datas['suma_hacienda_patrimonio_si']= suma_hacienda_patrimonio_si
            ###
            datas['suma_pasivo_hacienda']= suma_pasivos+suma_hacienda_patrimonio
            datas['suma_pasivo_hacienda_si']= suma_pasivo_tot_si+suma_hacienda_patrimonio_si
            datas['anio_fiscal']= self.anio_fiscal
            datas['periodo_fiscal']= self.periodo
            return self.env['report'].get_action([], 'reportes.report_sf', data=datas)

        if self.reporte_select.no_reporte == 1:
            datas={}
            arr_activo=[]
            #####activo circulante#####         
            
            sql_activo_circulante="""SELECT code,account_id,ABS(saldo_inicial) AS saldo_inicial,ABS(saldo_final) AS saldo_final  FROM v_balanza WHERE anio='%s' AND periodo=%s AND account_id in (38,45,52,62,72,98,105,108,127,137,143,147,151,161,164,167,170)  order by code asc"""
            self.env.cr.execute(sql_activo_circulante % (self.anio_fiscal,self.periodo))
            row_activo_efectivo = self.env.cr.dictfetchall()

            if (self.anio_fiscal==2019):
                saldos_anio_anterior="""SELECT acc.code,csa.cuenta as account_id,csa.importe as saldo_final FROM tjacdmx_contabilidad_saldos_anuales csa
                                        inner join account_account acc on acc.id=csa.cuenta
                                        WHERE id_reporte=31 and anio='2018' and cuenta in (38,45,52,62,72,98,105,108,127,137,143,147,151,161,164,167,170)
                                        order by acc.code asc;"""
                self.env.cr.execute(saldos_anio_anterior)
            else:
                saldos_anio_anterior="""SELECT code,account_id,ABS(saldo_inicial) AS saldo_inicial,ABS(saldo_final) AS saldo_final  FROM v_balanza WHERE anio='%s' AND periodo=12 AND account_id in (38,45,52,62,72,98,105,108,127,137,143,147,151,161,164,167,170)  order by code asc"""
                self.env.cr.execute(saldos_anio_anterior % (int(self.anio_fiscal)-1))
            row_saldos_anio_anterior_activo = self.env.cr.dictfetchall()

            # sql_activo_circulante_anio_anterior="""SELECT * FROM tjacdmx_contabilidad_saldos_anuales WHERE id_reporte=31 and anio='%s' order by create_date asc;"""
            # self.env.cr.execute(sql_activo_circulante_anio_anterior % (int(self.anio_fiscal)-1))
            # row_activo_efectivo_anio_anterior = self.env.cr.dictfetchall()
            
            if (self.anio_fiscal==2019):
                sql_activo_circulante_banco="""SELECT code,account_id,saldo_inicial AS saldo_inicial,saldo_final AS saldo_final  FROM v_balanza WHERE anio='%s' AND periodo=%s AND account_id in (45)  order by code asc"""
                self.env.cr.execute(sql_activo_circulante_banco % (self.anio_fiscal,self.periodo))
                row_activo_efectivo_banco = self.env.cr.dictfetchall()

                sql_activo_circulante_banco_before="""SELECT acc.code,csa.cuenta as account_id,csa.importe as saldo_final FROM tjacdmx_contabilidad_saldos_anuales csa
                                                        inner join account_account acc on acc.id=csa.cuenta
                                                        WHERE id_reporte=31 and anio='2018' and cuenta in (45)
                                                        order by acc.code asc;"""
                self.env.cr.execute(sql_activo_circulante_banco_before)
                row_activo_efectivo_banco_before = self.env.cr.dictfetchall()
            else:
                sql_activo_circulante_banco="""SELECT code,account_id,saldo_inicial AS saldo_inicial,saldo_final AS saldo_final  FROM v_balanza WHERE anio='%s' AND periodo=%s AND account_id in (45,52)  order by code asc"""
                self.env.cr.execute(sql_activo_circulante_banco % (self.anio_fiscal,self.periodo))
                row_activo_efectivo_banco = self.env.cr.dictfetchall()

                sql_activo_circulante_banco_before="""SELECT code,account_id,saldo_inicial AS saldo_inicial,saldo_final AS saldo_final  FROM v_balanza WHERE anio='%s' AND periodo=12 AND account_id in (45,52)  order by code asc"""
                self.env.cr.execute(sql_activo_circulante_banco_before % (int(self.anio_fiscal-1)))
                row_activo_efectivo_banco_before = self.env.cr.dictfetchall()
            
            datas['efectivo_saldo']= row_activo_efectivo[0]['saldo_final'] if row_activo_efectivo[0]['saldo_final'] else 0 
            datas['efectivo_saldo_inicial']= row_saldos_anio_anterior_activo[0]['saldo_final']
            datas['bancos_tesoreria_saldo']= row_activo_efectivo_banco[0]['saldo_final']
            datas['bancos_tesoreria_saldo_inicial']= row_activo_efectivo_banco_before[0]['saldo_final']
            datas['inversiones_tesoreria_saldo']= row_activo_efectivo[2]['saldo_final']
            datas['inversiones_tesoreria_saldo_inicial']= row_activo_efectivo_banco_before[1]['saldo_final']
            suma_efectivo_bancos= row_activo_efectivo[0]['saldo_final']+row_activo_efectivo_banco[0]['saldo_final']+row_activo_efectivo[2]['saldo_final']
            suma_efectivo_bancos_si= row_saldos_anio_anterior_activo[0]['saldo_final']+row_activo_efectivo_banco_before[0]['saldo_final']+row_activo_efectivo_banco_before[1]['saldo_final']
            datas['suma_efectivo_bancos']= suma_efectivo_bancos
            datas['suma_efectivo_bancos_si']= suma_efectivo_bancos_si
            ####
            datas['cuentas_pccp_saldo']= row_activo_efectivo[3]['saldo_final']
            datas['cuentas_pccp_saldo_inicial']= row_saldos_anio_anterior_activo[3]['saldo_final']
            datas['deudores_diversos_saldo']= row_activo_efectivo[4]['saldo_final']
            datas['deudores_diversos_saldo_inicial']= row_saldos_anio_anterior_activo[4]['saldo_final']
            datas['ingreso_recuperar_cp_saldo']= row_activo_efectivo[5]['saldo_final']
            datas['ingreso_recuperar_cp_saldo_inicial']= row_saldos_anio_anterior_activo[5]['saldo_final']
            suma_derechos_recibir= row_activo_efectivo[3]['saldo_final']+row_activo_efectivo[4]['saldo_final']+row_activo_efectivo[5]['saldo_final']
            suma_derechos_recibir_si= row_saldos_anio_anterior_activo[3]['saldo_final']+row_saldos_anio_anterior_activo[4]['saldo_final']+row_saldos_anio_anterior_activo[5]['saldo_final']
            datas['suma_derechos_recibir']= suma_derechos_recibir
            datas['suma_derechos_recibir_si']=suma_derechos_recibir_si
            ####
            datas['inventario_saldo']= row_activo_efectivo[6]['saldo_final']
            datas['inventario_saldo_inicial']= row_saldos_anio_anterior_activo[6]['saldo_final']
            datas['almacen_saldo']= row_activo_efectivo[7]['saldo_final']
            datas['almacen_saldo_inicial']= row_saldos_anio_anterior_activo[7]['saldo_final']
            suma_activos_inventario= row_activo_efectivo[6]['saldo_final']+row_activo_efectivo[7]['saldo_final']
            suma_activos_inventario_si= row_saldos_anio_anterior_activo[7]['saldo_final']
            datas['suma_activos_circulantes']= suma_efectivo_bancos+suma_derechos_recibir+suma_activos_inventario
            datas['suma_activos_circulantes_si']= suma_efectivo_bancos_si+suma_derechos_recibir_si+suma_activos_inventario_si
            ####activo no circulante
            datas['mobiliario_equipo_saldo']= row_activo_efectivo[8]['saldo_final']
            datas['mobiliario_equipo_saldo_inicial']= row_saldos_anio_anterior_activo[8]['saldo_final']
            datas['mobiliario_recreativo_saldo']= row_activo_efectivo[9]['saldo_final']
            datas['mobiliario_recreativo_saldo_inicial']= row_saldos_anio_anterior_activo[9]['saldo_final']
            datas['equipo_instrumental_saldo']= row_activo_efectivo[10]['saldo_final']
            datas['equipo_instrumental_saldo_inicial']= row_saldos_anio_anterior_activo[10]['saldo_final']
            datas['equipo_trasporte_saldo']= row_activo_efectivo[11]['saldo_final']
            datas['equipo_trasporte_saldo_inicial']= row_saldos_anio_anterior_activo[11]['saldo_final']
            datas['maquinaria_otros_saldo']= row_activo_efectivo[12]['saldo_final']
            datas['maquinaria_otros_saldo_inicial']= row_saldos_anio_anterior_activo[12]['saldo_final']
            datas['coleciones_arte_saldo']= row_activo_efectivo[13]['saldo_final']
            datas['coleciones_arte_saldo_inicial']= row_saldos_anio_anterior_activo[13]['saldo_final']
            suma_bienes_inmuebles= row_activo_efectivo[8]['saldo_final']+row_activo_efectivo[9]['saldo_final']+row_activo_efectivo[10]['saldo_final']+row_activo_efectivo[11]['saldo_final']+row_activo_efectivo[12]['saldo_final']+row_activo_efectivo[13]['saldo_final']
            suma_bienes_inmuebles_si= row_saldos_anio_anterior_activo[8]['saldo_final']+row_saldos_anio_anterior_activo[9]['saldo_final']+row_saldos_anio_anterior_activo[10]['saldo_final']+row_saldos_anio_anterior_activo[11]['saldo_final']+row_saldos_anio_anterior_activo[12]['saldo_final']+row_saldos_anio_anterior_activo[13]['saldo_final']
            datas['suma_bienes_inmuebles']= suma_bienes_inmuebles
            datas['suma_bienes_inmuebles_si']= suma_bienes_inmuebles_si
            ####
            datas['software_saldo']= row_activo_efectivo[14]['saldo_final']
            datas['software_saldo_inicial']= row_saldos_anio_anterior_activo[14]['saldo_final']
            datas['licencias_info_saldo']= row_activo_efectivo[15]['saldo_final']
            datas['licencias_info_saldo_inicial']= row_saldos_anio_anterior_activo[15]['saldo_final']
            suma_activos_intangibles= row_activo_efectivo[14]['saldo_final']+row_activo_efectivo[15]['saldo_final']
            suma_activos_intangibles_si= row_saldos_anio_anterior_activo[14]['saldo_final']+row_saldos_anio_anterior_activo[15]['saldo_final']
            datas['suma_activos_intangibles']= suma_activos_intangibles
            datas['suma_activos_intangibles_si']= suma_activos_intangibles_si
            ####
            suma_depreciaciones= row_activo_efectivo[16]['saldo_final']*-1
            suma_depreciaciones_si= row_saldos_anio_anterior_activo[16]['saldo_final']*-1
            datas['suma_depreciaciones']= suma_depreciaciones
            datas['suma_depreciaciones_si']= suma_depreciaciones_si

            datas['suma_activos_no_circulantes']= suma_bienes_inmuebles+suma_activos_intangibles+suma_depreciaciones
            datas['suma_activos_no_circulantes_si']= suma_bienes_inmuebles_si+suma_activos_intangibles_si+suma_depreciaciones_si

            datas['suma_activos']= suma_efectivo_bancos+suma_derechos_recibir+suma_activos_inventario+suma_bienes_inmuebles+suma_activos_intangibles+suma_depreciaciones
            datas['suma_activos_si']= suma_efectivo_bancos_si+suma_derechos_recibir_si+suma_activos_inventario_si+suma_bienes_inmuebles_si+suma_activos_intangibles_si+suma_depreciaciones_si #####pasivo circulante#####

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
            

            datas['servicios_per_saldo']=row_pasivo[0]['saldo_final']
            datas['servicios_per_saldo_inicial']= row_pasivo_before[0]['saldo_final']
            datas['proveedor_saldo']= row_pasivo[1]['saldo_final']
            datas['proveedor_saldo_inicial']= row_pasivo_before[1]['saldo_final']
            datas['retenciones_contri']= row_pasivo[2]['saldo_final']
            datas['retenciones_contri_inicial']= row_pasivo_before[2]['saldo_final']
            datas['acreedores_dicersos_saldo']= row_pasivo[3]['saldo_final']
            datas['acreedores_dicersos_saldo_inicial']= row_pasivo_before[3]['saldo_final']
            datas['contingencias_saldo']= 0
            datas['contingencias_saldo_inicial']= 0
            suma_cuenta_pagar= row_pasivo[0]['saldo_final']+row_pasivo[1]['saldo_final']+row_pasivo[2]['saldo_final']+row_pasivo[3]['saldo_final']
            suma_cuenta_pagar_si= row_pasivo_before[0]['saldo_final']+row_pasivo_before[1]['saldo_final']+row_pasivo_before[2]['saldo_final']+row_pasivo_before[3]['saldo_final']+0
            datas['suma_cuenta_pagar']= suma_cuenta_pagar
            datas['suma_cuenta_pagar_si']= suma_cuenta_pagar_si
            datas['provisiones_cp_saldo']= row_pasivo[4]['saldo_final']
            datas['provisiones_cp_saldo_inicial']= row_pasivo_before[4]['saldo_final']
            datas['suma_pasivo_circulante']= suma_cuenta_pagar+row_pasivo[4]['saldo_final']
            datas['suma_pasivo_circulante_si']= suma_cuenta_pagar_si+row_pasivo_before[4]['saldo_final']

            ####pasivo no circulante
            datas['otras_provisiones_saldo']= row_pasivo[5]['saldo_final']
            datas['otras_provisiones_saldo_inicial']= row_pasivo_before[5]['saldo_final']
            suma_proviciones_lp=row_pasivo[5]['saldo_final']
            suma_proviciones_lp_si=row_pasivo_before[5]['saldo_final']
            datas['suma_proviciones_lp']= suma_proviciones_lp
            datas['suma_proviciones_lp_si']= suma_proviciones_lp_si
            ####
            suma_pasivo_no_cir=row_pasivo[5]['saldo_final']
            suma_pasivo_no_cir_si=row_pasivo_before[5]['saldo_final']
            datas['suma_pasivo_no_cir']= suma_pasivo_no_cir
            datas['suma_pasivo_no_cir_si']= suma_pasivo_no_cir_si
            suma_pasivos=suma_cuenta_pagar+suma_pasivo_no_cir+row_pasivo[4]['saldo_final']
            suma_pasivos_si=suma_cuenta_pagar_si+suma_pasivo_no_cir_si
            datas['suma_pasivos']= suma_cuenta_pagar+suma_pasivo_no_cir+row_pasivo[4]['saldo_final']
            suma_pasivo_tot_si=suma_cuenta_pagar_si+suma_pasivo_no_cir_si+row_pasivo_before[4]['saldo_final']
            datas['suma_pasivos_si']= suma_pasivo_tot_si

            ####hacienda publica
            datas['aportaciones_saldo']= row_pasivo[6]['saldo_final']
            datas['aportaciones_saldo_inicial']= row_pasivo_before[6]['saldo_final']
            datas['donaciones_capital_saldo']= row_pasivo[7]['saldo_final']
            datas['donaciones_capital_saldo_inicial']= row_pasivo_before[7]['saldo_final']
            suma_hacienda_publica_dona=row_pasivo[6]['saldo_final']+row_pasivo[7]['saldo_final']
            suma_hacienda_publica_dona_si=row_pasivo_before[6]['saldo_final']+row_pasivo_before[7]['saldo_final']
            datas['suma_hacienda_publica_dona']= suma_hacienda_publica_dona
            datas['suma_hacienda_publica_dona_si']= suma_hacienda_publica_dona_si
            ######
            sql_pasivo_ahorro="""SELECT code,account_id,ABS(saldo_inicial) AS saldo_inicial,ABS(saldo_final) AS saldo_final  FROM v_balanza WHERE anio='%s' AND periodo=%s AND account_id in ('333','338','356','472','558','684')"""
            self.env.cr.execute(sql_pasivo_ahorro % (self.anio_fiscal,self.periodo))
            row_pasivo_ahorro = self.env.cr.dictfetchall()
            if(self.anio_fiscal==2019):
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
            else:
                sql_pasivo_ahorro="""SELECT code,account_id,ABS(saldo_inicial) AS saldo_inicial,ABS(saldo_final) AS saldo_final  FROM v_balanza WHERE anio='%s' AND periodo=%s AND account_id in ('333','338','356','472','558','684')"""
                self.env.cr.execute(sql_pasivo_ahorro % (self.anio_fiscal,self.periodo))
                row_pasivo_ahorro = self.env.cr.dictfetchall()

                sql_pasivo_ahorro_before="""SELECT code,account_id,ABS(saldo_inicial) AS saldo_inicial,ABS(saldo_final) AS saldo_final  FROM v_balanza WHERE anio='%s' AND periodo=12 AND account_id in ('333','338','356','472','558','684')"""
                self.env.cr.execute(sql_pasivo_ahorro_before % (self.anio_fiscal-1))
                row_pasivo_ahorro_before = self.env.cr.dictfetchall()

                datas['trans_asig_saldo']= row_pasivo_ahorro[0]['saldo_final']
                datas['trans_asig_saldo_inicial']= row_pasivo_ahorro_before[0]['saldo_final']
                datas['otros_ingresos_saldo']= row_pasivo_ahorro[1]['saldo_final']
                datas['otros_ingresos_saldo_inicial']= row_pasivo_ahorro_before[1]['saldo_final']
                datas['servi_personales_saldo']= row_pasivo_ahorro[2]['saldo_final']
                datas['servi_personales_saldo_inicial']= row_pasivo_ahorro_before[2]['saldo_final']
                datas['materiales_sumi_saldo']= row_pasivo_ahorro[3]['saldo_final']
                datas['materiales_sumi_saldo_inicial']= row_pasivo_ahorro_before[3]['saldo_final']
                datas['servicios_general_saldo']= row_pasivo_ahorro[4]['saldo_final']
                datas['servicios_general_saldo_inicial']= row_pasivo_ahorro_before[4]['saldo_final']
                datas['otros_gastos_p_saldo']= row_pasivo_ahorro[5]['saldo_final']
                datas['otros_gastos_p_saldo_inicial']= row_pasivo_ahorro_before[5]['saldo_final']
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
            suma_hacienda_publica=suma_re+row_pasivo[9]['saldo_final']*-1
            suma_hacienda_publica_si=row_pasivo_before[8]['saldo_final']+row_pasivo_before[9]['saldo_final']*-1
            datas['suma_hacienda_publica']= suma_hacienda_publica
            datas['suma_hacienda_publica_si']= suma_hacienda_publica_si
            ###
            suma_hacienda_patrimonio=suma_hacienda_publica_dona+suma_hacienda_publica
            suma_hacienda_patrimonio_si=suma_hacienda_publica_dona_si+suma_hacienda_publica_si
            datas['suma_hacienda_patrimonio']= suma_hacienda_patrimonio
            datas['suma_hacienda_patrimonio_si']= suma_hacienda_patrimonio_si
            ###
            datas['suma_pasivo_hacienda']= suma_pasivos+suma_hacienda_patrimonio
            datas['suma_pasivo_hacienda_si']= suma_pasivo_tot_si+suma_hacienda_patrimonio_si
            datas['anio_fiscal']= self.anio_fiscal
            datas['anio_fiscal_anterior']= self.anio_fiscal-1
            datas['periodo_fiscal']= self.periodo
            return self.env['report'].get_action([], 'reportes.sfcomp', data=datas)
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
            return self.env['report'].get_action([], 'reportes.estado_actividades_v2', data=datas)
        if self.reporte_select.no_reporte == 3:
            datas = {}
            res = self.read(['periodo','anio_fiscal'])
            res = res and res[0] or {}
            if self.periodo and self.anio_fiscal:
                self.env.cr.execute("""SELECT 
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
                            '684' )""" % (self.periodo, self.anio_fiscal))
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
            return self.env['report'].get_action([], 'reportes.report_estado_cambios_situacion_financiera', data=datas)
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
                sql_activo = """SELECT code,account_id,sum(debe) as debe,sum(haber) as haber FROM v_balanza 
                                WHERE anio='%s' AND 
                                periodo between 1 and %s AND account_id in (35, 36, 37, 38, 45, 52, 58, 61, 62, 72, 98, 108, 116, 117, 118, 126, 127, 137, 143, 147, 151, 161, 163, 164, 166, 170) group by 1,2;"""
                self.env.cr.execute(sql_activo % (self.anio_fiscal,self.periodo))
                rows_sql = self.env.cr.dictfetchall()
                ids=[]
                for i in rows_sql:
                    sql_activo = """SELECT ABS(saldo_final) AS saldo_final FROM v_balanza WHERE anio='%s' AND periodo=%s AND account_id=%s limit 1"""
                    self.env.cr.execute(sql_activo % (self.anio_fiscal-1,int(12),int(i['account_id'])))
                    rows_sql_si = self.env.cr.dictfetchall()
                    saldo_inicial=rows_sql_si[0]['saldo_final'] if rows_sql_si[0]['saldo_final'] else 0
                    query_r = {
                        'account_id': i['account_id'],
                        'code': i['code'],
                        'saldo_inicial': saldo_inicial,
                        'saldo_final': saldo_inicial+i['debe']-i['haber'],
                        'debe': i['debe'],
                        'haber': i['haber']
                    }
                    ids.append(query_r)
                ids_banco=[]
                for i in row_activo_efectivo_banco:
                    sql_activo = """SELECT ABS(saldo_final) AS saldo_final FROM v_balanza WHERE anio='%s' AND periodo=%s AND account_id=%s limit 1"""
                    self.env.cr.execute(sql_activo % (self.anio_fiscal-1,int(12),int(i['account_id'])))
                    rows_sql_si = self.env.cr.dictfetchall()
                    saldo_inicial=rows_sql_si[0]['saldo_final'] if rows_sql_si[0]['saldo_final'] else 0
                    query_banco = {
                        'account_id': i['account_id'],
                        'code': i['code'],
                        'saldo_inicial': saldo_inicial,
                        'saldo_final': saldo_inicial+i['debe']-i['haber'],
                    }
                    ids_banco.append(query_banco)
            datas['query_estado'] = ids
            datas['query_bancos'] = ids_banco
            datas['form'] = res
            return self.env['report'].get_action([], 'reportes.report_v2_estado_analitico_activo', data=datas)
        # Reporte Financiero - Estado de Variaciones en la Hacienda Publica / Patrimonio
        elif self.reporte_select.no_reporte == 7:
            datas = {}
            res = self.read(['periodo','anio_fiscal'])
            res = res and res[0] or {}
            if self.periodo and self.anio_fiscal:
                if(self.anio_fiscal==2019):
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
                else:
                    sql_pasivo="""SELECT code,account_id,ABS(saldo_inicial) AS saldo_inicial,ABS(saldo_final) AS saldo_final  FROM v_balanza WHERE anio='%s' AND periodo=%s AND account_id in (291,312,318,2635,333,338,356,472,558,684)"""
                    self.env.cr.execute(sql_pasivo % (self.anio_fiscal,self.periodo))
                    rows_sql = self.env.cr.dictfetchall()
                    sql_pasivo_before="""SELECT code,account_id,ABS(saldo_inicial) AS saldo_inicial,ABS(saldo_final) AS saldo_final  FROM v_balanza WHERE anio='%s' AND periodo=12 AND account_id in (291,312,318,2635,333,338,356,472,558,684)"""
                    self.env.cr.execute(sql_pasivo_before % (self.anio_fiscal-1))
                    rows_sql_before = self.env.cr.dictfetchall()
                    ids=[]
                    for i in rows_sql:
                        query_r = {
                            'account_id': i['account_id'],
                            'code': i['code'],
                            'saldo_inicial': i['saldo_inicial'],
                            'saldo_final': i['saldo_final']
                        }
                        ids.append(query_r)
                    ids2=[]
                    for i in rows_sql_before:
                        query_r2 = {
                            'account_id': i['account_id'],
                            'code': i['code'],
                            'saldo_inicial': i['saldo_inicial'],
                            'saldo_final': i['saldo_final']
                        }
                        ids2.append(query_r2)
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
            datas['query_estado_before'] = ids2
            datas['form'] = res
            #
            return self.env['report'].get_action([], 'reportes.report_v2_estado_variaciones_hp', data=datas)
        elif self.reporte_select.no_reporte == 8:
            periodo_anterior=self.periodo
            datas = {}
            datas['anio_fiscal']= self.anio_fiscal
            datas['periodo_fiscal']= self.periodo
            datas['anio_fiscal_anterior']= self.anio_fiscal-1
            sql_ejercicio="""SELECT account_id,ABS(saldo_final) AS saldo FROM v_balanza 
                            WHERE anio='%s' 
                            AND periodo=%s
                            AND account_id in (334,338,356,472,558,290,108,312,185,291);"""
            self.env.cr.execute(sql_ejercicio % (self.anio_fiscal,self.periodo))
            row_ejercicio = self.env.cr.dictfetchall()
            sql_ejercicio_anterior ="""SELECT account_id,ABS(saldo_final) AS saldo FROM v_balanza 
                            WHERE anio='%s' 
                            AND periodo=%s
                            AND account_id in (334,338,356,472,558,290,108,312,185,291);"""
            self.env.cr.execute(sql_ejercicio_anterior  % (self.anio_fiscal-1,12))
            row_ejercicio_anterior  = self.env.cr.dictfetchall()

            saldos_ejercicio_cuentas=[]
            saldos_ejercicio_anterior_cuentas=[]
            # ------Saldos origen Flujos Netos de Efectivo por Actividades de Inversion
            if(self.anio_fiscal==2020):
                sql_1 ="""SELECT SUM(csa.importe) as saldo FROM tjacdmx_contabilidad_saldos_anuales csa
                                        inner join account_account acc on acc.id=csa.cuenta
                                        WHERE id_reporte=31 and anio='2018' and cuenta in (62,72,98,108);"""
                self.env.cr.execute(sql_1)
            else:
                sql_1="""SELECT SUM(ABS(saldo_final)) AS saldo  FROM v_balanza WHERE anio='%s' AND periodo=12 AND account_id in (62,72,98,108);"""
                self.env.cr.execute(sql_1 % (self.anio_fiscal-1))
            row_sql1  = self.env.cr.dictfetchall()
            sum2018=row_sql1[0]['saldo'] if row_sql1 else 0
            sql_2 ="""SELECT SUM(ABS(saldo_final)) AS saldo  FROM v_balanza
                        WHERE anio='%s' AND periodo=%s AND account_id in (62,72,98,108);"""
            self.env.cr.execute(sql_2  % (self.anio_fiscal,self.periodo))
            row_sql2  = self.env.cr.dictfetchall()
            sum1=row_sql2[0]['saldo'] if row_sql2 else 0
            sql_3 ="""SELECT SUM(ABS(saldo_final)) AS saldo  FROM v_balanza
                        WHERE anio='%s' AND periodo=%s AND account_id in (62,72,98,108);"""
            self.env.cr.execute(sql_3  % (self.anio_fiscal-1,12))
            row_sql3  = self.env.cr.dictfetchall()
            sum2=row_sql3[0]['saldo'] if row_sql3 else 0
             # ------Saldos origen Flujos Netos de Efectivo por Actividades de Inversion fin
             # ------Saldos APLICACIon Flujos Netos de Efectivo por Actividades de Inversion
            if(self.anio_fiscal==2020):
                sql_4 ="""SELECT SUM(csa.importe) as saldo FROM tjacdmx_contabilidad_saldos_anuales csa
                                        inner join account_account acc on acc.id=csa.cuenta
                                        WHERE id_reporte=31 and anio='2018' and cuenta in (186,226,253,275,277,283);"""
                self.env.cr.execute(sql_4)
            else:
                sql_4="""SELECT SUM(ABS(saldo_final)) AS saldo  FROM v_balanza WHERE anio='%s' AND periodo=12 AND account_id in (186,226,253,275,277,283);"""
                self.env.cr.execute(sql_4 % (self.anio_fiscal-1))
            row_sql4  = self.env.cr.dictfetchall()
            sum_a2018=row_sql4[0]['saldo'] if row_sql4 else 0
            sql_5 ="""SELECT SUM(ABS(saldo_final)) AS saldo  FROM v_balanza
                        WHERE anio='%s' AND periodo=%s AND account_id in (186,226,253,275,277,283);"""
            self.env.cr.execute(sql_5  % (self.anio_fiscal,self.periodo))
            row_sql5  = self.env.cr.dictfetchall()
            sum_a1=row_sql5[0]['saldo'] if row_sql5 else 0
            sql_6 ="""SELECT SUM(ABS(saldo_final)) AS saldo  FROM v_balanza
                        WHERE anio='%s' AND periodo=%s AND account_id in (186,226,253,275,277,283);"""
            self.env.cr.execute(sql_6  % (self.anio_fiscal-1,12))
            row_sql6  = self.env.cr.dictfetchall()
            sum_a2=row_sql6[0]['saldo'] if row_sql6 else 0
             # ------Saldos APLICACIon Flujos Netos de Efectivo por Actividades de Inversion fin

            # --- datos de mes anterior suma de bancos 
            if(self.anio_fiscal==2020):
                sql_7 ="""SELECT SUM(csa.importe) as saldo FROM tjacdmx_contabilidad_saldos_anuales csa
                                        inner join account_account acc on acc.id=csa.cuenta
                                        WHERE id_reporte=25 and anio='2018' and cuenta in (38,45,52);"""
                self.env.cr.execute(sql_7)
            else:
                sql_7="""SELECT SUM(ABS(saldo_final)) AS saldo  FROM v_balanza WHERE anio='%s' AND periodo=12 AND account_id in (38,45,52);"""
                self.env.cr.execute(sql_7 % (self.anio_fiscal-1))
            row_sql7  = self.env.cr.dictfetchall()
            sum_a_ef2018=row_sql7[0]['saldo'] if row_sql7 else 0


            saldos_ejercicio=[]
            saldos_ejercicio_anterior=[]
            for i in row_ejercicio:
                query_r = {
                    'cuenta': i['account_id'],
                    'saldo': i['saldo']
                }
                saldos_ejercicio.append(query_r)
            for i in row_ejercicio_anterior:
                query_ra = {
                    'cuenta': i['account_id'],
                    'saldo': i['saldo']
                }
                saldos_ejercicio_anterior.append(query_ra)
            
            datas['saldos_ejercicio_or'] = float('0')
            datas['saldos_ejercicio_or_anterior'] = float('1929812')
            datas['saldos_ejercicio_aplic']=float('0')
            datas['saldos_ejercicio_aplic_anterior']=float('1929812')
            datas['saldos_ejercicio_aplic2']=float('38371163')
            datas['saldos_ejercicio_aplic_anterior2']=float('41204638')
            
            datas['saldos_ejercicio'] = saldos_ejercicio
            datas['saldos_ejercicio_anterior'] = saldos_ejercicio_anterior
            datas['saldo_AOOF']=float(sum1-sum2)
            datas['saldo_AOOF_si']=float(sum2-sum2018)

            datas['saldo_OOOF']=float(sum_a2-sum_a1)
            datas['saldo_OOOF_si']=float(sum_a2018-sum_a2) 
            datas['saldo_EEEIE']=float(sum_a_ef2018)             
            # raise UserError(_('Debug: %s----------%s' % (saldos_ejercicio,saldos_ejercicio_anterior)))
            return self.env['report'].get_action([], 'reportes.report_v2_estado_flujos_efectivo', data=datas)
        elif self.reporte_select.no_reporte == 9:
            datas={}
            
            return self.env['report'].get_action([], 'reportes.report_notas_estados_financieros', data=datas)