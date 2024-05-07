# -*- coding: utf-8 -*-
from datetime import date
from datetime import datetime
from odoo import api, fields, models, _, tools
from odoo.exceptions import ValidationError
from . import configuracion, catalogos
from dateutil.parser import parse

obtener_nombre = lambda x: x[0][1]
TIPO_UP = [(str(1), 'No'),(str(2),'Si'),(str(3),'Bimestre'),(str(4), 'Ajuste -'),(str(5), 'Remanente')]
STATUS_DOC = [('close', 'Sin validar'),('open','Validado')]

class Documento(models.Model):
    _name = 'presupuesto.documento'
    _description = "Documento"
    _order = 'id desc'
    _inherit = ['mail.thread']

    clase_documento = fields.Many2one('presupuesto.clase_documento', string=u'Clase documento', required=True,track_visibility='onchange')
    version = fields.Many2one('presupuesto.version', string=u'Versión',default='0', required=True,track_visibility='onchange')
    fecha_documento = fields.Date(string='Fecha de documento', required=True, default=fields.Datetime.now,track_visibility='onchange')
    fecha_contabilizacion = fields.Date(string='Fecha de contabilizacion', required=True, default=fields.Datetime.now,track_visibility='onchange')
    # generar numero de años automaticamente
    ejercicio = fields.Selection(catalogos.EJERCICIO_SELECT, required=True,track_visibility='onchange')
    # generar numero de meses automaticamente
    periodo = fields.Selection(catalogos.PERIODO_SELECT, required=True,track_visibility='onchange')
    periodo_origen = fields.Selection(catalogos.PERIODO_SELECT)
    detalle_documento_ids = fields.One2many('presupuesto.detalle_documento', 'documento_id',string='Detalle',copy=True,track_visibility='onchange')

    checar_referencia = fields.Char(string='checar_referencia', compute='_checar_referencia')
    referencia_compra = fields.Many2one('purchase.order', string='Referencia', readonly=True)
    referencia_factura = fields.Many2one('account.invoice', string='Referencia', readonly=True)
    referencia_pago = fields.Many2one('account.payment', string='Referencia', readonly=True)
    compra_id = fields.Many2one('purchase.order',string='Compra')
    partida_presupuestal=fields.Char(string='Partida', store=True)
    importe=fields.Char(string='Importe',track_visibility='onchange')
    status_rem=fields.Char(string='Estatus de arrastre', default='open')
    tipo=fields.Char(string='Tipo documento',track_visibility='onchange')
    status=fields.Selection(STATUS_DOC,string='Estatus', default='open',track_visibility='onchange')
    check_dev_comp=fields.Boolean(string='Devengado y Comprometido')
    clase_documento_ajuste = fields.Many2one('presupuesto.clase_documento', string=u'Clase documento', required=True)
    is_periodo_anterior = fields.Selection(TIPO_UP, string='Registro Periodo Anterior')
    concepto=fields.Char(string='Concepto',track_visibility='onchange')
    id_nomina=fields.Integer(string='No. Nomina')
    move_id = fields.One2many('account.move','documento_id', string='Asientos contables',track_visibility='onchange')
    remision_id= fields.Integer(string='Remision')
    
    
    def _compute_total(self):
        t=0
        for each in self.detalle_documento_ids:
            t=t+each.importe
        self.importe_total=t
        
    importe_total=fields.Float(string='Importe', digits=(15, 2), compute='_compute_total', default=0)
    
    @api.onchange('fecha_documento')
    def _set_dates_fields(self):
        fecha = datetime.strptime(str(self.fecha_documento), '%Y-%m-%d')
        
        self.update({'fecha_contabilizacion': fecha})
        self.update({'periodo': str(fecha.month)})
        self.update({'ejercicio': str(fecha.year)})
        
    def _compute_partida(self):
        #self.partida_presupuestal
        print ('s')

    @api.depends('clase_documento')
    def _checar_referencia(self):
        for record in self:
            record.checar_referencia = '%s' % record.clase_documento.tipo_documento

    
    def name_get(self):
        # partida= self.detalle_documento_ids[0].posicion_presupuestaria.partida_presupuestal if self.detalle_documento_ids[0].posicion_presupuestaria.partida_presupuestal else 0
        result = []
        for doc in self:
            name = 'Documento No. %s - %s- %s  ' % (doc.id,doc.clase_documento.nombre,doc.concepto)
            result.append((doc.id, name))
        return result

    
    def button_state_off(self):
        obj_am = self.env['account.move']
        am = obj_am.search([('documento_id', '=', self.id),('state', '=', 'posted')], limit=1)
        ctrl_periodo = self.env['control.periodos.wizard']
        if(ctrl_periodo.get_is_cerrado(self.fecha_documento)):
            raise ValidationError('No se permite modificar documentos de un periodo presupuestalmente cerrado')
        else:
            self.write({ 'status': 'close' })
            am.write({ 'state': 'draft' })
        
    
    
    def button_state_on(self):
        obj_am = self.env['account.move']
        obj_aml = self.env['account.move.line']
        ctrl_periodo = self.env['control.periodos.wizard']
        doc_line = self.detalle_documento_ids
        amon = obj_am.search([('documento_id', '=', self.id)], limit=1,order='create_date desc')
        amlon = obj_aml.search([('move_id', '=', amon.id)])
        suma_lines=0
        line_ids = []
        code_journal_change=""
        if(ctrl_periodo.get_is_cerrado(self.fecha_documento)):
            raise ValidationError('No se permite modificar documentos de un periodo presupuestalmente cerrado')
        else:
            for line in self.detalle_documento_ids:
                co = self.env['presupuesto.cuenta_orden'].search([('posicion_presupuestaria', '=', line.posicion_presupuestaria.id)])
                suma_lines=suma_lines+line.importe
                co_egreso = [0,False,{
                            'analytic_account_id': False,
                            'currency_id': False,
                            'credit': 0,
                            'date_maturity': self.fecha_contabilizacion,
                            'debit': abs(line.importe),
                            'amount_currency': 0,
                            'partner_id': False,
                            'name': 'presupuesto'
                        }]
                co_ingreso = [0,False,{
                        'analytic_account_id': False,
                        'currency_id': False,
                        'credit': abs(line.importe),
                        'date_maturity': self.fecha_contabilizacion,
                        'debit': 0,
                        'amount_currency': 0,
                        'partner_id': False,
                        'name': 'presupuesto'
                    }]
                if (self.clase_documento.tipo_documento == 'COMPROMETIDO'):
                    # raise ValidationError('debug: %s ' % (self.clase_documento))
                    co_egreso[2]['account_id'] = co.cta_orden_comprometido_egreso.id
                    co_ingreso[2]['account_id'] = co.cta_orden_original_egreso.id
                    jurnal_select="COPC"
                elif (self.clase_documento.tipo_documento == 'DEVENGADO'):
                    co_egreso[2]['account_id'] = co.cta_orden_devengado_egreso.id
                    co_ingreso[2]['account_id'] = co.cta_orden_comprometido_egreso.id
                    jurnal_select="COPD"
                elif (self.clase_documento.tipo_documento == 'EJERCIDO'):
                    co_egreso[2]['account_id'] = co.cta_orden_ejercido_egreso.id
                    co_ingreso[2]['account_id'] = co.cta_orden_devengado_egreso.id
                    jurnal_select="COPE"
                elif (self.clase_documento.tipo_documento == 'PAGADO'):
                    co_egreso[2]['account_id'] = co.cta_orden_pagado_egreso.id
                    co_ingreso[2]['account_id'] = co.cta_orden_ejercido_egreso.id
                    jurnal_select="COPP"
                elif (self.clase_documento.tipo_documento == 'RECLASIFICACION'):
                    co_egreso[2]['account_id'] = co.cta_orden_modificado_ingreso.id
                    co_ingreso[2]['account_id'] = co.cta_orden_modificado_egreso.id
                    jurnal_select="COPRR"
                elif (self.clase_documento.tipo_documento == 'REDUCCION'):
                    co_egreso[2]['account_id'] = co.cta_orden_modificado_ingreso.id
                    co_ingreso[2]['account_id'] = co.cta_orden_modificado_egreso.id
                    jurnal_select="COPR"
                        
                line_ids.append(co_egreso)
                line_ids.append(co_ingreso)
                code_journal_change=jurnal_select
            
            journal = self.env['account.journal'].search([('code', '=', code_journal_change)], limit=1)
            sum1='{0:.2f}'.format(float(suma_lines))
            sum2='{0:.2f}'.format(float(amon.amount))
            if(sum1==sum2):
                amon.post()
            else:
                poliza = obj_am.create({
                    'journal_id': journal.id,
                    'date': self.fecha_contabilizacion,
                    'ref': str(self.id),
                    'documento_id':self.id,
                    'narration':False,
                    'line_ids':line_ids,
                    'compra_id':self.compra_id.id
                })
                poliza.post()
            self.write({ 'status': 'open' })

    @api.constrains('detalle_documento_ids', 'clase_documento', 'version', 'ejercicio', 'periodo','periodo_origen', 'is_periodo_anterior')
    def _validate_llave_importe(self):
        obj_cp = self.env['presupuesto.control_presupuesto']
        obj_documento_origin = self.env['presupuesto.documento']
        obj_documento_detalle_origin = self.env['presupuesto.detalle_documento']
        if self.is_periodo_anterior == 2:
            for item in self:
                for detalle in item.detalle_documento_ids:
                    cp = obj_cp.search([
                        ('ejercicio', '=', item.ejercicio),
                        ('periodo', '=', item.periodo_origen),
                        ('version', '=', item.version.id),
                        ('fondo_economico', '=', detalle.fondo_economico.id),
                        ('posicion_presupuestaria', '=', detalle.posicion_presupuestaria.id),
                        ('centro_gestor', '=', detalle.centro_gestor.id),
                        ('area_funcional', '=', detalle.area_funcional.id)
                    ])
                    #raise ValidationError(cp.egreso_devengado)
                    if cp:
                        if item.clase_documento.id == 9:
                            if detalle.importe > cp.egreso_devengado:
                                raise ValidationError("El importe que intenta reducir es mayor al disponible para el momento ejercido del periodo anterior(%s)" % (cp.egreso_devengado))
                        elif item.clase_documento.id == 8:
                            if detalle.importe > cp.egreso_ejercido:
                                raise ValidationError("El importe que intenta reducir es mayor al disponible para el pagado del periodo anterior(%s)" % (cp.egreso_ejercido))
        elif self.is_periodo_anterior == 3:
            for item in self:
                for detalle in item.detalle_documento_ids:
                    cpo = obj_cp.search([
                        ('ejercicio', '=', item.ejercicio),
                        ('periodo', '=', item.periodo),
                        ('version', '=', item.version.id),
                        ('fondo_economico', '=', detalle.fondo_economico.id),
                        ('posicion_presupuestaria', '=', detalle.posicion_presupuestaria.id),
                        ('centro_gestor', '=', detalle.centro_gestor.id),
                        ('area_funcional', '=', detalle.area_funcional.id)
                    ])
                    cpb = obj_cp.search([
                        ('ejercicio', '=', item.ejercicio),
                        ('periodo', '=', item.periodo_origen),
                        ('version', '=', item.version.id),
                        ('fondo_economico', '=', detalle.fondo_economico.id),
                        ('posicion_presupuestaria', '=', detalle.posicion_presupuestaria.id),
                        ('centro_gestor', '=', detalle.centro_gestor.id),
                        ('area_funcional', '=', detalle.area_funcional.id)
                    ])
                    devengado = cpo.egreso_devengado + cpb.egreso_devengado
                    if cpo:
                        if item.clase_documento.id == 9:
                            #raise ValidationError(round(devengado,2))
                            if detalle.importe > devengado:
                                raise ValidationError("El importe que intenta reducir es mayor al disponible para el momento ejercido(%s)" % (devengado))
        elif self.is_periodo_anterior == 1:
            if(self.status=='open'):
            #raise ValidationError('debug')
                for item in self:
                    for detalle in item.detalle_documento_ids:
                        cp = obj_cp.search([
                            ('ejercicio', '=', item.ejercicio),
                            ('periodo', '=', item.periodo),
                            ('version', '=', item.version.id),
                            ('fondo_economico', '=', detalle.fondo_economico.id),
                            ('posicion_presupuestaria', '=', detalle.posicion_presupuestaria.id),
                            ('centro_gestor', '=', detalle.centro_gestor.id),
                            ('area_funcional', '=', detalle.area_funcional.id)
                        ])
                        doc_origin_search = obj_documento_origin.search([
                            ('ejercicio', '=', self.ejercicio),
                            ('periodo', '=', self.periodo),
                            ('clase_documento', '=', 3),
                            ('id', '!=', self.id),
                        ])
                        lista_docs=[]
                        for documentos in doc_origin_search:
                            linea=obj_documento_detalle_origin.search([('documento_id', '=', documentos.id),], limit=1)
                            partida = [0,False,{
                            'docuemnto_id':  documentos.id,
                            'posicion_presupuestaria': linea.posicion_presupuestaria.id,
                            }]
                            if(linea and item.clase_documento.id==3):
                                if(item.status=='open'):
                                    if(linea.posicion_presupuestaria.id==detalle.posicion_presupuestaria.id):
                                        lista_docs.append(partida)
                        if cp:
                            if lista_docs:
                                raise ValidationError("No se puede crear el documento original, ya existe! %s " % (lista_docs))
                            elif item.clase_documento.signo == '-':
                                sql_origen = """SELECT id,posicion_presupuestaria,SUM(aprobado) as aprobado,SUM(remanente) as remanente, SUM(reduccion) as reduccion,SUM(ampliacion) as ampliacion,SUM(modificado) as modificado,SUM(comprometido) as comprometido,SUM(devengado) as devengado,SUM(ejercido) as ejercido,SUM(pagado) as pagado
                                                FROM presupuestos_view_cp_operativo
                                                WHERE posicion_presupuestaria=%s and periodo=%s and periodo_origen=%s and ejercicio='%s' 
                                                GROUP by 1,2 limit 1"""
                                self.env.cr.execute(sql_origen % (detalle.posicion_presupuestaria.id,item.periodo_origen,item.periodo_origen, self.ejercicio))
                                importe_disponible_origen = self.env.cr.dictfetchall()
                                saldos_partida=[]
                                sql_destinos = """SELECT id,posicion_presupuestaria,SUM(aprobado) as aprobado,SUM(remanente) as remanente, SUM(reduccion) as reduccion,SUM(ampliacion) as ampliacion,SUM(modificado) as modificado,SUM(comprometido) as comprometido,SUM(devengado) as devengado,SUM(ejercido) as ejercido,SUM(pagado) as pagado
                                                FROM presupuestos_view_cp_operativo
                                                WHERE posicion_presupuestaria=%s and periodo=%s and periodo_origen=%s and ejercicio='%s' 
                                                GROUP by 1,2 limit 1"""
                                self.env.cr.execute(sql_destinos % (detalle.posicion_presupuestaria.id,item.periodo,item.periodo, self.ejercicio))
                                importe_disponible_destinos = self.env.cr.dictfetchall()
                                for i in importe_disponible_origen:
                                    movimientos = {
                                        'id': i['id'],
                                        'posicion_presupuestaria': i['posicion_presupuestaria'],
                                        'remanente': i['remanente'],
                                        'aprobado': i['aprobado'],
                                        'reduccion': i['reduccion'],
                                        'ampliacion': i['ampliacion'],
                                        'modificado': i['modificado'],
                                        'comprometido': i['comprometido'],
                                        'devengado': i['devengado'],
                                        'ejercido': i['ejercido'],
                                        'pagado': i['pagado']
                                        }
                                    saldos_partida.append(movimientos)
                                saldos_partida_destino=[]
                                for it2 in importe_disponible_destinos:
                                    if(it2['id']):
                                        movimientos_des = {
                                            'id': it2['id'],
                                            'posicion_presupuestaria': it2['posicion_presupuestaria'],
                                            'remanente': it2['remanente'],
                                            'aprobado': it2['aprobado'],
                                            'reduccion': it2['reduccion'],
                                            'ampliacion': it2['ampliacion'],
                                            'modificado': it2['modificado'],
                                            'comprometido': it2['comprometido'],
                                            'devengado': it2['devengado'],
                                            'ejercido': it2['ejercido'],
                                            'pagado': it2['pagado']
                                            }
                                        saldos_partida_destino.append(movimientos_des)
                                importe_mov=float(detalle.importe)
                                if (saldos_partida_destino):
                                    if item.clase_documento.id==6:
                                        dis_cp=float(saldos_partida[0]['remanente'])+float(saldos_partida[0]['ampliacion'])+float(saldos_partida[0]['modificado'])-float(saldos_partida[0]['comprometido'])
                                        if float(round(importe_mov,2)) > float(round(dis_cp,2)):
                                            print('salida')
                                            #raise ValidationError("El importe que intenta reducir es mayor al disponible (%s): original disponible (%s), se intenta comprometer (%s)" % (detalle.posicion_presupuestaria.partida_presupuestal,float(round(dis_cp,2)),float(round(importe_mov,2))))
                                    elif item.clase_documento.id == 7:
                                        dis_cp=float(saldos_partida[0]['comprometido'])-float(saldos_partida_destino[0]['devengado'])
                                        if float(round(importe_mov,2)) > float(round(dis_cp,2)):
                                            print('salida')
                                            #raise ValidationError("El importe que intenta reducir es mayor al disponible (%s): devengado disponible (%s), se intenta devengar (%s)" % (detalle.posicion_presupuestaria.partida_presupuestal,float(round(dis_cp,2)),float(round(importe_mov,2))))
                                    elif item.clase_documento.id ==9:
                                        dis_cp=float(saldos_partida[0]['devengado'])-float(saldos_partida_destino[0]['ejercido'])
                                        if float(round(importe_mov,2)) > float(round(dis_cp,2)):
                                            print('salida')
                                            #raise ValidationError("El importe que intenta reducir es mayor al disponible (%s): ejercido disponible (%s), se intenta ejercer (%s)" % (detalle.posicion_presupuestaria.partida_presupuestal,float(round(dis_cp,2)),float(round(importe_mov,2))))
                                    elif item.clase_documento.id  == 8:
                                        dis_cp=float(saldos_partida[0]['ejercido'])-float(saldos_partida_destino[0]['pagado'])
                                        if float(round(importe_mov,2)) > float(round(dis_cp,2)):
                                            print('salida')
                                            #raise ValidationError("El importe que intenta reducir es mayor al disponible (%s): pagado disponible (%s), se intenta pagar (%s)" % (detalle.posicion_presupuestaria.partida_presupuestal,float(round(dis_cp,2)),float(round(importe_mov,2))))
                                else:
                                    raise ValidationError("No se encontro documento original para esta partida (%s) para el periodo (%s)" % (detalle.posicion_presupuestaria.partida_presupuestal,item.periodo))
        
                        elif item.clase_documento.tipo_documento != 'ORIGINAL':
                            raise ValidationError("Se encontró un posible problema \n Razones: \n 1. No se tiene cargado presupuesto para este periodo.\n 2. No existe una cuanta de orden relacionada a esta partida. \n 3. No se tiene registrada esta partida.")

                        co = self.env['presupuesto.cuenta_orden'].search([('posicion_presupuestaria', '=', detalle.posicion_presupuestaria.id)])
                        if not co:
                            raise ValidationError('No existe la cuenta de orden  relacionada a esta partida(s) ')
            else:
                print('draft')
        elif self.is_periodo_anterior == 5:
            for item in self:
                for detalle in item.detalle_documento_ids:
                    cp = obj_cp.search([
                        ('ejercicio', '=', item.ejercicio),
                        ('periodo', '=', item.periodo_origen),
                        ('version', '=', item.version.id),
                        ('fondo_economico', '=', detalle.fondo_economico.id),
                        ('posicion_presupuestaria', '=', detalle.posicion_presupuestaria.id),
                        ('centro_gestor', '=', detalle.centro_gestor.id),
                        ('area_funcional', '=', detalle.area_funcional.id)
                    ])
        else:
            if(self.status=='open'):
                for item in self:
                    for detalle in item.detalle_documento_ids:
                        cp = obj_cp.search([
                            ('ejercicio', '=', item.ejercicio),
                            ('periodo', '=', item.periodo_origen),
                            ('version', '=', item.version.id),
                            ('fondo_economico', '=', detalle.fondo_economico.id),
                            ('posicion_presupuestaria', '=', detalle.posicion_presupuestaria.id),
                            ('centro_gestor', '=', detalle.centro_gestor.id),
                            ('area_funcional', '=', detalle.area_funcional.id)
                        ])
                        if cp:
                            if item.clase_documento.tipo_documento == 'ORIGINAL':
                                raise ValidationError("No se puede crear el documento original, ya existe! %s" % (item))
                            elif item.clase_documento.signo == '-':
                                sql_origen_alt = """SELECT id,posicion_presupuestaria,SUM(aprobado) as aprobado,SUM(remanente) as remanente, SUM(reduccion) as reduccion,SUM(ampliacion) as ampliacion,SUM(modificado) as modificado,SUM(comprometido) as comprometido,SUM(devengado) as devengado,SUM(ejercido) as ejercido,SUM(pagado) as pagado
                                                FROM presupuestos_view_cp_operativo
                                                WHERE posicion_presupuestaria=%s and periodo=%s and periodo_origen=%s and ejercicio='%s' 
                                                GROUP by 1,2 limit 1"""
                                self.env.cr.execute(sql_origen_alt % (detalle.posicion_presupuestaria.id,item.periodo,item.periodo_origen, self.ejercicio))
                                importe_disponible_origen_alt = self.env.cr.dictfetchall()
                                saldos_partida_alt=[]
                                for i in importe_disponible_origen_alt:
                                    movimientos = {
                                        'id': i['id'],
                                        'posicion_presupuestaria': i['posicion_presupuestaria'],
                                        'remanente': i['remanente'],
                                        'aprobado': i['aprobado'],
                                        'reduccion': i['reduccion'],
                                        'ampliacion': i['ampliacion'],
                                        'modificado': i['modificado'],
                                        'comprometido': i['comprometido'],
                                        'devengado': i['devengado'],
                                        'ejercido': i['ejercido'],
                                        'pagado': i['pagado']
                                        }
                                    saldos_partida_alt.append(movimientos)
                                sql_origen = """SELECT id,posicion_presupuestaria,SUM(aprobado) as aprobado,SUM(remanente) as remanente, SUM(reduccion) as reduccion,SUM(ampliacion) as ampliacion,SUM(modificado) as modificado,SUM(comprometido) as comprometido,SUM(devengado) as devengado,SUM(ejercido) as ejercido,SUM(pagado) as pagado
                                                FROM presupuestos_view_cp_operativo
                                                WHERE posicion_presupuestaria=%s and periodo=%s and periodo_origen=%s and ejercicio='%s' 
                                                GROUP by 1,2 limit 1"""
                                self.env.cr.execute(sql_origen % (detalle.posicion_presupuestaria.id,item.periodo_origen,item.periodo_origen, self.ejercicio))
                                importe_disponible_origen = self.env.cr.dictfetchall()
                                
                                saldos_partida=[]
                                sql_destinos = """SELECT id,posicion_presupuestaria,SUM(aprobado) as aprobado,SUM(remanente) as remanente, SUM(reduccion) as reduccion,SUM(ampliacion) as ampliacion,SUM(modificado) as modificado,SUM(comprometido) as comprometido,SUM(devengado) as devengado,SUM(ejercido) as ejercido,SUM(pagado) as pagado
                                                FROM presupuestos_view_cp_operativo
                                                WHERE posicion_presupuestaria=%s and periodo=%s and periodo_origen=%s and ejercicio='%s' 
                                                GROUP by 1,2 limit 1"""
                                self.env.cr.execute(sql_destinos % (detalle.posicion_presupuestaria.id,item.periodo,item.periodo, self.ejercicio))
                                importe_disponible_destinos = self.env.cr.dictfetchall()
                                for i in importe_disponible_origen:
                                    movimientos = {
                                        'id': i['id'],
                                        'posicion_presupuestaria': i['posicion_presupuestaria'],
                                        'remanente': i['remanente'],
                                        'aprobado': i['aprobado'],
                                        'reduccion': i['reduccion'],
                                        'ampliacion': i['ampliacion'],
                                        'modificado': i['modificado'],
                                        'comprometido': i['comprometido'],
                                        'devengado': i['devengado'],
                                        'ejercido': i['ejercido'],
                                        'pagado': i['pagado']
                                        }
                                    saldos_partida.append(movimientos)
                                saldos_partida_destino=[]
                                for it2 in importe_disponible_destinos:
                                    if(it2['id']):
                                        movimientos_des = {
                                            'id': it2['id'],
                                            'posicion_presupuestaria': it2['posicion_presupuestaria'],
                                            'remanente': it2['remanente'],
                                            'aprobado': it2['aprobado'],
                                            'reduccion': it2['reduccion'],
                                            'ampliacion': it2['ampliacion'],
                                            'modificado': it2['modificado'],
                                            'comprometido': it2['comprometido'],
                                            'devengado': it2['devengado'],
                                            'ejercido': it2['ejercido'],
                                            'pagado': it2['pagado']
                                            }
                                        saldos_partida_destino.append(movimientos_des)
                                importe_mov=float(detalle.importe)
                                if (saldos_partida_destino):
                                    if item.clase_documento.id==6:
                                        dis_cp=float(saldos_partida[0]['remanente'])+float(saldos_partida[0]['ampliacion'])+float(saldos_partida[0]['modificado'])-float(saldos_partida[0]['comprometido'])
                                        if float(round(importe_mov,2)) > float(round(dis_cp,2)):
                                            print ('pass')
                                            #raise ValidationError("El importe que intenta reducir es mayor al disponible (%s): original disponible (%s), se intenta comprometer (%s)" % (detalle.posicion_presupuestaria.partida_presupuestal,float(round(dis_cp,2)),float(round(importe_mov,2))))
                                    elif item.clase_documento.id == 7:
                                        dis_cp=float(saldos_partida[0]['comprometido'])-float(saldos_partida_destino[0]['devengado'])
                                        if float(round(importe_mov,2)) > float(round(dis_cp,2)):
                                            print ('pass')
                                            #raise ValidationError("El importe que intenta reducir es mayor al disponible (%s): devengado disponible (%s), se intenta devengar (%s)" % (detalle.posicion_presupuestaria.partida_presupuestal,float(round(dis_cp,2)),float(round(importe_mov,2))))
                                    elif item.clase_documento.id ==9:
                                        dis_cp=float(saldos_partida[0]['devengado'])-float(saldos_partida_destino[0]['ejercido'])
                                        if float(round(importe_mov,2)) > float(round(dis_cp,2)):
                                            print('salida')
                                            #raise ValidationError("El importe que intenta reducir es mayor al disponible (%s): ejercido disponible (%s), se intenta ejercer (%s)" % (detalle.posicion_presupuestaria.partida_presupuestal,float(round(dis_cp,2)),float(round(importe_mov,2))))
                                    elif item.clase_documento.id  == 8:
                                        dis_cp=float(saldos_partida_alt[0]['ejercido'])-float(saldos_partida_destino[0]['pagado'])
                                        if float(round(importe_mov,2)) > float(round(dis_cp,2)):
                                            print('salida')
                                            #raise ValidationError("El importe que intenta reducir es mayor al disponible (%s): pagado disponible (%s), se intenta pagar (%s)" % (detalle.posicion_presupuestaria.partida_presupuestal,float(round(dis_cp,2)),float(round(importe_mov,2))))
                                else:
                                    raise ValidationError("No se encontro documento original para esta partida (%s) para el periodo (%s)" % (detalle.posicion_presupuestaria.partida_presupuestal,item.periodo))
        
                        elif item.clase_documento.tipo_documento != 'ORIGINAL':
                            raise ValidationError("Se encontró un posible problema \n Razones: \n 1. No se tiene cargado presupuesto para este periodo.\n 2. No existe una cuanta de orden relacionada a esta partida. \n 3. No se tiene registrada esta partida.")

                        co = self.env['presupuesto.cuenta_orden'].search([('posicion_presupuestaria', '=', detalle.posicion_presupuestaria.id)])
                        if not co:
                            raise ValidationError('No existe la cuenta de orden  relacionada a esta partida(s) ')
            else:
                print('draft')
    @api.model
    def create(self,values,tipo=None):
        #raise ValidationError(tipo)
        if(tipo=='nomina'):
            record = super(Documento, self).create(values)
            return record
        elif(tipo=='reclasificacion'):
            record = super(Documento, self).create(values)
            for idx, item in enumerate(record.detalle_documento_ids):
                item.posicion = idx + 1
            return record
        elif(tipo=='remanente'):
            control_presupuesto = self.env['presupuesto.control_presupuesto']
            account_move = self.env['account.move']
            record = super(Documento, self).create(values)
            line_ids = []
            code_journal_change = ""
            for idx, item in enumerate(record.detalle_documento_ids):
                item.posicion = idx + 1
                co = self.env['presupuesto.cuenta_orden'].search([('posicion_presupuestaria', '=', item.posicion_presupuestaria.id)])
                cp_destino = control_presupuesto.search([
                    ('ejercicio', '=', record.ejercicio),
                    ('periodo', '=', record.periodo),
                    ('version', '=', record.version.id),
                    ('fondo_economico', '=', item.fondo_economico.id),
                    ('posicion_presupuestaria', '=', item.posicion_presupuestaria.id),
                    ('centro_gestor', '=', item.centro_gestor.id),
                    ('area_funcional', '=', item.area_funcional.id)
                ])
                cp = control_presupuesto.search([
                    ('ejercicio', '=', record.ejercicio),
                    ('periodo', '=', record.periodo_origen),
                    ('version', '=', record.version.id),
                    ('fondo_economico', '=', item.fondo_economico.id),
                    ('posicion_presupuestaria', '=', item.posicion_presupuestaria.id),
                    ('centro_gestor', '=', item.centro_gestor.id),
                    ('area_funcional', '=', item.area_funcional.id)])
                #raise ValidationError("%s" % (cp_destino))
                co_egreso = [0,False,{
                        'analytic_account_id': False,
                        'currency_id': False,
                        'credit': 0,
                        'date_maturity': record.fecha_contabilizacion,
                        'debit': abs(item.importe),
                        'amount_currency': 0,
                        'partner_id': False,
                        'name': 'presupuesto'
                    }]
                co_ingreso = [0,False,{
                        'analytic_account_id': False,
                        'currency_id': False,
                        'credit': abs(item.importe),
                        'date_maturity': record.fecha_contabilizacion,
                        'debit': 0,
                        'amount_currency': 0,
                        'partner_id': False,
                        'name': 'presupuesto'
                    }]
                if (record.clase_documento.tipo_documento == 'REMANENTE'):
                    co_egreso[2]['account_id'] = co.cta_orden_devengado_egreso.id
                    co_ingreso[2]['account_id'] = co.cta_orden_devengado_ingreso.id
                    jurnal_select="REMAN"

                line_ids.append(co_egreso)
                line_ids.append(co_ingreso)
                record.detalle_documento_ids[idx]['control_presupuesto_id'] = cp_destino.id
                code_journal_change=jurnal_select
            journal = self.env['account.journal'].search([('code', '=', code_journal_change)], limit=1)
            #raise ValidationError('debug: %s' % (journal))
            if journal:
                if(record.concepto):
                    ref=str(record.concepto.encode('utf-8'))
                else:
                    ref=str(record.concepto)
                poliza = account_move.create({
                    'journal_id': journal.id,
                    'date': record.fecha_contabilizacion,
                    'ref': ref,
                    'documento_id':record.id,
                    'narration':False,
                    'state':'draft',
                    'line_ids':line_ids,
                    'compra_id':record.compra_id.id
                })
            else:
                raise ValidationError('No existe el Diario de cuentas de orden presupuestales')
            return record
        elif(tipo=='cancel'):
            control_presupuesto = self.env['presupuesto.control_presupuesto']
            account_move = self.env['account.move']
            record = super(Documento, self).create(values)
            line_ids = []
            code_journal_change = ""
            for idx, item in enumerate(record.detalle_documento_ids):
                item.posicion = idx + 1
                co = self.env['presupuesto.cuenta_orden'].search([('posicion_presupuestaria', '=', item.posicion_presupuestaria.id)])
                cp_destino = control_presupuesto.search([
                    ('ejercicio', '=', record.ejercicio),
                    ('periodo', '=', record.periodo),
                    ('version', '=', record.version.id),
                    ('fondo_economico', '=', item.fondo_economico.id),
                    ('posicion_presupuestaria', '=', item.posicion_presupuestaria.id),
                    ('centro_gestor', '=', item.centro_gestor.id),
                    ('area_funcional', '=', item.area_funcional.id)
                ])
                cp = control_presupuesto.search([
                    ('ejercicio', '=', record.ejercicio),
                    ('periodo', '=', record.periodo_origen),
                    ('version', '=', record.version.id),
                    ('fondo_economico', '=', item.fondo_economico.id),
                    ('posicion_presupuestaria', '=', item.posicion_presupuestaria.id),
                    ('centro_gestor', '=', item.centro_gestor.id),
                    ('area_funcional', '=', item.area_funcional.id)])
                #raise ValidationError("%s" % (cp_destino))
                co_egreso = [0,False,{
                        'analytic_account_id': False,
                        'currency_id': False,
                        'credit': 0,
                        'date_maturity': record.fecha_contabilizacion,
                        'debit': abs(item.importe),
                        'amount_currency': 0,
                        'partner_id': False,
                        'name': 'presupuesto'
                    }]
                co_ingreso = [0,False,{
                        'analytic_account_id': False,
                        'currency_id': False,
                        'credit': abs(item.importe),
                        'date_maturity': record.fecha_contabilizacion,
                        'debit': 0,
                        'amount_currency': 0,
                        'partner_id': False,
                        'name': 'presupuesto'
                    }]
                if (record.clase_documento_ajuste.tipo_documento == 'CANCELACION' and record.tipo == 'COMPROMETIDO'):
                    importe_can=cp.egreso_comprometido - abs(item.importe)
                    cp.write({ 'egreso_comprometido': importe_can })
                    co_egreso[2]['account_id'] = co.cta_orden_comprometido_egreso.id
                    co_ingreso[2]['account_id'] = co.cta_orden_original_egreso.id
                    jurnal_select="COPCA"
                elif (record.clase_documento_ajuste.tipo_documento == 'CANCELACION' and record.tipo == 'DEVENGADO'):
                    cp.write({ 'egreso_devengado': cp.egreso_devengado - abs(item.importe) })
                    co_egreso[2]['account_id'] = co.cta_orden_devengado_egreso.id
                    co_ingreso[2]['account_id'] = co.cta_orden_comprometido_egreso.id
                    jurnal_select="COPCA"
                elif (record.clase_documento_ajuste.tipo_documento == 'CANCELACION' and record.tipo == 'EJERCIDO'):
                    cp.write({ 'egreso_ejercido': cp.egreso_ejercido - abs(item.importe) })
                    co_egreso[2]['account_id'] = co.cta_orden_ejercido_egreso.id
                    co_ingreso[2]['account_id'] = co.cta_orden_devengado_egreso.id
                    jurnal_select="COPCA"
                elif (record.clase_documento_ajuste.tipo_documento == 'CANCELACION' and record.tipo == 'PAGADO'):
                    cp.write({ 'egreso_devengado': cp.egreso_devengado - abs(item.importe) })
                    co_egreso[2]['account_id'] = co.cta_orden_pagado_egreso.id
                    co_ingreso[2]['account_id'] = co.cta_orden_ejercido_egreso.id
                    jurnal_select="COPCA"
                    
                line_ids.append(co_egreso)
                line_ids.append(co_ingreso)
                record.detalle_documento_ids[idx]['control_presupuesto_id'] = cp_destino.id
                code_journal_change=jurnal_select

            journal = self.env['account.journal'].search([('code', '=', code_journal_change)], limit=1)
            if journal:
                if(record.concepto):
                    ref=str(record.concepto.encode('utf-8'))
                else:
                    ref=str(record.concepto)
                poliza = account_move.create({
                    'journal_id': journal.id,
                    'date': record.fecha_contabilizacion,
                    'ref': ref,
                    'documento_id':record.id,
                    'narration':False,
                    'line_ids':line_ids,
                    'compra_id':record.compra_id.id
                })
                poliza.post()
            else:
                raise ValidationError('No existe el Diario de cuentas de orden presupuestales')
            return record

            
        elif(tipo=='ajust'):
            control_presupuesto = self.env['presupuesto.control_presupuesto']
            account_move = self.env['account.move']
            record = super(Documento, self).create(values)
            line_ids = []
            code_journal_change = ""
            for idx, item in enumerate(record.detalle_documento_ids):
                item.posicion = idx + 1
                co = self.env['presupuesto.cuenta_orden'].search([('posicion_presupuestaria', '=', item.posicion_presupuestaria.id)])
                cp_destino = control_presupuesto.search([
                    ('ejercicio', '=', record.ejercicio),
                    ('periodo', '=', record.periodo),
                    ('version', '=', record.version.id),
                    ('fondo_economico', '=', item.fondo_economico.id),
                    ('posicion_presupuestaria', '=', item.posicion_presupuestaria.id),
                    ('centro_gestor', '=', item.centro_gestor.id),
                    ('area_funcional', '=', item.area_funcional.id)
                ])
                cp = control_presupuesto.search([
                    ('ejercicio', '=', record.ejercicio),
                    ('periodo', '=', record.periodo_origen),
                    ('version', '=', record.version.id),
                    ('fondo_economico', '=', item.fondo_economico.id),
                    ('posicion_presupuestaria', '=', item.posicion_presupuestaria.id),
                    ('centro_gestor', '=', item.centro_gestor.id),
                    ('area_funcional', '=', item.area_funcional.id)])
                co_egreso = [0,False,{
                        'analytic_account_id': False,
                        'currency_id': False,
                        'credit': 0,
                        'date_maturity': record.fecha_contabilizacion,
                        'debit': abs(item.importe),
                        'amount_currency': 0,
                        'partner_id': False,
                        'name': 'presupuesto'
                    }]
                co_ingreso = [0,False,{
                        'analytic_account_id': False,
                        'currency_id': False,
                        'credit': abs(item.importe),
                        'date_maturity': record.fecha_contabilizacion,
                        'debit': 0,
                        'amount_currency': 0,
                        'partner_id': False,
                        'name': 'presupuesto'
                    }]
                if (record.clase_documento_ajuste.tipo_documento == 'AJUSTE' and record.tipo == 'COMPROMETIDO'):
                    if (float(item.importe_val) > 0.0):
                        if (cp.egreso_disponible >= item.importe):
                            cp.write({ 'egreso_comprometido': cp.egreso_comprometido + item.importe })
                            co_egreso[2]['account_id'] = co.cta_orden_comprometido_egreso.id
                            co_ingreso[2]['account_id'] = co.cta_orden_comprometido_ingreso.id
                        else:
                            co_egreso[2]['account_id'] = co.cta_orden_comprometido_egreso.id
                            co_ingreso[2]['account_id'] = co.cta_orden_comprometido_ingreso.id
                            print ('pass')
                            #raise ValidationError("No se cuenta con saldo disponible para realizar esta operacion - Tu saldo disponible: %s" % (cp.egreso_disponible))
                        jurnal_select="COPAJ"
                    else:
                         raise ValidationError("No puede mandar datos en negativos.")
                elif (record.clase_documento_ajuste.tipo_documento == 'AJUSTE' and record.tipo == 'DEVENGADO'):
                    if (float(item.importe_val) > 0.0):
                        if (cp.egreso_disponible >= item.importe):
                            cp.write({ 'egreso_devengado': cp.egreso_devengado + item.importe })
                            co_egreso[2]['account_id'] = co.cta_orden_devengado_egreso.id
                            co_ingreso[2]['account_id'] = co.cta_orden_devengado_ingreso.id
                        else:
                            print ('pass')
                            co_egreso[2]['account_id'] = co.cta_orden_devengado_egreso.id
                            co_ingreso[2]['account_id'] = co.cta_orden_devengado_ingreso.id
                            #raise ValidationError("No se cuenta con saldo disponible para realizar esta operacion - Tu saldo disponible: %s" % (cp.egreso_disponible))
                        jurnal_select="COPAJ"
                    else:
                         raise ValidationError("No puede mandar datos en negativos.")
                elif (record.clase_documento_ajuste.tipo_documento == 'AJUSTE' and record.tipo == 'EJERCIDO'):
                    if (float(item.importe_val) > 0.0):
                        if (cp.egreso_disponible >= item.importe):
                            cp.write({ 'egreso_ejercido': cp.egreso_ejercido + item.importe })
                            co_egreso[2]['account_id'] = co.cta_orden_ejercido_egreso.id
                            co_ingreso[2]['account_id'] = co.cta_orden_ejercido_ingreso.id
                        else:
                            raise ValidationError("No se cuenta con saldo disponible para realizar esta operacion - Tu saldo disponible: %s" % (cp.egreso_disponible))
                        jurnal_select="COPAJ"
                    else:
                         raise ValidationError("No puede mandar datos en negativos.")
                elif (record.clase_documento_ajuste.tipo_documento == 'AJUSTE' and record.tipo == 'PAGADO'):
                    if (float(item.importe_val) > 0.0):
                        if (cp.egreso_disponible >= item.importe):
                            cp.write({ 'egreso_pagado': cp.egreso_pagado + item.importe })
                            co_egreso[2]['account_id'] = co.cta_orden_pagado_egreso.id
                            co_ingreso[2]['account_id'] = co.cta_orden_pagado_ingreso.id
                        else:
                            raise ValidationError("No se cuenta con saldo disponible para realizar esta operacion - Tu saldo disponible: %s" % (cp.egreso_disponible))
                        jurnal_select="COPAJ"
                    else:
                         raise ValidationError("No puede mandar datos en negativos.")
               

                line_ids.append(co_egreso)
                line_ids.append(co_ingreso)
                record.detalle_documento_ids[idx]['control_presupuesto_id'] = cp_destino.id
                code_journal_change=jurnal_select

            journal = self.env['account.journal'].search([('code', '=', code_journal_change)], limit=1)
            if journal:
                if(record.concepto):
                    ref=str(record.concepto.encode('utf-8'))
                else:
                    ref=str(record.concepto)
                poliza = account_move.create({
                    'journal_id': journal.id,
                    'date': record.fecha_contabilizacion,
                    'ref': ref,
                    'documento_id':record.id,
                    'narration':False,
                    'line_ids':line_ids,
                    'compra_id':record.compra_id.id
                })
                poliza.post()
            else:
                raise ValidationError('No existe el Diario de cuentas de orden presupuestales')
            return record
        elif(values.get('is_periodo_anterior')==4):
            control_presupuesto = self.env['presupuesto.control_presupuesto']
            account_move = self.env['account.move']
            record = super(Documento, self).create(values)
            line_ids = []
            code_journal_change = ""
            for idx, item in enumerate(record.detalle_documento_ids):
                cpa = control_presupuesto.search([
                    ('ejercicio', '=', record.ejercicio),
                    ('periodo', '=', record.periodo_origen),
                    ('version', '=', record.version.id),
                    ('fondo_economico', '=', item.fondo_economico.id),
                    ('posicion_presupuestaria', '=', item.posicion_presupuestaria.id),
                    ('centro_gestor', '=', item.centro_gestor.id),
                    ('area_funcional', '=', item.area_funcional.id)
                ])
                item.importe = item.importe * -1
                item.posicion = idx + 1
                record.detalle_documento_ids[idx]['control_presupuesto_id'] = cpa.id
                co = self.env['presupuesto.cuenta_orden'].search([('posicion_presupuestaria', '=', item.posicion_presupuestaria.id)])
                co_egreso = [0,False,{
                        'analytic_account_id': False,
                        'currency_id': False,
                        'credit': 0,
                        'date_maturity': record.fecha_contabilizacion,
                        'debit': abs(item.importe),
                        'amount_currency': 0,
                        'partner_id': False,
                        'name': 'presupuesto'
                    }]
                co_ingreso = [0,False,{
                        'analytic_account_id': False,
                        'currency_id': False,
                        'credit': abs(item.importe),
                        'date_maturity': record.fecha_contabilizacion,
                        'debit': 0,
                        'amount_currency': 0,
                        'partner_id': False,
                        'name': 'presupuesto'
                    }]
                if record.clase_documento.tipo_documento == 'COMPROMETIDO':
                    cpa.write({
                        'egreso_comprometido': cpa.egreso_comprometido + item.importe
                    })
                    #movimiento contable
                    co_egreso[2]['account_id'] = co.cta_orden_comprometido_egreso.id
                    co_ingreso[2]['account_id'] = co.cta_orden_comprometido_ingreso.id
                    jurnal_select="COPCA"

                elif record.clase_documento.tipo_documento == 'DEVENGADO':
                    cpa.write({
                        'egreso_devengado': cpa.egreso_devengado + item.importe
                    })
                    #movimiento contable
                    co_egreso[2]['account_id'] = co.cta_orden_devengado_egreso.id
                    co_ingreso[2]['account_id'] = co.cta_orden_devengado_ingreso.id
                    jurnal_select="COPCA"

                elif record.clase_documento.tipo_documento == 'EJERCIDO':
                    cpa.write({
                        'egreso_ejercido': cpa.egreso_ejercido + item.importe
                    })
                    co_egreso[2]['account_id'] = co.cta_orden_ejercido_egreso.id
                    co_ingreso[2]['account_id'] = co.cta_orden_ejercido_ingreso.id
                    jurnal_select="COPCA"
                elif record.clase_documento.tipo_documento == 'PAGADO':
                    cpa.write({
                        'egreso_pagado': cpa.egreso_pagado + item.importe,
                    })
                    co_egreso[2]['account_id'] = co.cta_orden_pagado_egreso.id
                    co_ingreso[2]['account_id'] = co.cta_orden_pagado_ingreso.id
                    jurnal_select="COPCA"
                line_ids.append(co_egreso)
                line_ids.append(co_ingreso)
                code_journal_change=jurnal_select
            importe = item.importe
            #raise ValidationError(importe)
            journal = self.env['account.journal'].search([('code', '=', code_journal_change)], limit=1)
            if journal:
                if(record.concepto):
                    ref=str(record.concepto.encode('utf-8'))
                else:
                    ref=str(record.concepto)
                poliza = account_move.create({
                    'journal_id': journal.id,
                    'date': record.fecha_contabilizacion,
                    'ref':ref,
                    'documento_id':record.id,
                    'narration':False,
                    'line_ids':line_ids,
                    'compra_id':record.compra_id.id,
                    'amount': importe
                })
                #raise ValidationError(poliza)
                poliza.amount = importe
                poliza.post()
            return record
        else:
            control_presupuesto = self.env['presupuesto.control_presupuesto']
            account_move = self.env['account.move']
            record = super(Documento, self).create(values)
            line_ids = []
            code_journal_change = ""
            for idx, item in enumerate(record.detalle_documento_ids):
                if(values.get('is_periodo_anterior')==2):
                    cpa = control_presupuesto.search([
                        ('ejercicio', '=', record.ejercicio),
                        ('periodo', '=', record.periodo_origen),
                        ('version', '=', record.version.id),
                        ('fondo_economico', '=', item.fondo_economico.id),
                        ('posicion_presupuestaria', '=', item.posicion_presupuestaria.id),
                        ('centro_gestor', '=', item.centro_gestor.id),
                        ('area_funcional', '=', item.area_funcional.id)
                    ])
                elif(values.get('is_periodo_anterior')==3):
                    cpa = control_presupuesto.search([
                        ('ejercicio', '=', record.ejercicio),
                        ('periodo', '=', record.periodo_origen),
                        ('version', '=', record.version.id),
                        ('fondo_economico', '=', item.fondo_economico.id),
                        ('posicion_presupuestaria', '=', item.posicion_presupuestaria.id),
                        ('centro_gestor', '=', item.centro_gestor.id),
                        ('area_funcional', '=', item.area_funcional.id)
                    ])
                item.posicion = idx + 1
                co = self.env['presupuesto.cuenta_orden'].search([('posicion_presupuestaria', '=', item.posicion_presupuestaria.id)])
                cp_destino = control_presupuesto.search([
                    ('ejercicio', '=', record.ejercicio),
                    ('periodo', '=', record.periodo),
                    ('version', '=', record.version.id),
                    ('fondo_economico', '=', item.fondo_economico.id),
                    ('posicion_presupuestaria', '=', item.posicion_presupuestaria.id),
                    ('centro_gestor', '=', item.centro_gestor.id),
                    ('area_funcional', '=', item.area_funcional.id)
                ])
                
                if(values.get('is_periodo_anterior')==1):
                    cp = control_presupuesto.search([
                        ('ejercicio', '=', record.ejercicio),
                        ('periodo', '=', record.periodo),
                        ('version', '=', record.version.id),
                        ('fondo_economico', '=', item.fondo_economico.id),
                        ('posicion_presupuestaria', '=', item.posicion_presupuestaria.id),
                        ('centro_gestor', '=', item.centro_gestor.id),
                        ('area_funcional', '=', item.area_funcional.id)
                    ])
                if record.clase_documento.tipo_documento == 'ORIGINAL':
                    pass
                else:
                    cp = control_presupuesto.search([
                        ('ejercicio', '=', record.ejercicio),
                        ('periodo', '=', record.periodo),
                        ('version', '=', record.version.id),
                        ('fondo_economico', '=', item.fondo_economico.id),
                        ('posicion_presupuestaria', '=', item.posicion_presupuestaria.id),
                        ('centro_gestor', '=', item.centro_gestor.id),
                        ('area_funcional', '=', item.area_funcional.id) ])

                co_egreso = [0,False,{
                        'analytic_account_id': False,
                        'currency_id': False,
                        'credit': 0,
                        'date_maturity': record.fecha_contabilizacion,
                        'debit': item.importe,
                        'amount_currency': 0,
                        'partner_id': False,
                        'name': 'presupuesto'
                    }]
                co_ingreso = [0,False,{
                        'analytic_account_id': False,
                        'currency_id': False,
                        'credit': item.importe,
                        'date_maturity': record.fecha_contabilizacion,
                        'debit': 0,
                        'amount_currency': 0,
                        'partner_id': False,
                        'name': 'presupuesto'
                    }]
                if record.clase_documento.tipo_documento == 'ORIGINAL':
                    cp = control_presupuesto.create({
                        'ejercicio': record.ejercicio,
                        'periodo': record.periodo,
                        'version': record.version.id,
                        'fondo_economico': item.fondo_economico.id,
                        'posicion_presupuestaria': item.posicion_presupuestaria.id,
                        'centro_gestor': item.centro_gestor.id,
                        'area_funcional': item.area_funcional.id,
                        'egreso_aprobado': item.importe
                    })
                    #movimiento contable
                    co_egreso[2]['account_id'] = co.cta_orden_original_egreso.id
                    co_ingreso[2]['account_id'] = co.cta_orden_original_ingreso.id
                    jurnal_select="COP"
                elif record.clase_documento.tipo_documento == 'AMPLIACION' or \
                    (record.clase_documento.tipo_documento == 'RECLASIFICACION' and \
                    record.clase_documento.signo == '+'):
                    cp.write({
                        'ampliacion': cp.ampliacion + item.importe
                    })
                    #movimiento contable
                    co_egreso[2]['account_id'] = co.cta_orden_modificado_egreso.id
                    co_ingreso[2]['account_id'] = co.cta_orden_modificado_ingreso.id
                    jurnal_select="COPA"
                elif record.clase_documento.tipo_documento == 'REDUCCION' or \
                    (record.clase_documento.tipo_documento == 'RECLASIFICACION' and \
                    record.clase_documento.signo == '-'):
                    cp.write({
                        'reduccion': cp.reduccion + item.importe
                    })
                    #movimiento contable
                    co_egreso[2]['account_id'] = co.cta_orden_modificado_ingreso.id
                    co_ingreso[2]['account_id'] = co.cta_orden_modificado_egreso.id
                    jurnal_select="COPR"
                elif record.clase_documento.tipo_documento == 'COMPROMETIDO':
                    cp.write({
                        'egreso_comprometido': cp.egreso_comprometido + item.importe
                    })
                    #movimiento contable
                    co_egreso[2]['account_id'] = co.cta_orden_comprometido_egreso.id
                    co_ingreso[2]['account_id'] = co.cta_orden_comprometido_ingreso.id
                    jurnal_select="COPC"
                elif record.clase_documento.tipo_documento == 'DEVENGADO':
                    cp.write({
                        'egreso_comprometido': cp.egreso_comprometido - item.importe,
                        'egreso_devengado': cp.egreso_devengado + item.importe
                    })
                    #movimiento contable
                    co_egreso[2]['account_id'] = co.cta_orden_devengado_egreso.id
                    co_ingreso[2]['account_id'] = co.cta_orden_devengado_ingreso.id
                    jurnal_select="COPD"
                elif record.clase_documento.tipo_documento == 'EJERCIDO':
                    if(values.get('is_periodo_anterior')==2):
                        cpa.write({
                            'egreso_devengado': cpa.egreso_devengado - item.importe,
                            'egreso_ejercido': cpa.egreso_ejercido + item.importe
                        })
                        cp_destino.write({
                            'egreso_ejercido': cp_destino.egreso_ejercido + item.importe
                        })
                    elif(values.get('is_periodo_anterior')==3):
                        cpa.write({
                            'egreso_devengado': cpa.egreso_devengado - cpa.egreso_devengado
                        })
                        cp_destino.write({
                            'egreso_ejercido': cp_destino.egreso_ejercido + item.importe
                        })
                    else:
                        cp.write({
                            'egreso_devengado': cp.egreso_devengado - item.importe,
                            'egreso_ejercido': cp.egreso_ejercido + item.importe
                        })
                    co_egreso[2]['account_id'] = co.cta_orden_ejercido_egreso.id
                    co_ingreso[2]['account_id'] = co.cta_orden_ejercido_ingreso.id
                    jurnal_select="COPE"
                elif record.clase_documento.tipo_documento == 'PAGADO':
                    if(values.get('is_periodo_anterior')==2):
                        cpa.write({
                            'egreso_ejercido': cpa.egreso_ejercido - item.importe
                        })
                        cp_destino.write({
                            'egreso_pagado': cp_destino.egreso_pagado + item.importe
                        })
                    elif(values.get('is_periodo_anterior')==3):
                        cpa.write({
                            'egreso_ejercido': cpa.egreso_ejercido - cpa.egreso_ejercido
                        })
                        cp_destino.write({
                            'egreso_pagado': cp_destino.egreso_pagado + item.importe
                        })
                    else:
                        cp.write({
                            'egreso_ejercido': cp.egreso_ejercido - item.importe,
                            'egreso_pagado': cp.egreso_pagado + item.importe
                        })
                    co_egreso[2]['account_id'] = co.cta_orden_pagado_egreso.id
                    co_ingreso[2]['account_id'] = co.cta_orden_pagado_ingreso.id
                    jurnal_select="COPP"


                line_ids.append(co_egreso)
                line_ids.append(co_ingreso)
                if(values.get('is_periodo_anterior')==1):
                    record.detalle_documento_ids[idx]['control_presupuesto_id'] = cp.id
                elif record.clase_documento.tipo_documento == 'ORIGINAL':
                    record.detalle_documento_ids[idx]['control_presupuesto_id'] = cp.id
                else:
                    record.detalle_documento_ids[idx]['control_presupuesto_id'] = cp_destino.id
                code_journal_change=jurnal_select
            
            journal = self.env['account.journal'].search([('code', '=', code_journal_change)], limit=1)
            if journal:
                if(record.concepto):
                    ref=str(record.concepto.encode('utf-8'))
                else:
                    ref=str(record.concepto)
                poliza = account_move.create({
                    'journal_id': journal.id,
                    'date': record.fecha_contabilizacion,
                    'ref': ref,
                    'documento_id':record.id,
                    'narration':False,
                    'line_ids':line_ids,
                    'compra_id':record.compra_id.id
                })
                poliza.post()
            else:
                raise ValidationError('No existe el Diario de cuentas de orden presupuestales')
            return record


    
    def unlink(self):
        ctrl_periodo = self.env['control.periodos.wizard']
        if(ctrl_periodo.get_is_cerrado(self.fecha_documento)):
            raise ValidationError('No se permite eliminar documentos de un periodo presupuestalmente cerrado')
        else:
            obj_am = self.env['account.move']
            am = obj_am.search([('documento_id', '=', self.id),('state', '=', 'posted')], limit=1)
            if(am and self.status=='open'):
                raise ValidationError('No se permite eliminar documentos validados')
            else:
                am_unlink = obj_am.search([('documento_id', '=', self.id),('state', '=', 'draft')])
                am_unlink.unlink()
                return models.Model.unlink(self)

class DetalleDocumento(models.Model):
    _name = 'presupuesto.detalle_documento'
    _order = 'posicion'
    _description = "Detalle Documento"

    @api.model
    def get_fondo_economico(self):
        return self.env['presupuesto.fondo_economico'].search([('fuente_financiamiento','=','11')])

    @api.model
    def get_centro_gestor(self):
        return self.env['presupuesto.centro_gestor'].search([('clave','=','21A000')])

    @api.onchange('posicion_presupuestaria')
    def _get_de_area_funcional_by_partida(self):
        for rr in self:
            if rr.posicion_presupuestaria.capitulo == 1 or rr.posicion_presupuestaria.partida_presupuestal == '398100' or rr.posicion_presupuestaria.partida_presupuestal == '398200':
                self.area_funcional = self.env['presupuesto.area_funcional'].search([('area_funcional','=','020401')])
            elif rr.posicion_presupuestaria.capitulo == 2 or rr.posicion_presupuestaria.capitulo == 3 or rr.posicion_presupuestaria.capitulo == 5:
                self.area_funcional = self.env['presupuesto.area_funcional'].search([('area_funcional','=','020400')])

    posicion = fields.Integer(string='Posición', required=False, readonly=True)
    #Campo para relacionar llave con presupuesto
    documento_id = fields.Many2one('presupuesto.documento', string="Documento", required=True, ondelete='cascade')
    fondo_economico = fields.Many2one('presupuesto.fondo_economico', string='Fondo', required=True, readonly=1,  default=get_fondo_economico)
    posicion_presupuestaria = fields.Many2one('presupuesto.partida_presupuestal', string='Posición presupuestaria', required=True, domain="[('capitulo', '>=', 1), ('capitulo', '<=', 5), ('concepto', '>', 0)]")
    centro_gestor = fields.Many2one('presupuesto.centro_gestor', string='Centro gestor', required=True, readonly=1,  default=get_centro_gestor)
    area_funcional = fields.Many2one('presupuesto.area_funcional', string='Área funcional', required=True)
    importe = fields.Float(string='Importe', digits=(15, 2), required=True, default=0)
    control_presupuesto_id = fields.Many2one('presupuesto.control_presupuesto',string='Control presupuesto')
    momento_contable = fields.Char(string='Momento contable')
    importe_val=fields.Float(string='Importe val',digits=(15, 2), default=0)
    
    id_reference_ecercido=fields.Integer(string='referencia ejercido')
    control_presupuesto_nomina_id = fields.Many2one('nomina.nomina.control', string='Control presupuesto nomina')
    clave_partida = fields.Integer(string='Clave partida')
    check_line= fields.Boolean(string='Estado',default=True)
    pagar_saldo= fields.Boolean(string='pagar saldo')
    state_payment= fields.Selection([('ejercido','Ejercido'),('pagado','Pagado'),('ejercido_saldo','Ejercido con saldo')],string='Estado')
    state_pay=fields.Selection([('original','Original'),('ejercido_saldo','Ejercido con saldo'),('pagado','Pagado')],string='Estado',default='original')
    saldo_doc=fields.Float(compute='calcula_saldo',string='Saldo', digits=(15, 2), required=True, default=0)
    import_pay=fields.Float(string='Importe', digits=(15, 2), required=True, default=0)
    concepto=fields.Char(string='Concepto')

    
    def calcula_saldo(self):
        busca_doc_line = self.env['presupuesto.detalle_documento'].search([
            ('control_presupuesto_nomina_id','=',self.control_presupuesto_nomina_id.id),
            ('clave_partida','=',self.clave_partida),
            ('posicion_presupuestaria','=',self.posicion_presupuestaria.id),
            ('id_reference_ecercido','=',self.documento_id.id)])
        suma_importes=0
        for i in busca_doc_line:
            suma_importes=suma_importes+i.importe
        saldo=self.importe-suma_importes
        self.saldo_doc=saldo

    
    def name_get(self):
        result = []
        for doc in self:
            name = 'Documento No. %s - %s $%s' % (doc.documento_id.id,doc.posicion_presupuestaria.partida_presupuestal,doc.importe)
            result.append((doc.id, name))
        return result

class ControlPresupuesto(models.Model):
    _name = 'presupuesto.control_presupuesto'
    _description = "Control Presupuesto"

    ejercicio = fields.Selection(catalogos.EJERCICIO_SELECT, required=True)
    periodo = fields.Selection(catalogos.PERIODO_SELECT, required=True)
    version = fields.Many2one('presupuesto.version', string='Version', required=True)
    fondo_economico = fields.Many2one('presupuesto.fondo_economico', string='Fondo')
    posicion_presupuestaria = fields.Many2one('presupuesto.partida_presupuestal', string='Posición presupuestaria')
    centro_gestor = fields.Many2one('presupuesto.centro_gestor', string='Centro gestor')
    area_funcional = fields.Many2one('presupuesto.area_funcional', string='Área funcional')
    status = fields.Char(string='status', default='open')
    status_ES = fields.Char(string='Estado', compute='_compute_status')

    egreso_aprobado = fields.Float(
        string="Egreso Aprobado",
        digits=(15, 2), default=0)
    ampliacion = fields.Float(
        string='Ampliaciones',
        digits=(15, 2), default=0)
    reduccion = fields.Float(
        string='Reducciones',
        digits=(15, 2), default=0)
    egreso_modificado_remanente = fields.Float(
        string="Egreso Remanente",
        digits=(15,2),default=0)
    egreso_modificado = fields.Float(
        string="Egreso Modificado",
        digits=(15,2), compute='_egreso_modificado_calc')
    egreso_comprometido = fields.Float(
        string='Egreso Comprometido',
        digits=(15,2), default=0
    )
    egreso_devengado = fields.Float(
        string='Egreso Devengado',
        digits=(15,2), default=0
    )
    egreso_ejercido = fields.Float(
        string='Egreso Ejercido',
        digits=(15,2), default=0
    )
    egreso_pagado = fields.Float(
        string='Egreso Pagado',
        digits=(15,2), default=0
    )
    subejercicio = fields.Float(
        string='Subejercicio',
        digits=(15,2), default=0
    )
    egreso_disponible = fields.Float(
        string='Egreso Disponible',
        compute='_egreso_disponible'
    )
    detalle_documento_original_ids = fields.One2many(
        'presupuesto.detalle_documento',
        'control_presupuesto_id',
        domain=[('documento_id.clase_documento.tipo_documento','=','ORIGINAL')],
        string='Documento',
    )
    detalle_documento_remanente_ids = fields.One2many(
        'presupuesto.detalle_documento',
        'control_presupuesto_id',
        domain=[('documento_id.clase_documento.tipo_documento','=','REMANENTE'),
                ('documento_id.status', '!=', 'close')],
        string='Documento',
    )
    detalle_documento_ampliacion_ids = fields.One2many(
        'presupuesto.detalle_documento',
        'control_presupuesto_id',
        domain=['|',('documento_id.clase_documento.tipo_documento','=','AMPLIACION'),
                ('documento_id.clase_documento.tipo_documento', '=', 'RECLASIFICACION'),
                ('documento_id.clase_documento.signo', '=', '+'),
                ('documento_id.status', '!=', 'close')],
        string='Documento',
    )
    detalle_documento_reduccion_ids = fields.One2many(
        'presupuesto.detalle_documento',
        'control_presupuesto_id',
        domain=['|',('documento_id.clase_documento.tipo_documento','=','REDUCCION'),
                ('documento_id.clase_documento.tipo_documento', '=', 'RECLASIFICACION'),
                ('documento_id.clase_documento.signo', '=', '-'),
                ('documento_id.status', '!=', 'close')],
        string='Documento',
    )
    detalle_documento_comprometido_ids = fields.One2many(
        'presupuesto.detalle_documento',
        'control_presupuesto_id',
        domain=[('documento_id.clase_documento.tipo_documento','=','COMPROMETIDO'),
                ('documento_id.status', '!=', 'close')],
        string='Documento',
    )
    detalle_documento_devengado_ids = fields.One2many(
        'presupuesto.detalle_documento',
        'control_presupuesto_id',
        domain=[('documento_id.clase_documento.tipo_documento','=','DEVENGADO'),
                ('documento_id.status', '!=', 'close')],
        string='Documento',
    )
    detalle_documento_ejercido_ids = fields.One2many(
        'presupuesto.detalle_documento',
        'control_presupuesto_id',
        domain=[('documento_id.clase_documento.tipo_documento', '=', 'EJERCIDO'),
                ('documento_id.status', '!=', 'close')],
        string='Documento'
    )
    detalle_documento_pagado_ids = fields.One2many(
        'presupuesto.detalle_documento',
        'control_presupuesto_id',
        domain=[('documento_id.clase_documento.tipo_documento','=','PAGADO'),
                ('documento_id.status', '!=', 'close')],
        string='Documento',
    )

    @api.depends('egreso_aprobado', 'ampliacion', 'reduccion')
    def _egreso_modificado_calc(self):
        for r in self:
            r.egreso_modificado = r.egreso_aprobado + r.ampliacion - r.reduccion

    
    def _compute_status(self):
        if self.status=='open':
            status='ABIERTO'
        else:
            status='CERRADO'
        self.status_ES=status

    
    @api.depends(
        'ejercicio',
        'periodo',
        'version',
        'fondo_economico',
        'posicion_presupuestaria',
        'centro_gestor',
        'area_funcional'
    )
    def name_get(self):
        result = []
        for part_pres in self:
            name = '%s/%s/%s/%s/%s/%s/%s' % (
                part_pres.ejercicio,
                part_pres.periodo,
                obtener_nombre(part_pres.version.name_get()),
                obtener_nombre(part_pres.fondo_economico.name_get()),
                obtener_nombre(part_pres.posicion_presupuestaria.name_get()),
                obtener_nombre(part_pres.centro_gestor.name_get()),
                obtener_nombre(part_pres.area_funcional.name_get())
            )
            result.append((part_pres.id, name))
        return result

    @api.depends(
        'egreso_aprobado',
        'ampliacion',
        'reduccion',
        'egreso_comprometido',
        'egreso_devengado',
        'egreso_pagado')
    def _egreso_disponible(self):
        for r in self:
            r.egreso_disponible =  r.egreso_aprobado + r.ampliacion - r.reduccion + r.egreso_modificado_remanente - r.egreso_comprometido - r.egreso_devengado - r.egreso_ejercido - r.egreso_pagado

    _sql_constraints = [
        ('control_presupuesto_uniq',
        'UNIQUE (ejercicio, periodo, version, fondo_economico, posicion_presupuestaria, centro_gestor, area_funcional)',
        'La llave presupuestaria debe ser unico!')]

class Transferencia(models.Model):
    _name = 'presupuesto.transferencia'
    _description = u'Reclasificación de presupuesto'
    _inherit = ['mail.thread'] 
    _order = 'fecha_documento ASC'

    fecha_documento = fields.Date(string='Fecha de documento', required=True, default=fields.Datetime.now)
    fecha_contabilizacion = fields.Date(string='Fecha de contabilización', required=True)
    concepto = fields.Text(string='Concepto de reclasificación', track_visibility='onchange')
    ejercicio = fields.Selection(catalogos.EJERCICIO_SELECT, required=True)
    periodo = fields.Selection(catalogos.PERIODO_SELECT, required=True)
    importe = fields.Float(string='Importe a reclasificar', digits=(15, 2), required=True, track_visibility='onchange')
    detalle_transferencia_ids = fields.One2many('presupuesto.detalle_transferencia', 'transferencia_id', string='Detalle de Transferencia')
    move_id = fields.One2many('account.move', 'reclasificacion_id', index=True, store=True, track_visibility='onchange')
    state = fields.Selection([('progress', 'En Proceso'),('post', 'Valida'),('cancel', 'Cancelada')],default='progress', track_visibility='onchange')

    @api.onchange('fecha_documento')
    def _set_dates_fields(self):
        fecha = datetime.strptime(str(self.fecha_documento), '%Y-%m-%d')
        
        self.update({'fecha_contabilizacion': fecha})
        self.update({'periodo': str(fecha.month)})
        self.update({'ejercicio': str(fecha.year)})

    @api.depends(
        'ejercicio',
        'periodo'
    )
    def name_get(self):
        result = []
        for doc in self:
            name = 'Reclasificación de Recursos %s/%s/%s' % (
                doc.ejercicio,
                doc.periodo,
                doc.id
            )
            result.append((doc.id, name))
        return result
        
    @api.constrains('detalle_transferencia_ids', 'importe', 'periodo', 'ejercicio')
    def _validate_importe_recla(self):
        obj_documento = self.env['presupuesto.documento']
        control_presupuesto = self.env['presupuesto.control_presupuesto']
        account_move = self.env['account.move']
        #raise ValidationError("El importe a reclasificar -reducción- debe ser mayor a 0")
        for item in self:
            importe_total_reduccion = 0
            importe_total_ampliacion = 0
            version = 1
            ejercicio = item.ejercicio
            periodo = item.periodo
            fecha_contabilizacion = item.fecha_contabilizacion
            fecha_documento = item.fecha_documento
            documentos_originales_reduccion = []
            documentos_originales_ampliacion = []
            cls_doc_r = self.env['presupuesto.clase_documento'].search([('tipo_documento','=','RECLASIFICACION'), ('signo','=','-')], limit=1)
            cls_doc_a = self.env['presupuesto.clase_documento'].search([('tipo_documento','=','RECLASIFICACION'), ('signo','=','+')], limit=1)
            #Variables asiento
            line_ids_re = []
            line_ids_am = []
            code_journal = "COPR"
            concepto_asiento = item.concepto.encode('utf-8')
            #
            if item.importe == 0:
                raise ValidationError("El importe a reclasificar debe ser mayor 0")
            for detalle in item.detalle_transferencia_ids:
                importe_total_reduccion = importe_total_reduccion + detalle.de_importe
                importe_total_ampliacion = importe_total_ampliacion + detalle.para_importe
                if detalle.tipo_reclasificacion == 'REDUCCION':
                    #Cuenta de orden por partida_tipo
                    co_r = self.env['presupuesto.cuenta_orden'].search([('posicion_presupuestaria', '=', detalle.de_posicion_presupuestaria.id)])
                    #
                    sql_md="""
                        SELECT ((SUM(CASE WHEN pd.clase_documento = 3 THEN importe ELSE 0 END) + SUM(CASE WHEN (pd.clase_documento = 1) OR (pd.clase_documento = 4) THEN importe ELSE 0 END) + SUM(CASE WHEN pd.clase_documento = 10 THEN importe ELSE 0 END) ) -  SUM(CASE WHEN (pd.clase_documento = 2) OR (pd.clase_documento = 5) THEN importe ELSE 0 END) ) - SUM(CASE WHEN pd.clase_documento = 7 THEN importe ELSE 0 END) disponible
                        FROM presupuesto_detalle_documento dd
                        INNER JOIN presupuesto_partida_presupuestal pp ON dd.posicion_presupuestaria = pp.id
                        INNER JOIN presupuesto_documento pd ON dd.documento_id = pd.id
                        WHERE posicion_presupuestaria=%s and periodo=%s and status='open'
                        GROUP BY dd.posicion_presupuestaria,pp.partida_presupuestal,pd.periodo
                        """
                    self.env.cr.execute(sql_md % (detalle.de_posicion_presupuestaria.id,item.periodo))
                    importe_disponible = self.env.cr.fetchone()
                    if importe_disponible is not None:
                        importe_validar = importe_disponible[0]
                    else:
                        importe_validar = 0
                    #raise ValidationError("debug: %s" % (importe))
                    if detalle.de_importe == 0:
                        raise ValidationError("El importe a reclasificar -reducción- debe ser mayor a 0")
                    elif importe_validar < detalle.de_importe:
                        raise ValidationError("El importe a reducir es mayor al monto disponible de la partida (%s)" % (detalle.de_posicion_presupuestaria.partida_presupuestal))
                    elif importe_validar == 0:
                        raise ValidationError("La partida no existen en el contro presupuestal (%s)" % (detalle.de_posicion_presupuestaria.partida_presupuestal))
                    
                    control_destino = self.env['presupuesto.control_presupuesto'].search([
                        ('version', '=', version),
                        ('ejercicio', '=', ejercicio),
                        ('periodo', '=', periodo),
                        ('posicion_presupuestaria', '=', detalle.de_posicion_presupuestaria.id)
                    ])
                    doc_origin = [0, False,{
                        'centro_gestor': 1,
                        'area_funcional': detalle.de_area_funcional.id,
                        'fondo_economico': 1,
                        'posicion_presupuestaria': detalle.de_posicion_presupuestaria.id,
                        'importe': detalle.de_importe,
                        'control_presupuesto_id': control_destino.id
                    }]
                    documentos_originales_reduccion.append(doc_origin)
                    #Consulta al cp
                    cp_r = control_presupuesto.search([
                        ('ejercicio', '=', ejercicio),
                        ('periodo', '=', periodo),
                        ('version', '=', version),
                        ('fondo_economico', '=', 1),
                        ('posicion_presupuestaria', '=', detalle.de_posicion_presupuestaria.id),
                        ('centro_gestor', '=', 1),
                        ('area_funcional', '=', detalle.de_area_funcional.id)
                    ])

                    cp_r.write({
                        'reduccion': cp_r.reduccion + detalle.de_importe
                    })

                    co_egreso_r = [0,False,{
                        # 'journal_id': 68,
                        'analytic_account_id': False,
                        'currency_id': False,
                        'credit': 0,
                        'date_maturity': fecha_documento,
                        'debit': detalle.de_importe,
                        'amount_currency': 0,
                        'partner_id': False,
                        'name': 'Reclasificación de Recursos'
                    }]
                    co_ingreso_r = [0,False,{
                        # 'journal_id': 73,
                        'analytic_account_id': False,
                        'currency_id': False,
                        'credit': detalle.de_importe,
                        'date_maturity': fecha_documento,
                        'debit': 0,
                        'amount_currency': 0,
                        'partner_id': False,
                        'name': 'Reclasificación de Recursos'
                    }]
                    co_egreso_r[2]['account_id'] = co_r.cta_orden_modificado_egreso.id
                    co_ingreso_r[2]['account_id'] = co_r.cta_orden_modificado_ingreso.id
                    line_ids_re.append(co_egreso_r)
                    line_ids_re.append(co_ingreso_r)
                    #

                if detalle.tipo_reclasificacion == 'AMPLIACION':
                    #Cuenta de orden por partida_tipo
                    co_a = self.env['presupuesto.cuenta_orden'].search([('posicion_presupuestaria', '=', detalle.para_posicion_presupuestaria.id)])
                    #
                    control_destino = self.env['presupuesto.control_presupuesto'].search([
                        ('version', '=', version),
                        ('ejercicio', '=', ejercicio),
                        ('periodo', '=', periodo),
                        ('posicion_presupuestaria', '=', detalle.para_posicion_presupuestaria.id)
                    ])
                    if control_destino.posicion_presupuestaria.id == False:
                        raise ValidationError("La partida no existen en el contro presupuestal (%s)" % (detalle.para_posicion_presupuestaria.partida_presupuestal))
                    elif detalle.para_importe == 0:
                        raise ValidationError("El importe a reclasificar -ampliación- debe ser mayor a 0")
                    doc_origin_a = [0, False,{
                        'centro_gestor': 1,
                        'area_funcional': detalle.para_area_funcional.id,
                        'fondo_economico': 1,
                        'posicion_presupuestaria': detalle.para_posicion_presupuestaria.id,
                        'importe': detalle.para_importe,
                        'control_presupuesto_id': control_destino.id
                    }]
                    documentos_originales_ampliacion.append(doc_origin_a)
                    #Consulta al cp
                    cp_a = control_presupuesto.search([
                        ('ejercicio', '=', ejercicio),
                        ('periodo', '=', periodo),
                        ('version', '=', version),
                        ('fondo_economico', '=', 1),
                        ('posicion_presupuestaria', '=', detalle.para_posicion_presupuestaria.id),
                        ('centro_gestor', '=', 1),
                        ('area_funcional', '=', detalle.para_area_funcional.id)
                    ])

                    cp_a.write({
                        'ampliacion': cp_a.ampliacion + detalle.para_importe
                    })

                    co_egreso_a = [0,False,{
                        'analytic_account_id': False,
                        'currency_id': False,
                        'credit': detalle.para_importe,
                        'date_maturity': fecha_documento,
                        'debit': 0,
                        'amount_currency': 0,
                        'partner_id': False,
                        'name': 'Reclasificación de Recursos'
                    }]
                    co_ingreso_a = [0,False,{
                        'analytic_account_id': False,
                        'currency_id': False,
                        'credit': 0,
                        'date_maturity': fecha_documento,
                        'debit': detalle.para_importe,
                        'amount_currency': 0,
                        'partner_id': False,
                        'name': 'Reclasificación de Recursos'
                    }]
                    co_egreso_a[2]['account_id'] = co_a.cta_orden_modificado_ingreso.id
                    co_ingreso_a[2]['account_id'] = co_a.cta_orden_modificado_egreso.id
                    line_ids_am.append(co_ingreso_a)
                    line_ids_am.append(co_egreso_a)
                    #

            documento_r = obj_documento.create({
                'clase_documento': cls_doc_r.id,
                'version': version,
                'ejercicio': ejercicio,
                'periodo': periodo,
                'periodo_origen': periodo,
                'is_periodo_anterior': 1,
                'fecha_contabilizacion': fecha_contabilizacion,
                'fecha_documento': fecha_contabilizacion,
                'detalle_documento_ids': documentos_originales_reduccion
            },tipo='reclasificacion')
            documento_a = obj_documento.create({
                'clase_documento': cls_doc_a.id,
                'version': version,
                'ejercicio': ejercicio,
                'periodo': periodo,
                'periodo_origen': periodo,
                'is_periodo_anterior': 1,
                'fecha_contabilizacion': fecha_contabilizacion,
                'fecha_documento': fecha_contabilizacion,
                'detalle_documento_ids': documentos_originales_ampliacion
            },tipo='reclasificacion')
            
            ref_documento_a_id = documento_a.id
            ref_documento_r_id = documento_r.id
            for detalle in item.detalle_transferencia_ids:
                if detalle.tipo_reclasificacion == 'REDUCCION':
                    detalle.doc_reduccion = ref_documento_r_id
                elif detalle.tipo_reclasificacion == 'AMPLIACION':
                    detalle.doc_ampliacion = ref_documento_a_id
                
            #Asiento
            journal_re = self.env['account.journal'].search([('code', '=', 'COPR')], limit=1)
            journal_am = self.env['account.journal'].search([('code', '=', 'COPA')], limit=1)
            if journal_re:
                poliza = account_move.create({
                    'documento_id': documento_r.id,
                    'journal_id': journal_re.id,
                    'date': fecha_contabilizacion,
                    'concepto': concepto_asiento,
                    'narration':False,
                    'ref':item.id,
                    'reclasificacion_id':item.id,
                    'line_ids':line_ids_re,
                    'autorizo': 'ACRG',
                    'vobo': 'JSV',
                    'elaboro': 'SJGH',
                    'reviso': 'MPYM'
                })
                poliza.post()
            
            if journal_am:
                poliza = account_move.create({
                    'documento_id': documento_a.id,
                    'journal_id': journal_am.id,
                    'date': fecha_contabilizacion,
                    'concepto': concepto_asiento,
                    'narration':False,
                    'ref':item.id,
                    'reclasificacion_id':item.id,
                    'line_ids':line_ids_am,
                    'autorizo': 'ACRG',
                    'vobo': 'JSV',
                    'elaboro': 'SJGH',
                    'reviso': 'MPYM'
                })
                poliza.post()

            item.state = 'post'

        if importe_total_reduccion == 0:
            raise ValidationError("El importe a reducir debe ser mayor 0")
        elif float(round(item.importe,2)) < float(round(importe_total_reduccion,2)):
            raise ValidationError("El importe a reducir es mayor al importe a reclasificar")
        elif float(round(item.importe,2)) >  float(round(importe_total_reduccion,2)):
            raise ValidationError("El importe a reducir es menor al importe a reclasificar")
        elif float(round(item.importe,2)) <  float(round(importe_total_ampliacion,2)) :
            raise ValidationError("El importe a ampliar es mayor al importe a reclasificar")
        elif float(round(item.importe,2)) > float(round(importe_total_ampliacion,2)):
            raise ValidationError("El importe a ampliar es menor al importe a reclasificar")
        elif float(round(importe_total_ampliacion,2)) == 0:
            raise ValidationError("El importe a ampliar debe ser mayor a 0")
        elif  float(round(importe_total_reduccion,2)) > float(round(importe_total_ampliacion,2)):
            raise ValidationError("Importe a reducir es mayor a la ampliacion")
        elif float(round(importe_total_ampliacion,2)) >  float(round(importe_total_reduccion,2)):
            raise ValidationError("Importe a ampliar es mayor a la reducción")

    
    def print_reclasificacion(self):
        sql_lineas = """(select
                        0 id,
                        concat(SUBSTRING(code, 1, 3 ), '.0.0000.00') code,
                        "substring"(aa.code::text, 1, 3) cuenta,
                        "substring"(aa.code::text, 5, 1) sub_cta,
                        0 partida_id,0 clase_documento,
                        '' "ref",
                        sum(case when aml.journal_id in (95,103,102,73) then aml.credit*-1 else aml.credit end) credit,
                        sum(case when aml.journal_id in (95,103,102,73) then aml.debit*-1 else aml.debit end) debit
                    from
                        presupuesto_transferencia pt
                    join account_move am on am.reclasificacion_id=pt.id
                    join account_move_line aml on aml.move_id =am.id
                    join account_account aa on aa.id = aml.account_id
                    where
                        pt.id=%s 
                        group by 1,2,3,4)
                    union all
                    (select
                        distinct(aml.id),
                        aa.code,
                        "substring"(aa.code::text, 1, 3) cuenta,
                        "substring"(aa.code::text, 5, 1) sub_cta,
                        0 partida_id,0 clase_documento,
                        '' "ref",
                        case when aml.journal_id in (95,103,102,73) then aml.credit*-1 else aml.credit end,
                        case when aml.journal_id in (95,103,102,73) then aml.debit*-1 else aml.debit end
                    from
                        presupuesto_transferencia pt
                    join account_move am on am.reclasificacion_id=pt.id
                    join account_move_line aml on aml.move_id =am.id
                    join account_account aa on aa.id = aml.account_id
                    where
                        pt.id=%s 
                        ) order by code asc;""" %(self.id,self.id)

        self.env.cr.execute(sql_lineas)
        results = self.env.cr.dictfetchall()
        datas = {}
        suma_cargo = 0
        suma_abono = 0
        lineas = []
        count = 0

        df=pd.DataFrame.from_dict(results)
        cts_padre=df[df.code.str.contains('.0.0000.00')].filter(items=['code','ref','cuenta','sub_cta','credit','debit']).to_json(orient="records")
        
        cts_padre_parsed = json.loads(cts_padre)
        for item in cts_padre_parsed:
            filt=item['code'].split('.')
            ct_hijo=df[df.cuenta.str.contains(filt[0])].filter(items=['code','ref','cuenta','sub_cta','credit','debit']).to_json(orient="records")
            # raise ValidationError('%s'% (ct_hijo))
            cuenta_nombre = self.env['account.account'].search([('code', '=', str(item['code']))])[0].name
            insert_padre = {
                            'nombre': cuenta_nombre,
                            'cuenta': filt[0],
                            'subcuenta': '',
                            'subsubcuenta': '',
                            'subsubsubcuenta': '',
                            'parcial': '',
                            'cargo': '{0:,.2f}'.format(float(item['debit'])),
                            'abono': '{0:,.2f}'.format(float(item['credit'])),
                            }
            suma_cargo+=item['debit']
            suma_abono+=item['credit']
            lineas.append(insert_padre)
            capitulos = []
            cts_sub_cta_parsed = json.loads(ct_hijo)
            for subc in cts_sub_cta_parsed:
                capitulos.append(subc['sub_cta'])
            for sub_cta in list(set(capitulos)):
                tot_sub_cta=0
                sub_cta_filter=filt[0]+'.'+str(sub_cta)
                sub_cta_nombre = self.env['account.account'].search([('code', '=', str(sub_cta_filter+'.0000.00'))])[0].name
                cts_sub_cta=df[df.code.str.contains(sub_cta_filter)].filter(items=['code','ref','cuenta','sub_cta','credit','debit']).to_json(orient="records")
                cts_sub_cta_parsed = json.loads(cts_sub_cta)
                for it in cts_sub_cta_parsed:
                    if(it['debit']==0):
                        parcial=it['credit']
                    else:
                        parcial=it['debit']
                    tot_sub_cta=tot_sub_cta+parcial
                insert_padre = {
                                'nombre': sub_cta_nombre,
                                'cuenta': '',
                                'subcuenta': sub_cta,
                                'subsubcuenta': '',
                                'subsubsubcuenta': '',
                                'parcial': '',
                                'cargo': '',
                                'abono': '',
                                }
                lineas.append(insert_padre)
                for it_part in cts_sub_cta_parsed:
                    subc = it_part['code'].split('.')
                    subsubcuenta_nombre = self.env['account.account'].search([('code', '=like', subc[0] + '.' + subc[1] + '.' + subc[2] + '%')])[0].name
                    subsubsubcuenta_nombre = self.env['account.account'].search([('code', '=', str(it_part['code']))])[0].name
                    if(it_part['debit']==0):
                        parcial=it_part['credit']
                    else:
                        parcial=it_part['debit']
                    for count in range(1,5):
                        if count == 1:
                            pass
                        if count == 2:
                            pass
                        if count == 3:
                            insert = {
                            'nombre':subsubcuenta_nombre,
                            'cuenta': '',
                            'subcuenta': '',
                            'subsubcuenta': subc[2],
                            'subsubsubcuenta': '',
                            'parcial': '',
                            'cargo': '',
                            'abono': '',
                            }
                            lineas.append(insert)
                        if count == 4:
                            insert = {
                            'nombre': subsubsubcuenta_nombre,
                            'cuenta': '',
                            'subcuenta': '',
                            'subsubcuenta': '',
                            'subsubsubcuenta': subc[3],
                            'parcial': '{0:,.2f}'.format(float(parcial)),
                            'cargo': '',
                            'abono': '',
                            }
                            lineas.append(insert)
                            count += 1

        datas['lineas_cuenta'] = lineas

        datas['suma_abono'] = suma_abono
        datas['suma_cargo'] = suma_cargo

        form={
            'date':'%s'%(self.fecha_documento),
            'name':'CP-'+str(self.id),
            'concepto':self.concepto,
            'elaboro':'SJGH',
            'reviso':'MPYM',
            'vobo':'JSV',
            'autorizo':'ACRG',
        }
        datas['form'] = form

        return self.env['report'].get_action([], 'reportes.poliza_presupuestal', data=datas)
        
        

    
    
    def cancel_reclasificacion(self):
        account_move = self.env['account.move']
        obj_documento = self.env['presupuesto.documento']
        obj_documento_detalle = self.env['presupuesto.detalle_documento']
        obj_cp = self.env['presupuesto.control_presupuesto']
        poliza_id = self.move_id
        doc_transferencia = []
        for item in self.detalle_transferencia_ids:
            if item.tipo_reclasificacion == 'REDUCCION':
                docreduccion = obj_documento.search([
                    ('id', '=', item.doc_reduccion.id)
                ], limit=1)
                for i in docreduccion:
                    if i.id not in doc_transferencia:
                        doc_transferencia.append(docreduccion.id)
            if item.tipo_reclasificacion == 'AMPLIACION':
                docampliacion = obj_documento.search([
                    ('id', '=', item.doc_ampliacion.id)
                ], limit=1)
                for i in docampliacion:
                    if i.id not in doc_transferencia:
                        doc_transferencia.append(docampliacion.id)
        for doc in doc_transferencia:
            doc_trans = obj_documento.search([
                    ('id', '=', doc)
            ])
            doc_trans.write({
                'status': 'close'
            })
        for doc in doc_transferencia:
            doc_trans = obj_documento.search([
                    ('id', '=', doc)
            ])
            #Ampliacion
            if doc_trans.clase_documento.id == 4:
                doc_r = obj_documento_detalle.search([
                    ('documento_id', '=', doc)
                ])
                for ii in doc_r:
                    cp_a = obj_cp.search([
                        ('id', '=', ii.control_presupuesto_id.id)
                    ])
                    importe_detalle_documentos = ii.importe
                    cp_a.write({
                        'ampliacion': cp_a.ampliacion - importe_detalle_documentos
                    })
            #Reduccion
            if doc_trans.clase_documento.id == 5:
                doc_r = obj_documento_detalle.search([
                    ('documento_id', '=', doc)
                ])
                for ii in doc_r:
                    cp_r = obj_cp.search([
                        ('id', '=', ii.control_presupuesto_id.id)
                    ])
                    importe_detalle_documentos = ii.importe
                    cp_r.write({
                        'reduccion': cp_r.reduccion - importe_detalle_documentos
                    })

        #Poliza a borrador
        for poliza in poliza_id:
            poliza.write({
                'state': 'draft'
            })
        self.state = 'cancel'

class DetalleTransferencia(models.Model):
    _name = 'presupuesto.detalle_transferencia'
    _description = u'Detalle de Reclasificación de prespuesto'

    @api.model
    def get_centro_gestor_transferencia(self):
        return self.env['presupuesto.centro_gestor'].search([('clave','=','21A000')])

    @api.onchange('de_posicion_presupuestaria')
    def _get_de_area_funcional_by_partida(self):
        for rr in self:
            if rr.de_posicion_presupuestaria.capitulo == 1 or rr.de_posicion_presupuestaria.partida_presupuestal == '398100' or rr.de_posicion_presupuestaria.partida_presupuestal == '398200':
                self.de_area_funcional = self.env['presupuesto.area_funcional'].search([('area_funcional','=','020401')])
            elif rr.de_posicion_presupuestaria.capitulo == 2 or rr.de_posicion_presupuestaria.capitulo == 3 or rr.de_posicion_presupuestaria.capitulo == 5:
                self.de_area_funcional = self.env['presupuesto.area_funcional'].search([('area_funcional','=','020400')])
    
    @api.onchange('para_posicion_presupuestaria')
    def _get_para_area_funcional_by_partida(self):
        for ra in self:
            if ra.para_posicion_presupuestaria.capitulo == 1 or ra.para_posicion_presupuestaria.partida_presupuestal == '398100' or ra.para_posicion_presupuestaria.partida_presupuestal == '398200':
                self.para_area_funcional = self.env['presupuesto.area_funcional'].search([('area_funcional','=','020401')])
            elif ra.para_posicion_presupuestaria.capitulo == 2 or ra.para_posicion_presupuestaria.capitulo == 3 or ra.para_posicion_presupuestaria.capitulo == 5:
                self.para_area_funcional = self.env['presupuesto.area_funcional'].search([('area_funcional','=','020400')])
    
    transferencia_id = fields.Many2one('presupuesto.transferencia', string='Transferencia')
    tipo_reclasificacion = fields.Selection([('REDUCCION', 'Reducción'),('AMPLIACION', 'Ampliación')], string="Tipo", required=True)
    de_posicion_presupuestaria = fields.Many2one('presupuesto.partida_presupuestal', string='Posición presupuestaria', domain="[('control_contable_presupuestalc', '=', 0), ('capitulo', '>=', 1), ('capitulo', '<=', 5), ('concepto', '>', 0)]")
    de_centro_gestor = fields.Many2one('presupuesto.centro_gestor', string='Centro gestor', readonly=1,  default=get_centro_gestor_transferencia)
    de_area_funcional = fields.Many2one('presupuesto.area_funcional', string='Área funcional')
    de_importe = fields.Float(string='Importe', digits=(15, 2), default=0)
    para_posicion_presupuestaria = fields.Many2one('presupuesto.partida_presupuestal', string='Posición presupuestaria', domain="[('control_contable_presupuestalc', '=', 0), ('capitulo', '>=', 1), ('capitulo', '<=', 5), ('concepto', '>', 0)]")
    para_centro_gestor = fields.Many2one('presupuesto.centro_gestor', string='Centro gestor', readonly=1,  default=get_centro_gestor_transferencia)
    para_area_funcional = fields.Many2one('presupuesto.area_funcional', string='Área funcional')
    para_importe = fields.Float(string='Importe', digits=(15, 2), default=0)
    doc_reduccion = fields.Many2one('presupuesto.documento', readonly=1, index=True,domain=[('clase_documento.tipo_documento', '=', 'RECLASIFICACION'),('clase_documento.signo', '=', '-')])
    doc_ampliacion = fields.Many2one('presupuesto.documento', readonly=1, index=True,domain=[('clase_documento.tipo_documento', '=', 'RECLASIFICACION'),('clase_documento.signo', '=', '+')])

class viewControlPresu(models.Model):
    _name = 'presupuesto.view_cp'
    _auto = False
    _order = "partida_presupuestal asc"
    
    posicion_presupuestaria = fields.Integer(string='Posicion Presupuestaria')
    partida_presupuestal = fields.Char(string='Partida Presupuestal')
    denominacion = fields.Char(string='Nombre Partida')
    nom_capitulo = fields.Char(string='Capitulo')
    capitulo = fields.Char(string='Capitulo')
    fecha = fields.Date(string='Fecha')
    nom_mes = fields.Char(string='Mes')
    periodo = fields.Selection(catalogos.PERIODO_SELECT)
    ejercicio = fields.Selection(catalogos.EJERCICIO_SELECT)
    aprobado = fields.Float(string='Aprobado')
    remanente = fields.Float(string='Saldo inicial')
    ampliacion = fields.Float(string='Ampliacion')
    reduccion = fields.Float(string='Reduccion')
    modificado = fields.Float(string='Modificado')
    comprometido = fields.Float(string='Comprometido')
    devengado = fields.Float(string='Devengado')
    pagado = fields.Float(string='Pagado')
    ejercido = fields.Float(string='Ejercido')
    disponible = fields.Float(string='Disponible')

    def _select(self):
        select_str = """
            SELECT
                dd.control_presupuesto_id as id,
                dd.posicion_presupuestaria,
                pp.partida_presupuestal,
                pp.denominacion,
                CASE WHEN (pp.capitulo = 1) THEN 1000 
                    WHEN (pp.capitulo = 2) THEN 2000 
                    WHEN (pp.capitulo = 3) THEN 3000
                    WHEN (pp.capitulo = 5) THEN 5000 END nom_capitulo,
                pp.capitulo,
                cast(date_trunc('month',TO_TIMESTAMP(concat(pd.ejercicio, '-', pd.periodo, '-01'),'YYYY-MM-DD-DDD'))as date) fecha,
                to_char(to_timestamp(pd.periodo::text, 'MM'), 'TMMonth') nom_mes,
                pd.periodo,
                pd.ejercicio,
                SUM(CASE WHEN pd.clase_documento = 3 THEN dd.importe ELSE 0 END) aprobado,	
                SUM(CASE WHEN pd.clase_documento = 10 THEN dd.importe ELSE 0 END) remanente,	
                SUM(CASE WHEN (pd.clase_documento = 1) OR (pd.clase_documento = 4) THEN dd.importe ELSE 0 END) ampliacion,	
                SUM(CASE WHEN (pd.clase_documento = 2) OR (pd.clase_documento = 5) THEN dd.importe ELSE 0 END) reduccion,
                SUM(CASE WHEN pd.clase_documento = 3 THEN dd.importe ELSE 0 END) + SUM(CASE WHEN (pd.clase_documento = 1) OR (pd.clase_documento = 4) THEN dd.importe ELSE 0 END) + SUM(CASE WHEN pd.clase_documento = 10 THEN dd.importe ELSE 0 END) -  SUM(CASE WHEN (pd.clase_documento = 2) OR (pd.clase_documento = 5) THEN dd.importe ELSE 0 END) modificado,
                SUM(CASE WHEN pd.clase_documento = 6 THEN dd.importe ELSE 0 END) comprometido,	
                SUM(CASE WHEN pd.clase_documento = 7 THEN dd.importe ELSE 0 END) devengado,	
                SUM(CASE WHEN pd.clase_documento = 8 THEN dd.importe ELSE 0 END) pagado,	
                SUM(CASE WHEN pd.clase_documento = 9 THEN dd.importe ELSE 0 END) ejercido,
                ((SUM(CASE WHEN pd.clase_documento = 3 THEN dd.importe ELSE 0 END) + SUM(CASE WHEN (pd.clase_documento = 1) OR (pd.clase_documento = 4) THEN dd.importe ELSE 0 END) + SUM(CASE WHEN pd.clase_documento = 10 THEN dd.importe ELSE 0 END) ) -  SUM(CASE WHEN (pd.clase_documento = 2) OR (pd.clase_documento = 5) THEN dd.importe ELSE 0 END) ) - SUM(CASE WHEN pd.clase_documento = 7 THEN dd.importe ELSE 0 END) disponible
        """
        return select_str

    def _group_by(self):
        group_by_str = """
            GROUP BY
                dd.control_presupuesto_id,
                dd.posicion_presupuestaria,
                pp.partida_presupuestal,
                pp.capitulo,
                pp.denominacion,
                pd.periodo,
                pd.ejercicio
        """
        return group_by_str

    def _order_by(self):
        order_by_str = """
            ORDER BY
                pp.partida_presupuestal
        """
        return order_by_str

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
            CREATE view %s as
                %s
                FROM presupuesto_detalle_documento dd
                INNER JOIN presupuesto_partida_presupuestal pp ON dd.posicion_presupuestaria = pp.id
                INNER JOIN presupuesto_documento pd ON dd.documento_id = pd.id
                WHERE status='open'
                %s
                %s
        """ % (self._table, self._select(), self._group_by(), self._order_by()))
        
    
    @api.depends(
        'ejercicio',
        'periodo',
        'partida_presupuestal'
    )
    def name_get(self):
        result = []
        for part_pres in self:
            name = '%s/%s/%s' % (
                part_pres.ejercicio,
                part_pres.periodo,
                part_pres.partida_presupuestal
            )
            result.append((part_pres.id, name))
        return result

    detalle_documento_original_ids = fields.One2many(
        'presupuesto.detalle_documento',
        'control_presupuesto_id',
        domain=[('documento_id.clase_documento.tipo_documento','=','ORIGINAL')],
        string='Documento',
    )
    detalle_documento_remanente_ids = fields.One2many(
        'presupuesto.detalle_documento',
        'control_presupuesto_id',
        domain=[('documento_id.clase_documento.tipo_documento','=','REMANENTE'),
                ('documento_id.status', '!=', 'close')],
        string='Documento',
    )

    detalle_documento_comprometido_ids = fields.One2many(
        'presupuesto.detalle_documento',
        'control_presupuesto_id',
        domain=[('documento_id.clase_documento.tipo_documento','=','COMPROMETIDO'),
                ('documento_id.status', '!=', 'close')],
        string='Documento',
    )

    detalle_documento_devengado_ids = fields.One2many(
        'presupuesto.detalle_documento',
        'control_presupuesto_id',
        domain=[('documento_id.clase_documento.tipo_documento','=','DEVENGADO'),
                ('documento_id.status', '!=', 'close')],
        string='Documento',
    )

    detalle_documento_ejercido_ids = fields.One2many(
        'presupuesto.detalle_documento',
        'control_presupuesto_id',
        domain=[('documento_id.clase_documento.tipo_documento', '=', 'EJERCIDO'),
                ('documento_id.status', '!=', 'close')],
        string='Documento'
    )

    detalle_documento_pagado_ids = fields.One2many(
        'presupuesto.detalle_documento',
        'control_presupuesto_id',
        domain=[('documento_id.clase_documento.tipo_documento','=','PAGADO'),
                ('documento_id.status', '!=', 'close')],
        string='Documento',
    )

    detalle_documento_ampliacion_ids = fields.One2many(
        'presupuesto.detalle_documento',
        'control_presupuesto_id',
        domain=['|',('documento_id.clase_documento.tipo_documento','=','AMPLIACION'),
                ('documento_id.clase_documento.tipo_documento', '=', 'RECLASIFICACION'),
                ('documento_id.clase_documento.signo', '=', '+'),
                ('documento_id.status', '!=', 'close')],
        string='Documento',
    )

    detalle_documento_reduccion_ids = fields.One2many(
        'presupuesto.detalle_documento',
        'control_presupuesto_id',
        domain=['|',('documento_id.clase_documento.tipo_documento','=','REDUCCION'),
                ('documento_id.clase_documento.tipo_documento', '=', 'RECLASIFICACION'),
                ('documento_id.clase_documento.signo', '=', '-'),
                ('documento_id.status', '!=', 'close')],
        string='Documento',
    )

    presupuesto_aprobado = fields.Float(
        string='Presupuesto Aprobado',
        compute='_presupuesto_aprobado'
    )

    presupuesto_remanente = fields.Float(
        string='Saldo Inicial - Remanente',
        compute='_presupuesto_remanente'
    )

    presupuesto_modificado = fields.Float(
        string='Presupuesto Modificado',
        compute='_presupuesto_modificado'
    )

    presupuesto_modificado_disponible = fields.Float(
        string='Presupuesto Modificado',
        compute='_presupuesto_modificado_disponible'
    )

    presupuesto_ampliacion = fields.Float(
        string='Presupuesto Ampliacion',
        compute='_presupuesto_ampliacion'
    )

    presupuesto_reduccion = fields.Float(
        string='Presupuesto Reduccion',
        compute='_presupuesto_reduccion'
    )

    presupuesto_devengado = fields.Float(
        string='Presupuesto Devengado',
        compute='_presupuesto_devengado'
    )

    presupuesto_disponible = fields.Float(
        string='Presupuesto Disponible',
        compute='_presupuesto_disponible'
    )

    @api.depends(
        'aprobado',
        'ampliacion',
        'reduccion',
        'remanente',
        'devengado',
        'modificado'
        )

    def _presupuesto_aprobado(self):
        for r in self:
            r.presupuesto_aprobado = r.aprobado

    def _presupuesto_remanente(self):
        for r in self:
            r.presupuesto_remanente = r.remanente

    def _presupuesto_ampliacion(self):
        for r in self:
            r.presupuesto_ampliacion = r.ampliacion

    def _presupuesto_reduccion(self):
        for r in self:
            r.presupuesto_reduccion = r.reduccion * -1

    def _presupuesto_modificado(self):
        for r in self:
            r.presupuesto_modificado = r.aprobado + r.ampliacion + r.remanente - r.reduccion

    def _presupuesto_modificado_disponible(self):
        for r in self:
            r.presupuesto_modificado_disponible = r.aprobado + r.ampliacion + r.remanente - r.reduccion

    def _presupuesto_devengado(self):
        for r in self:
            r.presupuesto_devengado = r.devengado * -1

    def _presupuesto_disponible(self):
        for r in self:
            r.presupuesto_disponible = r.modificado - r.devengado

class PresupuestoAreaFuncionaMinistracion(models.Model):
    _name = 'presupuesto.area.funcional.ministracion'
    _description = 'Area funcional ministraciones'
    _rec_name = 'name'

    name = fields.Char(string="Nombre", required=True)
    code = fields.Char(string='Codigo',required=True)

class PresupuestoRubrosIngreso(models.Model):
    _name = 'presupuesto.rubro.ingreso'
    _description = 'RUBRO DE INGRESOS'
    _rec_name = 'name'

    name = fields.Char(string="Nombre", required=True)
    diario=fields.Many2one('account.journal', string='Diario')

class PresupuestoMinistracion(models.Model):
    _name = 'presupuesto.ministracion'
    _description = 'Ministraciones presupuestales'
    _rec_name = 'name'

    ejercicio = fields.Selection(catalogos.EJERCICIO_SELECT, required=True)
    periodo = fields.Selection(catalogos.PERIODO_SELECT, required=True)
    area_funcional_ministracion = fields.Many2one('presupuesto.area.funcional.ministracion', string='Area Funcional',required=True)
    centro_gestor = fields.Many2one('presupuesto.centro_gestor', string='Centro gestor')
    area_funcional_m = fields.Char(string='Area Funcional')
    posicion_presupuestaria_m = fields.Char(default='41411100', string="Posicion Presupuestal", readonly=True)
    importe_autorizado = fields.Float(string='Importe', digits=(15, 2), required=True, default=0)
    ampliacion_gdf = fields.Float(string='Ampliacion GDF', digits=(15, 2), required=True, default=0)
    ampliacion_otros_ingresos = fields.Float(string='Ampliacion Otros Ingresos', digits=(15, 2), required=True, default=0)
    reducciones = fields.Float(string='Reducciones', digits=(15, 2), required=True, default=0)
    importe_devengado = fields.Float(string='Importe Devengado', digits=(15, 2), required=True, default=0)
    importe_recaudado = fields.Float(string='Importe Recaudado', digits=(15, 2), required=True, default=0)
    modificado = fields.Float(string="Modificado", digits=(15, 2), default=0, compute="_ingreso_modificado")
    ampliacion = fields.Float(string="Ampliacion", digits=(15, 2), default=0, compute="_ampliacion_acumulada")
    name = fields.Char(string="Ampliacion", digits=(15, 2), default=0, compute="_name_ministreacion")
    rubro_ingreso = fields.Many2one('presupuesto.rubro.ingreso', string='Rubro de ingreso')

    
    
    @api.onchange('area_funcional_ministracion')
    def _onchange_area_funcional(self):
        if self.area_funcional_ministracion.id:
            self.update({'area_funcional_m': str(self.area_funcional_ministracion.code)})
    
    @api.depends('importe_autorizado', 'ampliacion_otros_ingresos', 'reducciones')
    def _ingreso_modificado(self):
        for r in self:
            r.modificado = r.importe_autorizado + r.ampliacion_otros_ingresos - r.reducciones

    @api.depends('ampliacion_gdf', 'ampliacion_otros_ingresos')
    def _ampliacion_acumulada(self):
        for r in self:
            r.ampliacion = r.ampliacion_gdf + r.ampliacion_otros_ingresos

    def _name_ministreacion(self):
        self.name=str('MIN/'+str(self.ejercicio)+'/'+str(self.periodo)+'/'+str(self.id))

class PresupuestoCanModMomentos(models.Model):
    _name = 'presupuesto.ajustes.mc'
    _description = 'Ajustes de momentos contables'
    purchase_origen=fields.Many2one('purchase.order', string='Compra',required=True)
    documento_origen=fields.Many2one('presupuesto.documento', string='Documento presupuestal',required=True)
    asiento_origen=fields.Many2one('account.move', string='Asiento',required=True)
    tipo_ajuste=fields.Selection([('cancel',u'Cancelación'),('+','Ajuste +'),('-','Ajuste -')],required=True)
    fecha_doc=fields.Date(string='Fecha',required=True)
    importe_ajuste=fields.Float(string='Importe')
    partidas_doc = fields.Many2one('presupuesto.detalle_documento',string='Partidas documento')
    compute_np=fields.Integer(string='No. Partidas')
    status=fields.Char(string='Status',default='draft')

    
    def name_get(self):
        result = []
        for doc in self:
            name = 'Ajuste %s' % (doc.id)
            result.append((doc.id, name))
        return result

    
    @api.onchange('purchase_origen')
    def _onchange_purchase(self):
        if self.purchase_origen.id:
            return {'domain': {'documento_origen': [('compra_id', '=', self.purchase_origen.id)]}}
    
    @api.onchange('documento_origen')
    def _onchange_purchase_compute(self):
        if self.documento_origen.id:
            return {'domain': {'partidas_doc': [('documento_id', '=', self.documento_origen.id)]}}

    @api.onchange('documento_origen')
    def _onchange_documento(self):
        if self.documento_origen.id:
            numero_p=len(self.documento_origen.detalle_documento_ids)
            asiento=self.env['account.move'].search([('ref','=',self.documento_origen.id)], limit=1)
            self.update({'asiento_origen': asiento[0].id})
            self.update({'compute_np': numero_p})
    
    
    def _compute_np(self):
        if self.documento_origen.id:
            numero_p=len(self.documento_origen.detalle_documento_ids)
            self.compute_np=numero_p

    
    def save_ajust(self):
        obj_documento = self.env['presupuesto.documento']
        fecha_orden = datetime.strptime(self.fecha_doc, '%Y-%m-%d')
        ejercicio = fecha_orden.year
        periodo = fecha_orden.month
        version = self.env['presupuesto.version'].search([], limit=1)
        cls_doc = self.env['presupuesto.clase_documento'].search([('tipo_documento','=','AJUSTE')], limit=1)

        if (self.partidas_doc):
            compras = []
            for item in self.partidas_doc:
                compra = [0, False,
                    {
                        'centro_gestor': item.centro_gestor.id,
                        'area_funcional': item.area_funcional.id,
                        'fondo_economico': item.fondo_economico.id,
                        'posicion_presupuestaria': item.posicion_presupuestaria.id,
                        'importe': self.importe_ajuste
                    }
                ]
                compras.append(compra)
                
            
            documento = obj_documento.create({
                'clase_documento': cls_doc.id,
                'version': version.id,
                'ejercicio': ejercicio,
                'periodo': periodo,
                'fecha_contabilizacion': self.date_order,
                'fecha_documento': self.date_order,
                'detalle_documento_ids': compras,
                'compra_id': self.id
            })

class viewControlPresuAcumulado(models.Model):
    _name = 'presupuestos.view_cp_acumulado'
    _auto = False
    _order = "partida_presupuestal asc"

    posicion_presupuestaria = fields.Integer(string='Posicion Presupuestaria')
    partida_presupuestal = fields.Char(string='Partida Presupuestal')
    denominacion = fields.Char(string='Nombre Partida')
    nom_capitulo = fields.Char(string='Capitulo')
    capitulo = fields.Char(string='Capitulo')
    periodo = fields.Selection(catalogos.PERIODO_SELECT)
    nom_mes = fields.Char(string='Mes')
    ejercicio = fields.Selection(catalogos.EJERCICIO_SELECT)
    aprobado = fields.Float(string='Aprobado')
    ampliacion = fields.Float(string='Ampliacion')
    reduccion = fields.Float(string='Reduccion')
    modificado = fields.Float(string='Modificado')
    comprometido = fields.Float(string='Comprometido')
    devengado = fields.Float(string='Devengado')
    pagado = fields.Float(string='Pagado')
    ejercido = fields.Float(string='Ejercido')
    mod_comp = fields.Float(string='Modificado_Comprometido')
    comp_dev = fields.Float(string='Comprometido_Devengado')
    mod_dev = fields.Float(string='Modificado_Devengado')
    dev_ejer = fields.Float(string='Devengado_Ejercido')
    dev_pag = fields.Float(string='Devengado_Ejercido')

    def _select(self):
        select_str = """
            SELECT
                dd.control_presupuesto_id as id,
                dd.posicion_presupuestaria,
                pp.partida_presupuestal,
                pp.denominacion,
                CASE WHEN (pp.capitulo = 1) THEN 1000 
                    WHEN (pp.capitulo = 2) THEN 2000 
                    WHEN (pp.capitulo = 3) THEN 3000
                    WHEN (pp.capitulo = 5) THEN 5000 END nom_capitulo,
                pp.capitulo,
                pd.periodo,
                to_char(to_timestamp(pd.periodo::text, 'MM'), 'TMMonth') nom_mes,
                pd.ejercicio,
                SUM(CASE WHEN pd.clase_documento = 3 THEN dd.importe ELSE 0 END) aprobado,	
                SUM(CASE WHEN (pd.clase_documento = 2) OR (pd.clase_documento = 5) THEN dd.importe ELSE 0 END) reduccion,
                SUM(CASE WHEN (pd.clase_documento = 1) OR (pd.clase_documento = 4) THEN dd.importe ELSE 0 END) ampliacion,	
                SUM(CASE WHEN pd.clase_documento = 3 THEN dd.importe ELSE 0 END) + SUM(CASE WHEN (pd.clase_documento = 1) OR (pd.clase_documento = 4) THEN dd.importe ELSE 0 END)  -  SUM(CASE WHEN (pd.clase_documento = 2) OR (pd.clase_documento = 5) THEN dd.importe ELSE 0 END) modificado,
                CASE 
                    WHEN (pp.capitulo = 1) OR (pp.partida_presupuestal = '398100') OR (pp.partida_presupuestal = '398200') THEN SUM(CASE WHEN pd.clase_documento = 3 THEN dd.importe ELSE 0 END) + SUM(CASE WHEN (pd.clase_documento = 1) OR (pd.clase_documento = 4) THEN dd.importe ELSE 0 END)  -  SUM(CASE WHEN (pd.clase_documento = 2) OR (pd.clase_documento = 5) THEN dd.importe ELSE 0 END) 
                    WHEN (pp.capitulo = 2) THEN SUM(CASE WHEN pd.clase_documento = 6 THEN dd.importe ELSE 0 END)
					WHEN (pp.capitulo = 3 AND pp.partida_presupuestal != '398100' AND pp.partida_presupuestal !='398200') THEN SUM(CASE WHEN pd.clase_documento = 6 THEN dd.importe ELSE 0 END)
                    WHEN (pp.capitulo = 5) THEN SUM(CASE WHEN pd.clase_documento = 6 THEN dd.importe ELSE 0 END) END comprometido,
                SUM(CASE WHEN pd.clase_documento = 7 THEN dd.importe ELSE 0 END) devengado,	
                SUM(CASE WHEN pd.clase_documento = 9 THEN dd.importe ELSE 0 END) ejercido,
                SUM(CASE WHEN pd.clase_documento = 8 THEN dd.importe ELSE 0 END) pagado,
                CASE WHEN (pp.capitulo = 1) OR (pp.partida_presupuestal = '398100') OR (pp.partida_presupuestal = '398200') THEN ((SUM(CASE WHEN pd.clase_documento = 3 THEN dd.importe ELSE 0 END) + SUM(CASE WHEN (pd.clase_documento = 1) OR (pd.clase_documento = 4) THEN dd.importe ELSE 0 END)  -  SUM(CASE WHEN (pd.clase_documento = 2) OR (pd.clase_documento = 5) THEN dd.importe ELSE 0 END)) - (SUM(CASE WHEN pd.clase_documento = 3 THEN dd.importe ELSE 0 END) + SUM(CASE WHEN (pd.clase_documento = 1) OR (pd.clase_documento = 4) THEN dd.importe ELSE 0 END)  -  SUM(CASE WHEN (pd.clase_documento = 2) OR (pd.clase_documento = 5) THEN dd.importe ELSE 0 END)))
                    WHEN (pp.capitulo = 2) THEN ((SUM(CASE WHEN pd.clase_documento = 3 THEN dd.importe ELSE 0 END) + SUM(CASE WHEN (pd.clase_documento = 1) OR (pd.clase_documento = 4) THEN dd.importe ELSE 0 END)  -  SUM(CASE WHEN (pd.clase_documento = 2) OR (pd.clase_documento = 5) THEN dd.importe ELSE 0 END)) - SUM(CASE WHEN pd.clase_documento = 6 THEN dd.importe ELSE 0 END))
                    WHEN (pp.capitulo = 3) AND (pp.partida_presupuestal != '398100') AND (pp.partida_presupuestal !='398200') THEN ((SUM(CASE WHEN pd.clase_documento = 3 THEN dd.importe ELSE 0 END) + SUM(CASE WHEN (pd.clase_documento = 1) OR (pd.clase_documento = 4) THEN dd.importe ELSE 0 END)  -  SUM(CASE WHEN (pd.clase_documento = 2) OR (pd.clase_documento = 5) THEN dd.importe ELSE 0 END)) - SUM(CASE WHEN pd.clase_documento = 6 THEN dd.importe ELSE 0 END))
                    WHEN (pp.capitulo = 5) THEN ((SUM(CASE WHEN pd.clase_documento = 3 THEN dd.importe ELSE 0 END) + SUM(CASE WHEN (pd.clase_documento = 1) OR (pd.clase_documento = 4) THEN dd.importe ELSE 0 END)  -  SUM(CASE WHEN (pd.clase_documento = 2) OR (pd.clase_documento = 5) THEN dd.importe ELSE 0 END)) - SUM(CASE WHEN pd.clase_documento = 6 THEN dd.importe ELSE 0 END)) END mod_comp,
                CASE WHEN (pp.capitulo = 1) OR (pp.partida_presupuestal = '398100') OR (pp.partida_presupuestal = '398200') THEN ((SUM(CASE WHEN pd.clase_documento = 3 THEN dd.importe ELSE 0 END) + SUM(CASE WHEN (pd.clase_documento = 1) OR (pd.clase_documento = 4) THEN dd.importe ELSE 0 END)  -  SUM(CASE WHEN (pd.clase_documento = 2) OR (pd.clase_documento = 5) THEN dd.importe ELSE 0 END)) - SUM(CASE WHEN pd.clase_documento = 7 THEN dd.importe ELSE 0 END))
                    WHEN (pp.capitulo = 2) THEN ((SUM(CASE WHEN pd.clase_documento = 6 THEN dd.importe ELSE 0 END)) - SUM(CASE WHEN pd.clase_documento = 7 THEN dd.importe ELSE 0 END))
                    WHEN (pp.capitulo = 3) AND (pp.partida_presupuestal != '398100') AND (pp.partida_presupuestal !='398200') THEN ((SUM(CASE WHEN pd.clase_documento = 6 THEN dd.importe ELSE 0 END)) - SUM(CASE WHEN pd.clase_documento = 7 THEN dd.importe ELSE 0 END))
                    WHEN (pp.capitulo = 5) THEN ((SUM(CASE WHEN pd.clase_documento = 6 THEN dd.importe ELSE 0 END)) - SUM(CASE WHEN pd.clase_documento = 7 THEN dd.importe ELSE 0 END)) END comp_dev,
                ((SUM(CASE WHEN pd.clase_documento = 3 THEN dd.importe ELSE 0 END) + SUM(CASE WHEN (pd.clase_documento = 1) OR (pd.clase_documento = 4) THEN dd.importe ELSE 0 END)  -  SUM(CASE WHEN (pd.clase_documento = 2) OR (pd.clase_documento = 5) THEN dd.importe ELSE 0 END)) - SUM(CASE WHEN pd.clase_documento = 7 THEN dd.importe ELSE 0 END)) mod_dev,
                ((SUM(CASE WHEN pd.clase_documento = 7 THEN dd.importe ELSE 0 END)) - SUM(CASE WHEN pd.clase_documento = 9 THEN dd.importe ELSE 0 END)) dev_ejer,
                ((SUM(CASE WHEN pd.clase_documento = 7 THEN dd.importe ELSE 0 END)) - SUM(CASE WHEN pd.clase_documento = 8 THEN dd.importe ELSE 0 END)) dev_pag
        """
        return select_str

    def _group_by(self):
        group_by_str = """
            GROUP BY
                dd.control_presupuesto_id,
                dd.posicion_presupuestaria,
                pp.partida_presupuestal,
                pp.capitulo,
                pp.denominacion,
                pd.periodo,
                pd.ejercicio
        """
        return group_by_str

    def _order_by(self):
        order_by_str = """
            ORDER BY
                pp.partida_presupuestal
        """
        return order_by_str

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
            CREATE view %s as
                %s
                FROM presupuesto_detalle_documento dd
                INNER JOIN presupuesto_partida_presupuestal pp ON dd.posicion_presupuestaria = pp.id
                INNER JOIN presupuesto_documento pd ON dd.documento_id = pd.id
                WHERE status='open'
                %s
                %s
        """ % (self._table, self._select(), self._group_by(), self._order_by()))

class viewControlPresuAcumulado(models.Model):
    _name = 'presupuestos.view_cp_acumulado_cp'
    _auto = False
    _order = "partida_presupuestal asc"

    posicion_presupuestaria = fields.Integer(string='Posicion Presupuestaria')
    partida_presupuestal = fields.Char(string='Partida Presupuestal')
    denominacion = fields.Char(string='Nombre Partida')
    nom_capitulo = fields.Char(string='Capitulo')
    capitulo = fields.Char(string='Capitulo')
    periodo = fields.Selection(catalogos.PERIODO_SELECT)
    nom_mes = fields.Char(string='Mes')
    ejercicio = fields.Selection(catalogos.EJERCICIO_SELECT)
    aprobado = fields.Float(string='Aprobado')
    ampliacion = fields.Float(string='Ampliacion')
    reduccion = fields.Float(string='Reduccion')
    modificado = fields.Float(string='Modificado')
    comprometido = fields.Float(string='Comprometido')
    devengado = fields.Float(string='Devengado')
    pagado = fields.Float(string='Pagado')
    ejercido = fields.Float(string='Ejercido')
    mod_comp = fields.Float(string='Modificado_Comprometido')
    comp_dev = fields.Float(string='Comprometido_Devengado')
    mod_dev = fields.Float(string='Modificado_Devengado')
    dev_ejer = fields.Float(string='Devengado_Ejercido')
    dev_pag = fields.Float(string='Devengado_Ejercido')
    reingreso = fields.Float(string='reingreso')
    total_reingreso = fields.Float(string='total_reingreso')

    def _select(self):
        select_str = """
            SELECT
                dd.control_presupuesto_id as id,
                dd.posicion_presupuestaria,
                pp.partida_presupuestal,
                pp.denominacion,
                CASE WHEN (pp.capitulo = 1) THEN 1000 
                    WHEN (pp.capitulo = 2) THEN 2000 
                    WHEN (pp.capitulo = 3) THEN 3000
                    WHEN (pp.capitulo = 5) THEN 5000 END nom_capitulo,
                pp.capitulo,
                pd.periodo,
                to_char(to_timestamp(pd.periodo::text, 'MM'), 'TMMonth') nom_mes,
                pd.ejercicio,
                SUM(CASE WHEN pd.clase_documento = 3 THEN dd.importe ELSE 0 END) aprobado,	
                SUM(CASE WHEN (pd.clase_documento = 2) OR (pd.clase_documento = 5) THEN dd.importe ELSE 0 END) reduccion,
                SUM(CASE WHEN (pd.clase_documento = 1) OR (pd.clase_documento = 4) THEN dd.importe ELSE 0 END) ampliacion,	
                SUM(CASE WHEN pd.clase_documento = 3 THEN dd.importe ELSE 0 END) + SUM(CASE WHEN (pd.clase_documento = 1) OR (pd.clase_documento = 4) THEN dd.importe ELSE 0 END)  -  SUM(CASE WHEN (pd.clase_documento = 2) OR (pd.clase_documento = 5) THEN dd.importe ELSE 0 END) modificado,
                CASE 
                    WHEN (pp.capitulo = 1) OR (pp.partida_presupuestal = '398100') OR (pp.partida_presupuestal = '398200') THEN SUM(CASE WHEN pd.clase_documento = 3 THEN dd.importe ELSE 0 END) + SUM(CASE WHEN (pd.clase_documento = 1) OR (pd.clase_documento = 4) THEN dd.importe ELSE 0 END)  -  SUM(CASE WHEN (pd.clase_documento = 2) OR (pd.clase_documento = 5) THEN dd.importe ELSE 0 END) 
                    WHEN (pp.capitulo = 2) THEN SUM(CASE WHEN pd.clase_documento = 6 THEN dd.importe ELSE 0 END)
					WHEN (pp.capitulo = 3 AND pp.partida_presupuestal != '398100' AND pp.partida_presupuestal !='398200') THEN SUM(CASE WHEN pd.clase_documento = 6 THEN dd.importe ELSE 0 END)
                    WHEN (pp.capitulo = 5) THEN SUM(CASE WHEN pd.clase_documento = 6 THEN dd.importe ELSE 0 END) END comprometido,
                SUM(CASE WHEN pd.clase_documento = 7 THEN dd.importe ELSE 0 END) devengado,	
                SUM(CASE WHEN pd.clase_documento = 9 THEN dd.importe ELSE 0 END) ejercido,
                SUM(CASE WHEN pd.clase_documento = 8 THEN dd.importe ELSE 0 END) pagado,
                CASE WHEN (pp.capitulo = 1) OR (pp.partida_presupuestal = '398100') OR (pp.partida_presupuestal = '398200') THEN ((SUM(CASE WHEN pd.clase_documento = 3 THEN dd.importe ELSE 0 END) + SUM(CASE WHEN (pd.clase_documento = 1) OR (pd.clase_documento = 4) THEN dd.importe ELSE 0 END)  -  SUM(CASE WHEN (pd.clase_documento = 2) OR (pd.clase_documento = 5) THEN dd.importe ELSE 0 END)) - (SUM(CASE WHEN pd.clase_documento = 3 THEN dd.importe ELSE 0 END) + SUM(CASE WHEN (pd.clase_documento = 1) OR (pd.clase_documento = 4) THEN dd.importe ELSE 0 END)  -  SUM(CASE WHEN (pd.clase_documento = 2) OR (pd.clase_documento = 5) THEN dd.importe ELSE 0 END)))
                    WHEN (pp.capitulo = 2) THEN ((SUM(CASE WHEN pd.clase_documento = 3 THEN dd.importe ELSE 0 END) + SUM(CASE WHEN (pd.clase_documento = 1) OR (pd.clase_documento = 4) THEN dd.importe ELSE 0 END)  -  SUM(CASE WHEN (pd.clase_documento = 2) OR (pd.clase_documento = 5) THEN dd.importe ELSE 0 END)) - SUM(CASE WHEN pd.clase_documento = 6 THEN dd.importe ELSE 0 END))
                    WHEN (pp.capitulo = 3) AND (pp.partida_presupuestal != '398100') AND (pp.partida_presupuestal !='398200') THEN ((SUM(CASE WHEN pd.clase_documento = 3 THEN dd.importe ELSE 0 END) + SUM(CASE WHEN (pd.clase_documento = 1) OR (pd.clase_documento = 4) THEN dd.importe ELSE 0 END)  -  SUM(CASE WHEN (pd.clase_documento = 2) OR (pd.clase_documento = 5) THEN dd.importe ELSE 0 END)) - SUM(CASE WHEN pd.clase_documento = 6 THEN dd.importe ELSE 0 END))
                    WHEN (pp.capitulo = 5) THEN ((SUM(CASE WHEN pd.clase_documento = 3 THEN dd.importe ELSE 0 END) + SUM(CASE WHEN (pd.clase_documento = 1) OR (pd.clase_documento = 4) THEN dd.importe ELSE 0 END)  -  SUM(CASE WHEN (pd.clase_documento = 2) OR (pd.clase_documento = 5) THEN dd.importe ELSE 0 END)) - SUM(CASE WHEN pd.clase_documento = 6 THEN dd.importe ELSE 0 END)) END mod_comp,
                CASE WHEN (pp.capitulo = 1) OR (pp.partida_presupuestal = '398100') OR (pp.partida_presupuestal = '398200') THEN ((SUM(CASE WHEN pd.clase_documento = 3 THEN dd.importe ELSE 0 END) + SUM(CASE WHEN (pd.clase_documento = 1) OR (pd.clase_documento = 4) THEN dd.importe ELSE 0 END)  -  SUM(CASE WHEN (pd.clase_documento = 2) OR (pd.clase_documento = 5) THEN dd.importe ELSE 0 END)) - SUM(CASE WHEN pd.clase_documento = 7 THEN dd.importe ELSE 0 END))
                    WHEN (pp.capitulo = 2) THEN ((SUM(CASE WHEN pd.clase_documento = 6 THEN dd.importe ELSE 0 END)) - SUM(CASE WHEN pd.clase_documento = 7 THEN dd.importe ELSE 0 END))
                    WHEN (pp.capitulo = 3) AND (pp.partida_presupuestal != '398100') AND (pp.partida_presupuestal !='398200') THEN ((SUM(CASE WHEN pd.clase_documento = 6 THEN dd.importe ELSE 0 END)) - SUM(CASE WHEN pd.clase_documento = 7 THEN dd.importe ELSE 0 END))
                    WHEN (pp.capitulo = 5) THEN ((SUM(CASE WHEN pd.clase_documento = 6 THEN dd.importe ELSE 0 END)) - SUM(CASE WHEN pd.clase_documento = 7 THEN dd.importe ELSE 0 END)) END comp_dev,
                ((SUM(CASE WHEN pd.clase_documento = 3 THEN dd.importe ELSE 0 END) + SUM(CASE WHEN (pd.clase_documento = 1) OR (pd.clase_documento = 4) THEN dd.importe ELSE 0 END)  -  SUM(CASE WHEN (pd.clase_documento = 2) OR (pd.clase_documento = 5) THEN dd.importe ELSE 0 END)) - SUM(CASE WHEN pd.clase_documento = 7 THEN dd.importe ELSE 0 END)) mod_dev,
                ((SUM(CASE WHEN pd.clase_documento = 7 THEN dd.importe ELSE 0 END)) - SUM(CASE WHEN pd.clase_documento = 9 THEN dd.importe ELSE 0 END)) dev_ejer,
                ((SUM(CASE WHEN pd.clase_documento = 7 THEN dd.importe ELSE 0 END)) - SUM(CASE WHEN pd.clase_documento = 8 THEN dd.importe ELSE 0 END)) dev_pag,
                ((SUM(CASE WHEN pd.clase_documento = 6 THEN dd.importe ELSE 0 END)) - SUM(CASE WHEN pd.clase_documento = 7 THEN dd.importe ELSE 0 END)) reingreso,
                ((SUM(CASE WHEN pd.clase_documento = 6 THEN dd.importe ELSE 0 END)) -  (SUM(CASE WHEN pd.clase_documento = 6 THEN dd.importe ELSE 0 END)) - SUM(CASE WHEN pd.clase_documento = 7 THEN dd.importe ELSE 0 END))*-1 total_reingreso
        """
        return select_str

    def _group_by(self):
        group_by_str = """
            GROUP BY
                dd.control_presupuesto_id,
                dd.posicion_presupuestaria,
                pp.partida_presupuestal,
                pp.capitulo,
                pp.denominacion,
                pd.periodo,
                pd.ejercicio
        """
        return group_by_str

    def _order_by(self):
        order_by_str = """
            ORDER BY
                pp.partida_presupuestal
        """
        return order_by_str

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
            CREATE view %s as
                %s
                FROM presupuesto_detalle_documento dd
                INNER JOIN presupuesto_partida_presupuestal pp ON dd.posicion_presupuestaria = pp.id
                INNER JOIN presupuesto_documento pd ON dd.documento_id = pd.id
                WHERE status='open'
                %s
                %s
        """ % (self._table, self._select(), self._group_by(), self._order_by()))

class viewControlPresuAcumulado(models.Model):
    _name = 'presupuestos.view_cp_operativo'
    _auto = False
    _order = "partida_presupuestal asc"
    
    posicion_presupuestaria = fields.Integer(string='Posicion Presupuestaria')
    partida_presupuestal = fields.Char(string='Partida Presupuestal')
    denominacion = fields.Char(string='Nombre Partida')
    nom_capitulo = fields.Char(string='Capitulo')
    capitulo = fields.Char(string='Capitulo')
    fecha = fields.Date(string='Fecha')
    nom_mes = fields.Char(string='Mes')
    periodo = fields.Selection(catalogos.PERIODO_SELECT)
    periodo_origen = fields.Selection(catalogos.PERIODO_SELECT)
    ejercicio = fields.Selection(catalogos.EJERCICIO_SELECT)
    aprobado = fields.Float(string='Aprobado')
    remanente = fields.Float(string='Saldo inicial')
    ampliacion = fields.Float(string='Ampliacion')
    reduccion = fields.Float(string='Reduccion')
    modificado = fields.Float(string='Modificado')
    comprometido = fields.Float(string='Comprometido')
    devengado = fields.Float(string='Devengado')
    pagado = fields.Float(string='Pagado')
    ejercido = fields.Float(string='Ejercido')
    disponible = fields.Float(string='Disponible')

    def _select(self):
        select_str = """
            SELECT
                dd.control_presupuesto_id as id,
                dd.posicion_presupuestaria,
                pp.partida_presupuestal,
                pp.denominacion,
                CASE WHEN (pp.capitulo = 1) THEN 1000 
                    WHEN (pp.capitulo = 2) THEN 2000 
                    WHEN (pp.capitulo = 3) THEN 3000
                    WHEN (pp.capitulo = 5) THEN 5000 END nom_capitulo,
                pp.capitulo,
                cast(date_trunc('month',TO_TIMESTAMP(concat(pd.ejercicio, '-', pd.periodo, '-01'),'YYYY-MM-DD-DDD'))as date) fecha,
                to_char(to_timestamp(pd.periodo::text, 'MM'), 'TMMonth') nom_mes,
                pd.periodo,
                coalesce(pd.periodo_origen, pd.periodo) as periodo_origen,
                pd.ejercicio,
                sum( case when pd.clase_documento = 3 then dd.importe else 0 end) as aprobado,
	sum( case when pd.clase_documento = 10 then dd.importe else 0 end) as remanente,
	sum( case when pd.clase_documento = 1 or pd.clase_documento = 4 then dd.importe else 0 end) as ampliacion,
	sum( case when pd.clase_documento = 2 or pd.clase_documento = 5 then dd.importe else 0 end) as reduccion,
	sum( case when pd.clase_documento = 3 then dd.importe else 0 end) + sum( case when pd.clase_documento = 1 or pd.clase_documento = 4 then dd.importe else 0 end) + sum( case when pd.clase_documento = 10 then dd.importe else 0 end) - sum( case when pd.clase_documento = 2 or pd.clase_documento = 5 then dd.importe else 0 end) as modificado,
	sum( case when pd.clase_documento = 6 then dd.importe else 0 end) as comprometido,
	sum( case when pd.clase_documento = 7 then dd.importe else 0 end) as devengado,
	sum( case when pd.clase_documento = 9 then dd.importe else 0 end) as ejercido,
	sum( case when pd.clase_documento = 8 then dd.importe else 0 end) as pagado,
	sum( case when pd.clase_documento = 3 then dd.importe else 0 end) + sum( case when pd.clase_documento = 1 or pd.clase_documento = 4 then dd.importe else 0 end) + sum( case when pd.clase_documento = 10 then dd.importe else 0 end) - sum( case when pd.clase_documento = 2 or pd.clase_documento = 5 then dd.importe else 0 end) - sum( case when pd.clase_documento = 7 then dd.importe else 0 end) as disponible
"""
        return select_str

    def _group_by(self):
        group_by_str = """
            GROUP BY
                dd.control_presupuesto_id,
                dd.posicion_presupuestaria,
                pp.partida_presupuestal,
                pp.capitulo,
                pp.denominacion,
                pd.periodo,
                pd.ejercicio,
                pd.periodo_origen
        """
        return group_by_str

    def _order_by(self):
        order_by_str = """
            ORDER BY
                pp.partida_presupuestal
        """
        return order_by_str

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
            CREATE view %s as
                %s
                FROM presupuesto_detalle_documento dd
                INNER JOIN presupuesto_partida_presupuestal pp ON dd.posicion_presupuestaria = pp.id
                INNER JOIN presupuesto_documento pd ON dd.documento_id = pd.id
                WHERE status='open'
                %s
                %s
        """ % (self._table, self._select(), self._group_by(), self._order_by()))

class viewControlPresu(models.Model):
    _name = 'presupuesto.view_cp_materiales'
    _auto = False
    _order = "partida_presupuestal asc"
    
    posicion_presupuestaria = fields.Integer(string='Posicion Presupuestaria')
    partida_presupuestal = fields.Char(string='Partida Presupuestal')
    denominacion = fields.Char(string='Nombre Partida')
    nom_capitulo = fields.Char(string='Capitulo')
    capitulo = fields.Char(string='Capitulo')
    fecha = fields.Date(string='Fecha')
    nom_mes = fields.Char(string='Mes')
    periodo = fields.Selection(catalogos.PERIODO_SELECT)
    ejercicio = fields.Selection(catalogos.EJERCICIO_SELECT)
    aprobado = fields.Float(string='Aprobado')
    remanente = fields.Float(string='Saldo inicial')
    ampliacion = fields.Float(string='Ampliacion')
    reduccion = fields.Float(string='Reduccion')
    modificado = fields.Float(string='Modificado')
    comprometido = fields.Float(string='Comprometido')
    devengado = fields.Float(string='Devengado')
    pagado = fields.Float(string='Pagado')
    ejercido = fields.Float(string='Ejercido')
    disponible = fields.Float(string='Disponible')

    def _select(self):
        select_str = """
            SELECT
                dd.control_presupuesto_id as id,
                dd.posicion_presupuestaria,
                pp.partida_presupuestal,
                pp.denominacion,
                CASE
                    WHEN (pp.capitulo = 2) THEN 2000 
                    WHEN (pp.capitulo = 3) THEN 3000
                    WHEN (pp.capitulo = 5) THEN 5000 END nom_capitulo,
                pp.capitulo,
                cast(date_trunc('month',TO_TIMESTAMP(concat(pd.ejercicio, '-', pd.periodo, '-01'),'YYYY-MM-DD-DDD'))as date) fecha,
                to_char(to_timestamp(pd.periodo::text, 'MM'), 'TMMonth') nom_mes,
                pd.periodo,
                pd.ejercicio,
                SUM(CASE WHEN pd.clase_documento = 3 THEN dd.importe ELSE 0 END) aprobado,	
                SUM(CASE WHEN pd.clase_documento = 10 THEN dd.importe ELSE 0 END) remanente,	
                SUM(CASE WHEN (pd.clase_documento = 1) OR (pd.clase_documento = 4) THEN dd.importe ELSE 0 END) ampliacion,	
                SUM(CASE WHEN (pd.clase_documento = 2) OR (pd.clase_documento = 5) THEN dd.importe ELSE 0 END) reduccion,
                SUM(CASE WHEN pd.clase_documento = 3 THEN dd.importe ELSE 0 END) + SUM(CASE WHEN (pd.clase_documento = 1) OR (pd.clase_documento = 4) THEN dd.importe ELSE 0 END) + SUM(CASE WHEN pd.clase_documento = 10 THEN dd.importe ELSE 0 END) -  SUM(CASE WHEN (pd.clase_documento = 2) OR (pd.clase_documento = 5) THEN dd.importe ELSE 0 END) modificado,
                SUM(CASE WHEN pd.clase_documento = 6 THEN dd.importe ELSE 0 END) comprometido,	
                SUM(CASE WHEN pd.clase_documento = 7 THEN dd.importe ELSE 0 END) devengado,	
                SUM(CASE WHEN pd.clase_documento = 8 THEN dd.importe ELSE 0 END) pagado,	
                SUM(CASE WHEN pd.clase_documento = 9 THEN dd.importe ELSE 0 END) ejercido,
                ((SUM(CASE WHEN pd.clase_documento = 3 THEN dd.importe ELSE 0 END) + SUM(CASE WHEN (pd.clase_documento = 1) OR (pd.clase_documento = 4) THEN dd.importe ELSE 0 END) + SUM(CASE WHEN pd.clase_documento = 10 THEN dd.importe ELSE 0 END) ) -  SUM(CASE WHEN (pd.clase_documento = 2) OR (pd.clase_documento = 5) THEN dd.importe ELSE 0 END) ) - SUM(CASE WHEN pd.clase_documento = 7 THEN dd.importe ELSE 0 END) disponible
        """
        return select_str

    def _group_by(self):
        group_by_str = """
            GROUP BY
                dd.control_presupuesto_id,
                dd.posicion_presupuestaria,
                pp.partida_presupuestal,
                pp.capitulo,
                pp.denominacion,
                pd.periodo,
                pd.ejercicio
        """
        return group_by_str

    def _order_by(self):
        order_by_str = """
            ORDER BY
                pp.partida_presupuestal
        """
        return order_by_str

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
            CREATE view %s as
                %s
                FROM presupuesto_detalle_documento dd
                INNER JOIN presupuesto_partida_presupuestal pp ON dd.posicion_presupuestaria = pp.id
                INNER JOIN presupuesto_documento pd ON dd.documento_id = pd.id
                WHERE pp.capitulo!=1 and   status='open'
                %s
                %s
        """ % (self._table, self._select(), self._group_by(), self._order_by()))
        
    
    @api.depends(
        'ejercicio',
        'periodo',
        'partida_presupuestal'
    )
    def name_get(self):
        result = []
        for part_pres in self:
            name = '%s/%s/%s' % (
                part_pres.ejercicio,
                part_pres.periodo,
                part_pres.partida_presupuestal
            )
            result.append((part_pres.id, name))
        return result

    detalle_documento_original_ids = fields.One2many(
        'presupuesto.detalle_documento',
        'control_presupuesto_id',
        domain=[('documento_id.clase_documento.tipo_documento','=','ORIGINAL')],
        string='Documento',
    )
    detalle_documento_remanente_ids = fields.One2many(
        'presupuesto.detalle_documento',
        'control_presupuesto_id',
        domain=[('documento_id.clase_documento.tipo_documento','=','REMANENTE'),
                ('documento_id.status', '!=', 'close')],
        string='Documento',
    )

    detalle_documento_comprometido_ids = fields.One2many(
        'presupuesto.detalle_documento',
        'control_presupuesto_id',
        domain=[('documento_id.clase_documento.tipo_documento','=','COMPROMETIDO'),
                ('documento_id.status', '!=', 'close')],
        string='Documento',
    )

    detalle_documento_devengado_ids = fields.One2many(
        'presupuesto.detalle_documento',
        'control_presupuesto_id',
        domain=[('documento_id.clase_documento.tipo_documento','=','DEVENGADO'),
                ('documento_id.status', '!=', 'close')],
        string='Documento',
    )

    detalle_documento_ejercido_ids = fields.One2many(
        'presupuesto.detalle_documento',
        'control_presupuesto_id',
        domain=[('documento_id.clase_documento.tipo_documento', '=', 'EJERCIDO'),
                ('documento_id.status', '!=', 'close')],
        string='Documento'
    )

    detalle_documento_pagado_ids = fields.One2many(
        'presupuesto.detalle_documento',
        'control_presupuesto_id',
        domain=[('documento_id.clase_documento.tipo_documento','=','PAGADO'),
                ('documento_id.status', '!=', 'close')],
        string='Documento',
    )

    detalle_documento_ampliacion_ids = fields.One2many(
        'presupuesto.detalle_documento',
        'control_presupuesto_id',
        domain=['|',('documento_id.clase_documento.tipo_documento','=','AMPLIACION'),
                ('documento_id.clase_documento.tipo_documento', '=', 'RECLASIFICACION'),
                ('documento_id.clase_documento.signo', '=', '+'),
                ('documento_id.status', '!=', 'close')],
        string='Documento',
    )

    detalle_documento_reduccion_ids = fields.One2many(
        'presupuesto.detalle_documento',
        'control_presupuesto_id',
        domain=['|',('documento_id.clase_documento.tipo_documento','=','REDUCCION'),
                ('documento_id.clase_documento.tipo_documento', '=', 'RECLASIFICACION'),
                ('documento_id.clase_documento.signo', '=', '-'),
                ('documento_id.status', '!=', 'close')],
        string='Documento',
    )

    presupuesto_aprobado = fields.Float(
        string='Presupuesto Aprobado',
        compute='_presupuesto_aprobado'
    )

    presupuesto_remanente = fields.Float(
        string='Saldo Inicial - Remanente',
        compute='_presupuesto_remanente'
    )

    presupuesto_modificado = fields.Float(
        string='Presupuesto Modificado',
        compute='_presupuesto_modificado'
    )

    presupuesto_modificado_disponible = fields.Float(
        string='Presupuesto Modificado',
        compute='_presupuesto_modificado_disponible'
    )

    presupuesto_ampliacion = fields.Float(
        string='Presupuesto Ampliacion',
        compute='_presupuesto_ampliacion'
    )

    presupuesto_reduccion = fields.Float(
        string='Presupuesto Reduccion',
        compute='_presupuesto_reduccion'
    )

    presupuesto_devengado = fields.Float(
        string='Presupuesto Devengado',
        compute='_presupuesto_devengado'
    )

    presupuesto_disponible = fields.Float(
        string='Presupuesto Disponible',
        compute='_presupuesto_disponible'
    )

    @api.depends(
        'aprobado',
        'ampliacion',
        'reduccion',
        'remanente',
        'devengado',
        'modificado'
        )

    def _presupuesto_aprobado(self):
        for r in self:
            r.presupuesto_aprobado = r.aprobado

    def _presupuesto_remanente(self):
        for r in self:
            r.presupuesto_remanente = r.remanente

    def _presupuesto_ampliacion(self):
        for r in self:
            r.presupuesto_ampliacion = r.ampliacion

    def _presupuesto_reduccion(self):
        for r in self:
            r.presupuesto_reduccion = r.reduccion * -1

    def _presupuesto_modificado(self):
        for r in self:
            r.presupuesto_modificado = r.aprobado + r.ampliacion + r.remanente - r.reduccion

    def _presupuesto_modificado_disponible(self):
        for r in self:
            r.presupuesto_modificado_disponible = r.aprobado + r.ampliacion + r.remanente - r.reduccion

    def _presupuesto_devengado(self):
        for r in self:
            r.presupuesto_devengado = r.devengado * -1

    def _presupuesto_disponible(self):
        for r in self:
            r.presupuesto_disponible = r.modificado - r.devengado

class viewPolizasDocumento(models.Model):
    _name = 'presupuesto.view_polizas_documento'
    _auto = False
    
    aml_id = fields.Integer(string='aml_id')
    code = fields.Char(string='code')
    cuenta = fields.Integer(string='cuenta')
    capitulo = fields.Integer(string='capitulo')
    partida_id = fields.Integer(string='partida_id')
    clase_documento = fields.Integer(string='clase_documento')
    ref = fields.Char(string='ref')
    fecha_documento = fields.Date(string='fecha_documento')
    credit = fields.Float(string='credit')
    debit = fields.Float(string='debit')

    def _select(self):
        select_str = """
            select
                distinct (aml.id) aml_id,
                aa.code,
                SUBSTRING(aa.code, 1, 3 ) cuenta,
                ppp.capitulo,
                ppp.id partida_id,
                pd.clase_documento,
                am."ref",
                pd.fecha_documento,
                case when aml.journal_id in (95,103,102,73) then aml.credit*-1 else aml.credit end,
                case when aml.journal_id in (95,103,102,73) then aml.debit*-1 else aml.debit end
        """
        return select_str


    def _order_by(self):
        order_by_str = """
            ORDER BY
                aa.code asc
        """
        return order_by_str

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
            CREATE view %s as
                %s
                from
                    account_move_line aml
                join account_move am on
                    am.id = aml.move_id
                left join presupuesto_documento pd on
                    pd.id = am.documento_id
                left join presupuesto_detalle_documento pdd on
                    pdd.documento_id = pd.id
                    and abs(round(pdd.importe, 2)) = abs(round(aml.balance, 2))
                join account_account aa on
                    aa.id = aml.account_id
                left join presupuesto_partida_presupuestal ppp on
                    ppp.id = pdd.posicion_presupuestaria
                where ppp.id>0
                %s
        """ % (self._table, self._select(), self._order_by()))
  
class polizas_presupuestales(models.Model):
    _name = 'polizas_presupuestales'
    _description = "Poliza"
    _rec_name = 'id'
    _inherit = ['mail.thread']

    partidas = fields.Many2many('presupuesto.partida_presupuestal', string='Posición presupuestaria',relation='partidas_polizas_history', required=True,track_visibility='onchange')
    capitulo= fields.Selection([('1000','1000'),('2000','2000'),('3000','3000'),('5000','5000')],string='Capitulo',track_visibility='onchange')
    clase_documento = fields.Many2many('presupuesto.clase_documento', string='Clase documento',relation='clase_documento_history', required=True,track_visibility='onchange')
    fecha_inicio=fields.Date(string='Fecha inicio', default=fields.Datetime.now,track_visibility='onchange')
    fecha_fin=fields.Date(string='Fecha fin', default=fields.Datetime.now,track_visibility='onchange')
    no_poliza = fields.Char(string='Poliza')
    concepto = fields.Char(string='concepto',track_visibility='onchange')
    elaboro = fields.Char(string='elaboro',default='SJGH',track_visibility='onchange')
    reviso = fields.Char(string='reviso',default='MPYM',track_visibility='onchange')
    vobo = fields.Char(string='vobo',default='JSV',track_visibility='onchange')
    autorizo = fields.Char(string='autorizo',default='ACRG',track_visibility='onchange')
    
    
    def _compute_no_poliza(self):
        # clcs = self.env['presupuesto.clc'].search([('id_factura','=',self.id)])
        self.no_poliza = 'CP-'+str(self.id)

    def filter_set(aquarium_creatures, search_string):
        def iterator_func(x):
            for v in x.values():
                if search_string in v:
                    return True
            return False
        return filter(iterator_func, aquarium_creatures)

    
    def pdf_poliza(self):
        ids_pareg=[]
        for par in self.partidas:
            ids_pareg.append(par.id)
        if(len(ids_pareg)>1):
            partidas=tuple(ids_pareg)
        else:
            if(self.partidas):
                partidas='('+str(ids_pareg[0])+')'
        clase_ids=[]
        for clase in self.clase_documento:
            clase_ids.append(clase.id)
        if(len(clase_ids)>1):
            clas_doc=tuple(clase_ids)
        else:
            clas_doc='('+str(clase_ids[0])+')'

        if(self.capitulo):
            capitulo=self.capitulo[:-3]
            sql_lineas = """(select
                            concat(SUBSTRING(code, 1, 3 ), '.0.0000.00') code, cuenta,capitulo sub_cta,
                            0 partida_id,clase_documento,'' "ref",sum(credit) credit,sum(debit) debit
                        from
                            presupuesto_view_polizas_documento
                        where
                            clase_documento in %s
                            and capitulo=%s
                            and fecha_documento between '%s' and '%s'
                        group by 1,2,3,4,5)                 
                        union all
                        (select code,cuenta,capitulo sub_cta,partida_id,
                            clase_documento,ref,credit,debit
                        from
                            presupuesto_view_polizas_documento
                        where
                            clase_documento in %s
                            and capitulo=%s
                            and fecha_documento between '%s' and '%s')
            order by code asc""" % (clas_doc,capitulo,self.fecha_inicio,self.fecha_fin,clas_doc,capitulo,self.fecha_inicio,self.fecha_fin)
        else:
            sql_lineas = """(select
                                 concat(SUBSTRING(code, 1, 3 ), '.0.0000.00') code,
                            cuenta,capitulo sub_cta,0 partida_id,clase_documento,
                            '' "ref",sum(credit) credit,sum(debit) debit
                            from
                                presupuesto_view_polizas_documento
                            where
                                clase_documento in %s
                                and partida_id in %s
                                and fecha_documento between '%s' and '%s'
                            group by 1,2,3,4,5)                 
                            union all
                            (select
                                code,cuenta,capitulo sub_cta,partida_id,
                                clase_documento,ref,credit,debit
                            from
                                presupuesto_view_polizas_documento
                            where
                                clase_documento in %s
                                and partida_id in %s
                                and fecha_documento between '%s' and '%s') 
            order by code asc;""" %(clas_doc,partidas,self.fecha_inicio,self.fecha_fin,clas_doc,partidas,self.fecha_inicio,self.fecha_fin)

        self.env.cr.execute(sql_lineas)
        results = self.env.cr.dictfetchall()
        datas = {}
        suma_cargo = 0
        suma_abono = 0
        lineas = []
        count = 0
        if not(results):
            raise ValidationError('No se encontraron resultados')
        
        df=pd.DataFrame.from_dict(results)
        cts_padre=df[df.code.str.contains('.0.0000.00')].filter(items=['code','ref','cuenta','sub_cta','credit','debit']).to_json(orient="records")
        cts_padre_parsed = json.loads(cts_padre)
        for item in cts_padre_parsed:
            filt=item['code'].split('.')
            ct_hijo=df[df.cuenta.str.contains(filt[0])].filter(items=['code','ref','cuenta','sub_cta','credit','debit']).to_json(orient="records")
            cuenta_nombre = self.env['account.account'].search([('code', '=', str(item['code']))])[0].name
            insert_padre = {
                            'nombre': cuenta_nombre,
                            'cuenta': filt[0],
                            'subcuenta': '',
                            'subsubcuenta': '',
                            'subsubsubcuenta': '',
                            'parcial': '',
                            'cargo': '{0:,.2f}'.format(float(item['debit'])),
                            'abono': '{0:,.2f}'.format(float(item['credit'])),
                            }
            suma_cargo+=item['debit']
            suma_abono+=item['credit']
            lineas.append(insert_padre)
            capitulos = []
            cts_sub_cta_parsed = json.loads(ct_hijo)
            for subc in cts_sub_cta_parsed:
                capitulos.append(subc['sub_cta'])
            for sub_cta in list(set(capitulos)):
                tot_sub_cta=0
                sub_cta_filter=filt[0]+'.'+str(sub_cta)
                sub_cta_nombre = self.env['account.account'].search([('code', '=', str(sub_cta_filter+'.0000.00'))])[0].name
                cts_sub_cta=df[df.code.str.contains(sub_cta_filter)].filter(items=['code','ref','cuenta','sub_cta','credit','debit']).to_json(orient="records")
                cts_sub_cta_parsed = json.loads(cts_sub_cta)
                for it in cts_sub_cta_parsed:
                    if(it['debit']==0):
                        parcial=it['credit']
                    else:
                        parcial=it['debit']
                    tot_sub_cta=tot_sub_cta+parcial
                insert_padre = {
                                'nombre': sub_cta_nombre,
                                'cuenta': '',
                                'subcuenta': sub_cta,
                                'subsubcuenta': '',
                                'subsubsubcuenta': '',
                                'parcial': '',
                                'cargo': '',
                                'abono': '',
                                }
                lineas.append(insert_padre)
                for it_part in cts_sub_cta_parsed:
                    subc = it_part['code'].split('.')
                    subsubcuenta_nombre = self.env['account.account'].search([('code', '=like', subc[0] + '.' + subc[1] + '.' + subc[2] + '%')])[0].name
                    subsubsubcuenta_nombre = self.env['account.account'].search([('code', '=', str(it_part['code']))])[0].name
                    if(it_part['debit']==0):
                        parcial=it_part['credit']
                    else:
                        parcial=it_part['debit']
                    for count in range(1,5):
                        if count == 1:
                            pass
                        if count == 2:
                            pass
                        if count == 3:
                            insert = {
                            'nombre':subsubcuenta_nombre,
                            'cuenta': '',
                            'subcuenta': '',
                            'subsubcuenta': subc[2],
                            'subsubsubcuenta': '',
                            'parcial': '',
                            'cargo': '',
                            'abono': '',
                            }
                            lineas.append(insert)
                        if count == 4:
                            insert = {
                            'nombre': subsubsubcuenta_nombre,
                            'cuenta': '',
                            'subcuenta': '',
                            'subsubcuenta': '',
                            'subsubsubcuenta': subc[3],
                            'parcial': '{0:,.2f}'.format(float(parcial)),
                            'cargo': '',
                            'abono': '',
                            }
                            lineas.append(insert)
                            count += 1

        datas['lineas_cuenta'] = lineas

        datas['suma_abono'] = suma_abono
        datas['suma_cargo'] = suma_cargo

        form={
            'date':'De %s a %s'%(self.fecha_inicio,self.fecha_fin),
            'name':'CP-'+str(self.no_poliza),
            'concepto':self.concepto,
            'elaboro':self.elaboro,
            'reviso':self.reviso,
            'vobo':self.vobo,
            'autorizo':self.autorizo
        }
        datas['form'] = form

        return self.env['report'].get_action([], 'reportes.poliza_presupuestal', data=datas)
        
class viewControlPresuV2(models.Model):
    _name = 'presupuesto.view_cp_v2'
    _auto = False
    _order = "partida_presupuestal asc"
    
    posicion_presupuestaria = fields.Integer(string='Posicion Presupuestaria')
    posicion_presupuestaria_padre = fields.Integer(string='Posicion Presupuestaria')
    partida_presupuestal = fields.Char(string='Partida Presupuestal')
    denominacion = fields.Char(string='Nombre Partida')
    nom_capitulo = fields.Char(string='Capitulo')
    capitulo = fields.Char(string='Capitulo')
    fecha = fields.Date(string='Fecha')
    nom_mes = fields.Char(string='Mes')
    periodo = fields.Selection(catalogos.PERIODO_SELECT)
    ejercicio = fields.Selection(catalogos.EJERCICIO_SELECT)
    aprobado = fields.Float(string='Aprobado')
    remanente = fields.Float(string='Saldo inicial')
    ampliacion = fields.Float(string='Ampliacion')
    reduccion = fields.Float(string='Reduccion')
    modificado = fields.Float(string='Modificado')
    comprometido = fields.Float(string='Comprometido')
    devengado = fields.Float(string='Devengado')
    pagado = fields.Float(string='Pagado')
    ejercido = fields.Float(string='Ejercido')
    disponible = fields.Float(string='Disponible')

    def _select(self):
        select_str = """
            SELECT
                dd.control_presupuesto_id as id,
                dd.posicion_presupuestaria,
                pp.partida_presupuestal,
                pp.denominacion,
                CASE WHEN (pp.capitulo = 1) THEN 1000 
                    WHEN (pp.capitulo = 2) THEN 2000 
                    WHEN (pp.capitulo = 3) THEN 3000
                    WHEN (pp.capitulo = 5) THEN 5000 END nom_capitulo,
                pp.capitulo,
                cast(date_trunc('month',TO_TIMESTAMP(concat(pd.ejercicio, '-', pd.periodo, '-01'),'YYYY-MM-DD-DDD'))as date) fecha,
                to_char(to_timestamp(pd.periodo::text, 'MM'), 'TMMonth') nom_mes,
                pd.periodo,
                pd.ejercicio,
                SUM(CASE WHEN pd.clase_documento = 3 THEN dd.importe ELSE 0 END) aprobado,	
                SUM(CASE WHEN pd.clase_documento = 10 THEN dd.importe ELSE 0 END) remanente,	
                SUM(CASE WHEN (pd.clase_documento = 1) OR (pd.clase_documento = 4) THEN dd.importe ELSE 0 END) ampliacion,	
                SUM(CASE WHEN (pd.clase_documento = 2) OR (pd.clase_documento = 5) THEN dd.importe ELSE 0 END) reduccion,
                SUM(CASE WHEN pd.clase_documento = 3 THEN dd.importe ELSE 0 END) + SUM(CASE WHEN (pd.clase_documento = 1) OR (pd.clase_documento = 4) THEN dd.importe ELSE 0 END) + SUM(CASE WHEN pd.clase_documento = 10 THEN dd.importe ELSE 0 END) -  SUM(CASE WHEN (pd.clase_documento = 2) OR (pd.clase_documento = 5) THEN dd.importe ELSE 0 END) modificado,
                SUM(CASE WHEN pd.clase_documento = 6 THEN dd.importe ELSE 0 END) comprometido,	
                SUM(CASE WHEN pd.clase_documento = 7 THEN dd.importe ELSE 0 END) devengado,	
                SUM(CASE WHEN pd.clase_documento = 8 THEN dd.importe ELSE 0 END) pagado,	
                SUM(CASE WHEN pd.clase_documento = 9 THEN dd.importe ELSE 0 END) ejercido,
                ((SUM(CASE WHEN pd.clase_documento = 3 THEN dd.importe ELSE 0 END) + SUM(CASE WHEN (pd.clase_documento = 1) OR (pd.clase_documento = 4) THEN dd.importe ELSE 0 END) + SUM(CASE WHEN pd.clase_documento = 10 THEN dd.importe ELSE 0 END) ) -  SUM(CASE WHEN (pd.clase_documento = 2) OR (pd.clase_documento = 5) THEN dd.importe ELSE 0 END) ) - SUM(CASE WHEN pd.clase_documento = 7 THEN dd.importe ELSE 0 END) disponible
        """
        return select_str

    def _group_by(self):
        group_by_str = """
            GROUP BY
                dd.control_presupuesto_id,
                dd.posicion_presupuestaria,
                pp.partida_presupuestal,
                pp.capitulo,
                pp.denominacion,
                pd.periodo,
                pd.ejercicio
        """
        return group_by_str

    def _order_by(self):
        order_by_str = """
            ORDER BY
                pp.partida_presupuestal
        """
        return order_by_str

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
            CREATE view %s as
                %s
                FROM presupuesto_detalle_documento dd
                INNER JOIN presupuesto_partida_presupuestal pp ON dd.posicion_presupuestaria = pp.id
                INNER JOIN presupuesto_documento pd ON dd.documento_id = pd.id
                WHERE status='open'
                %s
                %s
        """ % (self._table, self._select(), self._group_by(), self._order_by()))
        
    
    @api.depends(
        'ejercicio',
        'periodo',
        'partida_presupuestal'
    )
    def name_get(self):
        result = []
        for part_pres in self:
            name = '%s/%s/%s' % (
                part_pres.ejercicio,
                part_pres.periodo,
                part_pres.partida_presupuestal
            )
            result.append((part_pres.id, name))
        return result

    detalle_documento_original_ids = fields.One2many(
        'presupuesto.detalle_documento',
        'control_presupuesto_id',
        domain=[('documento_id.clase_documento.tipo_documento','=','ORIGINAL')],
        string='Documento',
    )
    detalle_documento_remanente_ids = fields.One2many(
        'presupuesto.detalle_documento',
        'control_presupuesto_id',
        domain=[('documento_id.clase_documento.tipo_documento','=','REMANENTE'),
                ('documento_id.status', '!=', 'close')],
        string='Documento',
    )

    detalle_documento_comprometido_ids = fields.One2many(
        'presupuesto.detalle_documento',
        'control_presupuesto_id',
        domain=[('documento_id.clase_documento.tipo_documento','=','COMPROMETIDO'),
                ('documento_id.status', '!=', 'close')],
        string='Documento',
    )

    detalle_documento_devengado_ids = fields.One2many(
        'presupuesto.detalle_documento',
        'control_presupuesto_id',
        domain=[('documento_id.clase_documento.tipo_documento','=','DEVENGADO'),
                ('documento_id.status', '!=', 'close')],
        string='Documento',
    )

    detalle_documento_ejercido_ids = fields.One2many(
        'presupuesto.detalle_documento',
        'control_presupuesto_id',
        domain=[('documento_id.clase_documento.tipo_documento', '=', 'EJERCIDO'),
                ('documento_id.status', '!=', 'close')],
        string='Documento'
    )

    detalle_documento_pagado_ids = fields.One2many(
        'presupuesto.detalle_documento',
        'control_presupuesto_id',
        domain=[('documento_id.clase_documento.tipo_documento','=','PAGADO'),
                ('documento_id.status', '!=', 'close')],
        string='Documento',
    )

    detalle_documento_ampliacion_ids = fields.One2many(
        'presupuesto.detalle_documento',
        'control_presupuesto_id',
        domain=['|',('documento_id.clase_documento.tipo_documento','=','AMPLIACION'),
                ('documento_id.clase_documento.tipo_documento', '=', 'RECLASIFICACION'),
                ('documento_id.clase_documento.signo', '=', '+'),
                ('documento_id.status', '!=', 'close')],
        string='Documento',
    )

    detalle_documento_reduccion_ids = fields.One2many(
        'presupuesto.detalle_documento',
        'control_presupuesto_id',
        domain=['|',('documento_id.clase_documento.tipo_documento','=','REDUCCION'),
                ('documento_id.clase_documento.tipo_documento', '=', 'RECLASIFICACION'),
                ('documento_id.clase_documento.signo', '=', '-'),
                ('documento_id.status', '!=', 'close')],
        string='Documento',
    )

    presupuesto_aprobado = fields.Float(
        string='Presupuesto Aprobado',
        compute='_presupuesto_aprobado'
    )

    presupuesto_remanente = fields.Float(
        string='Saldo Inicial - Remanente',
        compute='_presupuesto_remanente'
    )

    presupuesto_modificado = fields.Float(
        string='Presupuesto Modificado',
        compute='_presupuesto_modificado'
    )

    presupuesto_modificado_disponible = fields.Float(
        string='Presupuesto Modificado',
        compute='_presupuesto_modificado_disponible'
    )

    presupuesto_ampliacion = fields.Float(
        string='Presupuesto Ampliacion',
        compute='_presupuesto_ampliacion'
    )

    presupuesto_reduccion = fields.Float(
        string='Presupuesto Reduccion',
        compute='_presupuesto_reduccion'
    )

    presupuesto_devengado = fields.Float(
        string='Presupuesto Devengado',
        compute='_presupuesto_devengado'
    )

    presupuesto_disponible = fields.Float(
        string='Presupuesto Disponible',
        compute='_presupuesto_disponible'
    )

    @api.depends(
        'aprobado',
        'ampliacion',
        'reduccion',
        'remanente',
        'devengado',
        'modificado'
        )

    def _presupuesto_aprobado(self):
        for r in self:
            r.presupuesto_aprobado = r.aprobado

    def _presupuesto_remanente(self):
        for r in self:
            r.presupuesto_remanente = r.remanente

    def _presupuesto_ampliacion(self):
        for r in self:
            r.presupuesto_ampliacion = r.ampliacion

    def _presupuesto_reduccion(self):
        for r in self:
            r.presupuesto_reduccion = r.reduccion * -1

    def _presupuesto_modificado(self):
        for r in self:
            r.presupuesto_modificado = r.aprobado + r.ampliacion + r.remanente - r.reduccion

    def _presupuesto_modificado_disponible(self):
        for r in self:
            r.presupuesto_modificado_disponible = r.aprobado + r.ampliacion + r.remanente - r.reduccion

    def _presupuesto_devengado(self):
        for r in self:
            r.presupuesto_devengado = r.devengado * -1

    def _presupuesto_disponible(self):
        for r in self:
            r.presupuesto_disponible = r.modificado - r.devengado

