# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import api, fields, models, _, tools
from odoo.exceptions import ValidationError,UserError
from num2words import num2words
import xlwt
import json
import time
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import odoo.addons.decimal_precision as dp
from odoo.tools.float_utils import float_compare
import collections




class Compra(models.Model):
    _inherit = 'purchase.order'
    partner_id = fields.Many2one(comodel_name='res.partner', string='Vendor', required=True, change_default=True, track_visibility='always')
    @api.model
    def get_fondo(self):
        return self.env['presupuesto.fondo_economico'].search([('fuente_financiamiento','=','11')])
    @api.model
    def get_centro_g(self):
        return self.env['presupuesto.centro_gestor'].search([('clave','=','21A000')])
    @api.model
    def get_area_funci(self):
        return self.env['presupuesto.area_funcional'].search([('area_funcional','=','020400')])

    area=fields.Selection([('SG', 'SG'), ('RM', 'RM')],strig='Area')
    fondo_economico = fields.Many2one(comodel_name='presupuesto.fondo_economico',string='Fondo',required=True,readonly=1,  default=get_fondo)
    centro_gestor = fields.Many2one(comodel_name='presupuesto.centro_gestor',string='Centro gestor',required=True,readonly=1, default=get_centro_g)
    area_funcional = fields.Many2one(comodel_name='presupuesto.area_funcional',string='Área funcional',required=True, default=get_area_funci)
    tipo_contrato = fields.Many2one(comodel_name='purchase.requisition.type',string='Tipo de contrato')
    justificacion = fields.Text(string='Justificacion y uso solicitado')
    observaciones = fields.Text(string='Otras observaciones')
    amount_tax = fields.Monetary(string='Tax', store=True, readonly=True)
    type_purchase_button = fields.Char(string='Tipo de compra', default='purchase')
    status_account_move = fields.Char(string='M. Presupuestal', default='ORIGINAL')
    line_asientos_contables = fields.One2many('account.move', string='Asientos contables', compute="_compute_asientos")    
    
    def _compute_asientos(self):
        if(self.type_purchase == 'compra' and self.compromiso):
            self.line_asientos_contables = self.env['account.move'].search(['|',('compra_id','=',self.id),('ref','=',self.compromiso.name)])
        else:
            self.line_asientos_contables = self.env['account.move'].search([('compra_id','=',self.id),('state','=','posted')])
        
        

        


    taxes_id = fields.Many2many('account.tax', string='Taxes')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Vendor', change_default=True, track_visibility='always')
    order_line = fields.One2many('purchase.order.line', 'order_id', string='Order Lines', states={'cancel': [('readonly', True)], 'done': [('readonly', True)]}, copy=True)
    fecha_devengado=fields.Date(string='Fecha devengado')
    

    date_order = fields.Datetime('Order Date', required=True,  index=True, copy=False)
    check=fields.Boolean(string='Devengado opciones')
    check_dev_comp=fields.Boolean(string='Devengado y Comprometido')
    totales=fields.Html(compute='compute_totales',string='Totales por partidas')
    sp_totales=fields.Html(compute='compute_sp_totales',string='S.P.')
    requisition_purchase=fields.Many2one(comodel_name='presupuesto.requisicion',string='Requisición')
    solicitud_pago_purchase=fields.Char(string='Solicitud de pago')
    folio=fields.Char(string='Folio')

    type_purchase=fields.Selection([('compra','Compra'),('fondo','Fondo'),('comprobacion','Comprobacion de gasto')],string='Tipo de compra',index=True, default='compra',required=True)
    importe_comprometido=fields.Float(string='Importe')
    date_planned = fields.Datetime(string='Scheduled Date')


    referencia_compra = fields.Many2one(comodel_name='purchase.order',string='Referencia compra')
    remisiones_compra = fields.Many2one(comodel_name='tjacdmx.remisiones',string='Referencia compra')
    compromiso=fields.Many2one(comodel_name='presupuesto.requisicion.compras.compromisos.line',string='Requisición v2')
    #journal_ids = fields.Many2many('account.journal', string='Journals', required=True, default=lambda self: self.env['account.journal'].search([]))
    sp_ids = fields.Many2many('presupuesto.solicitud.pago.line', string='S.P.')



    @api.model
    def create(self, values):
        purchase = super(Compra, self).create(values)
        purchase.write({'state': 'sent'})
        return purchase



    @api.depends('order_line.date_planned')
    def _compute_date_planned(self):
        if(self.type_purchase=='fondo'):
            for order in self:
                min_date = False
                for line in order.order_line:
                    if not min_date or line.date_planned < min_date:
                        min_date = line.date_planned
                if min_date:
                    order.date_planned = min_date
        else:
            for order in self:
                min_date = self.date_order if self.date_order else False
                if min_date:
                    order.date_planned = min_date
        

    
    @api.onchange('asientos_compra')
    def _onchange_empleado(self):
        asiento = self.env['account.move'].search([('id','=',self.asientos_compra.id)],limit=1)
        dif=asiento.amount-self.amount_total
        if(asiento.journal_id.id==70):
            self.update({'check': True })
        else:
            self.update({'check': False })
        self.update({'total_ultimo_ac': dif })

    
    
    @api.onchange('compromiso')
    def _onchange_compromiso(self):
        self.date_order = self.compromiso.fecha

    
    def print_requisition_purchase(self):
        return self.env['report'].get_action([], 'reportes.purchase_requisicion')

    
    def compute_totales(self):
        sql="""
            select 
                pp.partida_presupuestal as partida,
                SUM(l.price_total) as total
            from purchase_order_line l
                inner join product_product p on p.id= l.product_id
                inner join product_template pt on pt.id= p.product_tmpl_id
                inner join presupuesto_partida_presupuestal pp on pp.id= pt.posicion_presupuestaria
            where order_id=%s
            group by 1"""
        self.env.cr.execute(sql % (self.id))
        totales_compra = self.env.cr.dictfetchall()
        ids=[] 
        for i in totales_compra:
            partidas = {'partida': i['partida'],'total': i['total']}
            ids.append(partidas)
        html_items=""
        for items in ids:
            partida=items['partida']
            total=str(items['total'])
            html_items2="<tr><td><p>"+partida+"</p></td> <td><p>"+total+"</p></td> </tr>"
            html_items+=html_items2.encode('ascii', 'ignore')
        html="""<table class="table">
                    <tr><td><p><strong>Partida</strong></p></td><td><p><strong>Total</strong></p></td></tr>
                    %s
            </table>""" % (html_items)
        self.totales=html
    
    
    def compute_sp_totales(self):
        
        sps = self.env['presupuesto.solicitud.pago'].search([('compras','=',self.id)])

        html_items=""
        for sp in sps:
             
            html_items2="<tr><td><p>"+sp.fecha+"</p></td> <td><a target=\"_blank\" href=\"/web#id="+str(sp.id)+"&view_type=form&model=presupuesto.solicitud.pago&menu_id=253&action=541\" >"+sp.name+"</a></td> <td><p>"+'${0:,.2f}'.format(sp.importe)+"</p></td> </tr>"
            html_items+=html_items2.encode('ascii', 'ignore')
        html="""<table class="table">
                    <tr><td><p><strong>Fecha</strong></p></td><td><p><strong>SP</strong></p></td><td><p><strong>Importe</strong></p></td></tr>
                    %s
            </table>""" % (html_items)
        self.sp_totales=html

    
    def action_crear_sp(self):
        compra = self.env['purchase.order'].search([('id','=',self.id)])
        listids=[]
        listids.append(compra.id)
 
        facturas = self.env['account.invoice'].search([('origin','=',self.name)])

        lineas_sp = []

        for fac in facturas:
            lineas_sp.append({
                            'proveedor': compra.partner_id.id,
                            'fecha': fac.date_due,
                            'importe': fac.amount_total,
                            'partida': compra.compromiso.requisicion_compra.partida.id,
                            'descripcion': '',
                            'factura': fac.reference_provedor,
                            'adjudicacion': compra.tipo_contrato.name,
                            'compromiso': compra.compromiso.id,
                            })

        return {
                    'name': _("Crear compra"),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'presupuesto.solicitud.pago',
                    'target': 'new',
                    'type': 'ir.actions.act_window',
                    'context': {
                        'default_state': 'draft',
                        'default_compras': compra.id,
                        'default_proveedor': compra.partner_id.id,
                        'default_lineas_solicitud_pago':lineas_sp
                        # 'default_type_purchacee':'compra',
                        # 'default_compromiso':self.compromiso.id,
                        # 'default_date_order':self.compromiso.fecha,
                        # 'default_fecha_devengado': self.fecha,
                        # 'default_sp_ids': listids ,
                        # 'default_partner_id': self.proveedor.id
                        }
                } 
    

    
    def status_momento_p(self):
        action = self.env.ref('account.action_move_journal_line')
        result = action.read()[0]
        result.pop('id', None)
        result['context'] = {}
        asientos_ids = self.id
        if asientos_ids > 1:
            result['domain'] = "[('compra_id','=', %s)]" % (self.id)
        elif asientos_ids == 1:
            raise ValidationError("La compra se encuentra '%s' " % (self.status_account_move))
        return result
    

    
    def action_view_invoice(self):
        result = super(Compra, self).action_view_invoice()
        result['context'].update({
            'default_fondo_economico': self.fondo_economico.id,
            'default_centro_gestor': self.centro_gestor.id,
            'default_area_funcional': self.area_funcional.id
        })
        return result

    
    def print_quotation(self):
        result = super(Compra, self).print_quotation()
        control_presupuesto = self.env['presupuesto.control_presupuesto']
        version = self.env['presupuesto.version'].search([], limit=1)
        fecha_origen = datetime.strptime(self.date_order, '%Y-%m-%d %H:%M:%S') if self.date_order else datetime.today()
        
        if(self.compromiso 
                and self.type_purchase == 'compra'):
                fecha_origen = datetime.strptime(self.compromiso.fecha, '%Y-%m-%d')

        for idx, item in enumerate(self.order_line):
            item.posicion = idx + 1
            co = self.env['presupuesto.cuenta_orden'].search([('posicion_presupuestaria', '=', item.product_id.posicion_presupuestaria.id)])
            sql_md="""
                    SELECT (
                        (SUM(CASE WHEN pd.clase_documento = 3 THEN importe ELSE 0 END) + 
                        SUM(CASE WHEN (pd.clase_documento = 1) OR (pd.clase_documento = 4) THEN importe ELSE 0 END) +
                        SUM(CASE WHEN pd.clase_documento = 10 THEN importe ELSE 0 END) ) -
                        SUM(CASE WHEN (pd.clase_documento = 2) OR (pd.clase_documento = 5) THEN importe ELSE 0 END) ) - 
                        SUM(CASE WHEN pd.clase_documento = 6 THEN importe ELSE 0 END) disponible
                    FROM presupuesto_detalle_documento dd
                    INNER JOIN presupuesto_partida_presupuestal pp ON dd.posicion_presupuestaria = pp.id
                    INNER JOIN presupuesto_documento pd ON dd.documento_id = pd.id
                    WHERE posicion_presupuestaria=%s and periodo=%s
                    GROUP BY dd.posicion_presupuestaria,pp.partida_presupuestal,pd.periodo
                    """
            self.env.cr.execute(sql_md % (item.product_id.posicion_presupuestaria.id, fecha_origen.month))
            importe_disponible_origen = self.env.cr.fetchone()

            if(not self.compromiso 
                and self.type_purchase != 'compra'):

                if(importe_disponible_origen):
                    impor_validate=importe_disponible_origen[0]
                    if (impor_validate>0):
                        impor_conv=importe_disponible_origen[0]
                    else:
                        impor_conv=0
                    #raise ValidationError("%s" % (item.price_subtotal))
                    if(item.price_subtotal>impor_conv):
                        raise ValidationError("El presupuesto no es suficiente para esta compra, el saldo es: %s)" % (impor_conv))

                else:
                    raise ValidationError("El presupuesto no es suficiente para esta compra.")

        return result
    

    
    @api.onchange('order_line')
    def _onchange_uom_purchase(self):
        if(self.order_line):
            linea_referencia=self.order_line[0]
            if(linea_referencia.product_uom.name == 'Servicio'):
                self.update({'type_purchase_button': 'service'})
            else:
                self.update({'type_purchase_button': 'purchase'})
    
    
    @api.onchange('sp_ids')
    def _onchange_sp_ids(self):
        if(len(self.sp_ids) > 0):
            print(self.sp_ids[0])
            

    
    def importe_con_letra(self, cantidad):
        cantidad = '{0:.2f}'.format(float(cantidad))
        importe = cantidad.split('.')[0]
        centavos = cantidad.split('.')[1]
        importe = (num2words(importe, lang='es').split(' punto ')[0]).upper()
        moneda = ' pesos '.upper()
        leyenda = '/100 m.n.'.upper()
        return importe + moneda + centavos + leyenda
    
    
    @api.onchange('type_purchase')
    def _onchange_type_purchase(self):  
        self.requisition_purchase = ''
        self.importe_comprometido = ''
        self.referencia_compra = ''
        self.folio = ''

    
    @api.onchange('requisition_purchase')
    def _onchange_requisition_purchase(self):  
        self.importe_comprometido = ''
        self.referencia_compra = ''
    
    
    @api.onchange('importe_comprometido')
    def _onchange_importe_comprometido(self):  
        self.referencia_compra = ''   
        
    
    
    def button_open_devengado_window(self):
        user_session = self.env['res.users'].browse(self.env.uid)
        permisos = self.env['presupuesto.permisos.presupuestales'].search([('usuario_id','=',user_session.id),('devengado','=','open')])
        ctrl_periodo = self.env['control.periodos.wizard']
        if(permisos):
            return {
                'name': _("Recibir pedido"),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'momentos_presupuestales.wizard',
                'target': 'new',
                'type': 'ir.actions.act_window',
                'context': {'compra': self.id,'momento': str('devengado'),'provision': 'False','tipo_contrato':self.tipo_contrato.id}
            } 
        else:
            raise ValidationError("No cuenta con permisos para realizar esta operación, comuníquese con el administrador para revisar las operaciones autorizadas.")

    
    def do_new_transfer_dev(self):
        user_session = self.env['res.users'].browse(self.env.uid)
        permisos = self.env['presupuesto.permisos.presupuestales'].search([('usuario_id','=',user_session.id),('devengado','=','open')])
        ctrl_periodo = self.env['control.periodos.wizard']    
            
        if(not ctrl_periodo.get_is_cerrado(self.fecha_devengado)
            and permisos):

            documentos = []
            obj_documento = self.env['presupuesto.documento']
            version = self.env['presupuesto.version'].search([], limit=1)
            cls_doc = self.env['presupuesto.clase_documento'].search([('tipo_documento','=','DEVENGADO')], limit=1)
            fecha_origen = datetime.strptime(self.date_order, '%Y-%m-%d %H:%M:%S') if self.date_order else datetime.today()

            if(self.compromiso 
                and self.type_purchase == 'compra'):
                fecha_origen = datetime.strptime(self.compromiso.fecha, '%Y-%m-%d')

            fecha = datetime.strptime(self.fecha_devengado, '%Y-%m-%d') if self.fecha_devengado else datetime.today()
            purchase_order = self.env['purchase.order'].search([('name', '=', self.name)])
            items = self.env['purchase.order.line'].search([('order_id', '=', purchase_order.id),('check_items', '=', True)])
            items_deven = self.env['purchase.order.line'].search([('order_id', '=', purchase_order.id),('state_devengado', '=', 'devengado')])
            items_validate = self.env['purchase.order.line'].search([('order_id', '=', purchase_order.id)])
            items_deve_con = self.env['account.move'].search([('compra_id', '=', purchase_order.id), ('journal_id','=',70)])
            rowo=len(items)
            rowv=len(items_validate)
            rowas=len(items_deve_con)
            rowdeven=len(items_deven)
            if(rowo==rowdeven):
                put_states_purchase="UPDATE purchase_order SET status_account_move='DEVENGADO' WHERE id=%s" % (self.id)
                self.env.cr.execute(put_states_purchase)
            if(rowo==rowv or rowas>=rowv):
                put_states_purchase="UPDATE purchase_order SET status_account_move='DEVENGADO' WHERE id=%s" % (self.id)
                self.env.cr.execute(put_states_purchase)
                # self.write({'status_account_move': "DEVENGADO"})
            if (rowas>=rowv):
                put_states_purchase="UPDATE purchase_order SET status_account_move='DEVENGADO' WHERE id=%s" % (self.id)
                self.env.cr.execute(put_states_purchase)
            else:
                if(rowo<=0):
                    raise ValidationError("No se han seleccionado productos o servicios para recibir.")
                elif(rowdeven>=rowv):
                    raise ValidationError("No hay registros para devengar.")
                else:
                    #raise ValidationError("marcados:%s  items:%s  asientos:%s" % (len(items), len(items_validate), len(items_deve_con) ))
                    for item in items:
                        put_states="UPDATE purchase_order_line SET state_devengado='devengado',check_items='False' WHERE id=%s" % (item.id)
                        self.env.cr.execute(put_states)
                        posicion_presupuestaria = item.product_id.product_tmpl_id.posicion_presupuestaria
                        documento={'clase_documento': cls_doc.id,'version': version.id,
                                    'ejercicio': fecha.year,'periodo': fecha.month,'periodo_origen': fecha_origen.month,
                                    'fecha_contabilizacion': fecha.strftime("%Y-%m-%d"),'fecha_documento': fecha.strftime("%Y-%m-%d"),
                                    'detalle_documento_ids': [],'compra_id': purchase_order.id }
                        detalle_doc = [0, False,{
                            'centro_gestor': purchase_order.centro_gestor.id,'area_funcional': purchase_order.area_funcional.id,
                            'fondo_economico': purchase_order.fondo_economico.id,'posicion_presupuestaria': posicion_presupuestaria.id,
                            'importe': item.price_total,'momento_contable': 'DEVENGADO','periodo_origen': fecha_origen.month }]
                        doc_idx = _check_exist_doc(documentos, documento)
                        if doc_idx > -1:
                            documentos[doc_idx]['detalle_documento_ids'].append(detalle_doc)
                        else:
                            documento['detalle_documento_ids'].append(detalle_doc)
                            documentos.append(documento)
                    for doc in documentos:
                        obj_documento.create(doc)
                        asientos=rowas+1
                        if(asientos==rowv):
                            self.write({'status_account_move': "DEVENGADO"})
        else:
            raise ValidationError("No cuenta con permisos para realizar esta operación, comuníquese con el administrador para revisar las operaciones autorizadas.")


    
    def button_confirm(self):
        result = super(Compra, self).button_confirm()
        user_session = self.env['res.users'].browse(self.env.uid)
        permisos = self.env['presupuesto.permisos.presupuestales'].search([('usuario_id','=',user_session.id),('comprometido','=','open')])
        ctrl_periodo = self.env['control.periodos.wizard']
        
        if(not ctrl_periodo.get_is_cerrado(self.date_order)
            and permisos):
            obj_documento = self.env['presupuesto.documento']
            fecha_orden = datetime.strptime(self.date_order, '%Y-%m-%d %H:%M:%S')
            ejercicio = fecha_orden.year
            periodo = fecha_orden.month
            version = self.env['presupuesto.version'].search([], limit=1)
            cls_doc = self.env['presupuesto.clase_documento'].search([('tipo_documento','=','COMPROMETIDO')], limit=1)
            self.write({'status_account_move': "COMPROMETIDO"})
            sale_search = self.env['purchase.order'].search([('name','=',self.origin)], limit=1)
            tjacdmx_update_status_mc = "UPDATE purchase_order SET status_account_move='COMPROMETIDO' WHERE id=%s" % (self.id)
            self.env.cr.execute(tjacdmx_update_status_mc)
            compras = []
            if(self.type_purchase=='compra'):
                posicion_presupuestaria = self.compromiso.requisicion_compra.partida.id
                compra = [0, False,
                    {
                        'centro_gestor': self.centro_gestor.id,
                        'area_funcional': self.area_funcional.id,
                        'fondo_economico': self.fondo_economico.id,
                        'posicion_presupuestaria': posicion_presupuestaria,
                        'importe': self.importe_comprometido,
                        'momento_contable': 'ORIGINAL'
                    }]
                compras.append(compra)
                #raise ValidationError("Debug: %s" % (compras))
            else:
                for item in self.order_line:
                    posicion_presupuestaria = item.product_id.product_tmpl_id.posicion_presupuestaria
                    compra = [0, False,
                        {
                            'centro_gestor': self.centro_gestor.id,
                            'area_funcional': self.area_funcional.id,
                            'fondo_economico': self.fondo_economico.id,
                            'posicion_presupuestaria': posicion_presupuestaria.id,
                            'importe': item.price_total,
                            'momento_contable': 'ORIGINAL'
                        }
                    ]
                    compras.append(compra)

            # Si, el compromiso de la compra viene referenciado no realizar asiento de compromido
            if(self.type_purchase == 'compra' and self.compromiso):
                return result
            

            documento = obj_documento.create({
                'clase_documento': cls_doc.id,
                'version': version.id,
                'ejercicio': ejercicio,
                'periodo': periodo,
                'periodo_origen': periodo,
                'fecha_contabilizacion': self.date_order,
                'fecha_documento': self.date_order,
                'detalle_documento_ids': compras,
                'compra_id': self.id
            })
        else:
            raise ValidationError("No cuenta con permisos para realizar esta operación, comuníquese con el administrador para revisar las operaciones autorizadas.")
        return result

    
    def save_ajust(self):
        documentos = []
        obj_documento = self.env['presupuesto.documento']
        cls_doc = self.env['presupuesto.clase_documento'].search([('tipo_documento','=','REMANENTE')], limit=1)
        fecha = datetime.strptime(self.fecha_ajuste, '%Y-%m-%d') if self.fecha_ajuste else datetime.today()
        fecha_origen = datetime.strptime(self.date_order , '%Y-%m-%d %H:%M:%S') if self.date_order else datetime.today()

        if(self.compromiso 
                and self.type_purchase == 'compra'):
                fecha_origen = datetime.strptime(self.compromiso.fecha, '%Y-%m-%d')

        documento = self.env['presupuesto.documento'].search([('id','=',self.asientos_compra.documento_id.id)],limit=1)
        # if (float(self.total_ultimo_ac) > 0.0):
        #     importe_fin = float('-'+self.total_ultimo_ac)
        # else:
        #     importe_fin=abs(float(self.total_ultimo_ac))
        #raise ValidationError("Debug: %s" % (fecha.year))
        control_destino = self.env['presupuesto.control_presupuesto'].search([
            ('version', '=', documento.version.id),
            ('ejercicio', '=', fecha.year),
            ('periodo', '=', fecha.month),
            ('posicion_presupuestaria', '=', documento.detalle_documento_ids[0].posicion_presupuestaria.id)])
        documentos_originales = []
        detalle_doc = [0, False,
            {
            'centro_gestor': documento.detalle_documento_ids[0].centro_gestor.id,
            'area_funcional': documento.detalle_documento_ids[0].area_funcional.id,
            'fondo_economico': documento.detalle_documento_ids[0].fondo_economico.id,
            'posicion_presupuestaria': documento.detalle_documento_ids[0].posicion_presupuestaria.id,
            'importe': float(self.total_ultimo_ac),
            'importe_val':float(self.total_ultimo_ac),
            'control_presupuesto_id': control_destino.id
            }]
        documentos_originales.append(detalle_doc)
        documento_create = obj_documento.create({
            'clase_documento': documento.clase_documento.id,
            'clase_documento_ajuste': cls_doc.id,
            'version': documento.version.id,
            'ejercicio': fecha.year,
            'periodo': fecha.month,
            'periodo_origen': fecha_origen.month,
            'fecha_contabilizacion': fecha.strftime("%Y-%m-%d"),
            'fecha_documento': fecha.strftime("%Y-%m-%d"),
            'detalle_documento_ids': documentos_originales,
            'compra_id': self.id,
            'tipo':  documento.clase_documento.tipo_documento,
            'check_dev_comp': self.check_dev_comp,
        },tipo='ajuste_presupuestal')

        self.write({'total_ultimo_ac': ""})
        self.write({'asientos_compra': ""})
        self.write({'fecha_ajuste': ""})
        self.write({'check': False})
            


    
    def button_cancel_purchase(self):
        user_session = self.env['res.users'].browse(self.env.uid)
        permisos = self.env['presupuesto.permisos.presupuestales'].search([('usuario_id','=',user_session.id),('cancelar_compra','=','open')])
        ctrl_periodo = self.env['control.periodos.wizard']

        if(not ctrl_periodo.get_is_cerrado(self.date_order)):
            if(permisos):
                
                if(self.type_purchase == 'compra' and self.compromiso):
                    stock=self.env['stock.picking'].search([('origin', '=', self.name)],limit=1)
                    stick_ids= stock.id if stock.id else 0

                    query5 = "DELETE FROM stock_pack_operation WHERE picking_id=%s" % (stick_ids)
                    query6 = "DELETE FROM stock_move WHERE picking_id=%s" % (stick_ids)
                    query7 = "DELETE FROM stock_picking WHERE id=%s" % (stick_ids)

                    self.env.cr.execute(query5)
                    self.env.cr.execute(query6)
                    self.env.cr.execute(query7)
                    put_state_line_purchase= "UPDATE purchase_order SET state='sent', status_account_move='ORIGINAL' WHERE id=%s" % (self.id)
                    self.env.cr.execute(put_state_line_purchase) 
                else:
                    return {
                        'name': _("Cancelar documento Comprometido"),
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'cancel_budget.wizard',
                        'target': 'new',
                        'type': 'ir.actions.act_window',
                        'context': {'tipo': 'COPC','compra_id':self.id}
                    } 
            else:
                raise ValidationError("No cuenta con permisos para realizar esta operación, comuníquese con el administrador para revisar las operaciones autorizadas.")
        
            

    # 
    # def button_cancel_purchase_d(self):
    #     result = super(Compra, self).button_confirm()
    #     user_session = self.env['res.users'].browse(self.env.uid)
    #     permisos = self.env['presupuesto.permisos.presupuestales'].search([('usuario_id','=',user_session.id),('cancelar_compra','=','open')])
    #     if(permisos):
    #         documento=self.env['presupuesto.documento'].search([('compra_id', '=', self.id)],limit=1)
    #         asiento_contable=self.env['account.move'].search([('documento_id', '=', documento.id)],limit=1)
    #         stock=self.env['stock.picking'].search([('origin', '=', self.name)],limit=1)
    #         documento_id= documento.id if documento.id else 0
    #         asiento_contable_id= asiento_contable.id if asiento_contable.id else 0
    #         stick_ids= stock.id if stock.id else 0
    #         if(self.type_purchase=='compra'):
    #             posicion_presupuestaria = self.requisition_purchase.partida
    #             cp = self.env['presupuesto.control_presupuesto'].search([
    #             ('version', '=', documento.version.id),
    #             ('ejercicio', '=', documento.ejercicio),
    #             ('periodo', '=', documento.periodo),
    #             ('posicion_presupuestaria', '=', posicion_presupuestaria.id)])
    #             cp.write({ 'egreso_comprometido': cp.egreso_comprometido - self.importe_comprometido })
    #         else:
    #             for item in self.order_line:
    #                 posicion_presupuestaria = item.product_id.product_tmpl_id.posicion_presupuestaria
    #                 cp = self.env['presupuesto.control_presupuesto'].search([
    #                 ('version', '=', documento.version.id),
    #                 ('ejercicio', '=', documento.ejercicio),
    #                 ('periodo', '=', documento.periodo),
    #                 ('posicion_presupuestaria', '=', posicion_presupuestaria.id)])
    #                 #raise ValidationError("Debug: %s" % (item.price_subtotal))
    #                 cp.write({ 'egreso_comprometido': cp.egreso_comprometido - item.price_subtotal })
                
    #         query1 = "DELETE FROM presupuesto_detalle_documento WHERE documento_id=%s" % (documento_id)
    #         query2 = "DELETE FROM presupuesto_documento WHERE id=%s" % (documento_id)
    #         query3 = "DELETE FROM account_move_line WHERE move_id=%s" % (asiento_contable_id)
    #         query4 = "DELETE FROM account_move WHERE id=%s" % (asiento_contable_id)
    #         query5 = "DELETE FROM stock_pack_operation WHERE picking_id=%s" % (stick_ids)
    #         query6 = "DELETE FROM stock_move WHERE picking_id=%s" % (stick_ids)
    #         query7 = "DELETE FROM stock_picking WHERE id=%s" % (stick_ids)
    #         self.env.cr.execute(query1)
    #         self.env.cr.execute(query2)
    #         self.env.cr.execute(query3)
    #         self.env.cr.execute(query4)
    #         self.env.cr.execute(query5)
    #         self.env.cr.execute(query6)
    #         self.env.cr.execute(query7)
    #         self.write({'state': 'draft'})
    #         self.write({'status_account_move': 'ORIGINAL'})
            
    #     else:
    #         raise ValidationError("No cuenta con permisos para realizar esta operación, comuníquese con el administrador para revisar las operaciones autorizadas.")
    #     return result

    
    def button_cancel_devengado(self):
        user_session = self.env['res.users'].browse(self.env.uid)
        permisos = self.env['presupuesto.permisos.presupuestales'].search([('usuario_id','=',user_session.id),('cancelar_devengado','=','open')])
        
        if(permisos):
            return {
                'name': _("Cancelar documento Devengado"),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'cancel_budget.wizard',
                'target': 'new',
                'type': 'ir.actions.act_window',
                'context': {'tipo': 'COPD','compra_id':self.id}
            } 
        else:
            raise ValidationError("No cuenta con permisos para realizar esta operación, comuníquese con el administrador para revisar las operaciones autorizadas.")


    # 
    # def button_cancel_devengado_d(self):
    #     user_session = self.env['res.users'].browse(self.env.uid)
    #     permisos = self.env['presupuesto.permisos.presupuestales'].search([('usuario_id','=',user_session.id),('cancelar_devengado','=','open')])
    #     if(permisos):
    #         documento=self.env['presupuesto.documento'].search([('compra_id', '=', self.id)],limit=1)
    #         asiento_contable=self.env['account.move'].search([('documento_id', '=', documento.id)],limit=1)
    #         stock=self.env['stock.picking'].search([('origin', '=', self.name)],limit=1)
    #         documento_id= documento.id if documento.id else 0
    #         asiento_contable_id= asiento_contable.id if asiento_contable.id else 0
    #         stick_ids= stock.id if stock.id else 0
    #         for item in self.order_line:
    #             posicion_presupuestaria = item.product_id.product_tmpl_id.posicion_presupuestaria
    #             cp = self.env['presupuesto.control_presupuesto'].search([
    #             ('version', '=', documento.version.id),
    #             ('ejercicio', '=', documento.ejercicio),
    #             ('periodo', '=', documento.periodo),
    #             ('posicion_presupuestaria', '=', posicion_presupuestaria.id)])
    #             total_dev=cp.egreso_devengado - item.price_subtotal
    #             total_com=cp.egreso_comprometido + item.price_subtotal
    #             # cp.write({ 'egreso_devengado': cp.egreso_devengado - item.price_subtotal })
    #             # cp.write({ 'egreso_comprometido': cp.egreso_comprometido + item.price_subtotal })
    #             put_state_line= "UPDATE presupuesto_control_presupuesto SET egreso_comprometido='%s', egreso_devengado='%s' WHERE id=%s" % (total_com,total_dev,cp.id)
    #             self.env.cr.execute(put_state_line)
    #             put_state_line= "UPDATE purchase_order_line SET state_devengado='comprometido', check_items='True' WHERE id=%s" % (item.id)
    #             self.env.cr.execute(put_state_line)

    #         query1 = "DELETE FROM presupuesto_detalle_documento WHERE documento_id=%s" % (documento_id)
    #         query2 = "DELETE FROM presupuesto_documento WHERE id=%s" % (documento_id)
    #         query3 = "DELETE FROM account_move_line WHERE move_id=%s" % (asiento_contable_id)
    #         query4 = "DELETE FROM account_move WHERE id=%s" % (asiento_contable_id)
    #         query5 = "DELETE FROM stock_pack_operation WHERE picking_id=%s" % (stick_ids)
    #         query6 = "DELETE FROM stock_move WHERE picking_id=%s" % (stick_ids)
    #         query7 = "DELETE FROM stock_picking WHERE id=%s" % (stick_ids)
    #         self.env.cr.execute(query1)
    #         self.env.cr.execute(query2)
    #         self.env.cr.execute(query3)
    #         self.env.cr.execute(query4)
    #         self.env.cr.execute(query5)
    #         self.env.cr.execute(query6)
    #         self.env.cr.execute(query7)
    #         self.write({'state': 'purchase'})
    #         self.write({'status_account_move': 'COMPROMETIDO'})
    #     else:
    #         raise ValidationError("No cuenta con permisos para realizar esta operación, comuníquese con el administrador para revisar las operaciones autorizadas.")

    
    def button_wizard_cancel(self):
        user_session = self.env['res.users'].browse(self.env.uid)
        permisos = self.env['presupuesto.permisos.presupuestales'].search([('usuario_id','=',user_session.id),('registro_cancelaciones','=','open')])
        if(permisos):
            return {
                'name': _("Cancelación o Ajuste"),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'cancelacion_ajuste.wizard',
                'target': 'new',
                'type': 'ir.actions.act_window',
                'context': {'compra_id':self.id,'tipo_compra':str(self.type_purchase), 'documentos_ids': self.compromiso.documento.id }
            } 
        else:
            raise ValidationError("No cuenta con permisos para realizar esta operación, comuníquese con el administrador para revisar las operaciones autorizadas.")



class CompraLine(models.Model):
    _inherit = 'purchase.order.line'

    partida_producto = fields.Char(compute='_compute_partida', string='Partida')
    check_items=fields.Boolean(string='Omitir registro',default=True)
    state_devengado=fields.Selection([('comprometido','Comprometido'),('devengado','Devengado')],string='Omitir registro',default='comprometido')
    date_planned = fields.Datetime(string='Scheduled Date')
    price_standar = fields.Float(string='Unit Price', required=False,  digits=dp.get_precision('Product Price'))
    price_unit = fields.Float(string='Unit Price', required=True, digits=dp.get_precision('Product Price'))

    product_qty = fields.Float(string='Quantity', digits=dp.get_precision('Product Unit of Measure'), required=True)
    date_planned = fields.Datetime(string='Scheduled Date', required=True, index=True)
    taxes_id = fields.Many2many('account.tax', string='Taxes', domain=['|', ('active', '=', False), ('active', '=', True)])
    product_uom = fields.Many2one(comodel_name='product.uom', string='Product Unit of Measure', required=True)
    product_id = fields.Many2one(comodel_name='product.product', string='Product', domain=[('purchase_ok', '=', True)], change_default=True, required=True)
    # move_ids = fields.One2many('stock.move', 'purchase_line_id', string='Reservation', readonly=True, ondelete='set null', copy=False)
    company_id = fields.Many2one(comodel_name='res.company', related='order_id.company_id', string='Company', store=True, readonly=True)

    
    def _compute_partida(self):
        self.partida_producto=self.product_id.posicion_presupuestaria.partida_presupuestal

    @api.onchange('price_standar')
    def _onchange_price_standar(self):
        self.price_unit = self.price_standar *1.16
 


class RecibirProductos(models.Model):
    _inherit = 'stock.picking'


    totales=fields.Html(compute='compute_desglose',string='Entradas')
    status_compra = fields.Char(compute='_compute_status_compra', string = 'M. Presupuestal')

    
    def _compute_status_compra(self):
        compra = self.env['purchase.order'].search([('name','=',self.origin)])
        self.status_compra =  compra.status_account_move

    
    def do_new_transfer(self):
        if(self.env['tjacdmx.cierre.inventario'].get_is_periodo_cerrado(
            datetime.strptime(self.min_date, '%Y-%m-%d %H:%M:%S').month,
            datetime.strptime(self.min_date, '%Y-%m-%d %H:%M:%S').year) == False):

            self.move_lines = self.move_lines.sorted(key=lambda l: l.date_expected, reverse=True)


            for pick in self:
                if pick.state == 'done':
                    raise UserError(_('The pick is already validated'))
                pack_operations_delete = self.env['stock.pack.operation']
                if not pick.move_lines and not pick.pack_operation_ids:
                    raise UserError(_('Please create some Initial Demand or Mark as Todo and create some Operations. '))
                # In draft or with no pack operations edited yet, ask if we can just do everything
                if pick.state == 'draft' or all([x.qty_done == 0.0 for x in pick.pack_operation_ids]):
                    # If no lots when needed, raise error
                    picking_type = pick.picking_type_id
                    if (picking_type.use_create_lots or picking_type.use_existing_lots):
                        for pack in pick.pack_operation_ids:
                            if pack.product_id and pack.product_id.tracking != 'none':
                                raise UserError(_('Some products require lots/serial numbers, so you need to specify those first!'))
                    view = self.env.ref('stock.view_immediate_transfer')
                    wiz = self.env['stock.immediate.transfer'].create({'pick_id': pick.id})
                    # TDE FIXME: a return in a loop, what a good idea. Really.
                    return {
                        'name': _('Immediate Transfer?'),
                        'type': 'ir.actions.act_window',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'stock.immediate.transfer',
                        'views': [(view.id, 'form')],
                        'view_id': view.id,
                        'target': 'new',
                        'res_id': wiz.id,
                        'context': self.env.context,
                    }

                # Check backorder should check for other barcodes
                if pick.check_backorder():
                    view = self.env.ref('stock.view_backorder_confirmation')
                    wiz = self.env['stock.backorder.confirmation'].create({'pick_id': pick.id})
                    # TDE FIXME: same reamrk as above actually
                    return {
                        'name': _('Create Backorder?'),
                        'type': 'ir.actions.act_window',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'stock.backorder.confirmation',
                        'views': [(view.id, 'form')],
                        'view_id': view.id,
                        'target': 'new',
                        'res_id': wiz.id,
                        'context': self.env.context,
                    }
                for operation in pick.pack_operation_ids:
                    if operation.qty_done < 0:
                        raise UserError(_('No negative quantities allowed'))
                    if operation.qty_done > 0:
                        operation.write({'product_qty': operation.qty_done})
                    else:
                        pack_operations_delete |= operation
                if pack_operations_delete:
                    pack_operations_delete.unlink()
            self.do_transfer()
            return
        else:
            return False


    
    def do_transfer(self):
        """ If no pack operation, we do simple action_done of the picking.
        Otherwise, do the pack operations. """
        # TDE CLEAN ME: reclean me, please
        self._create_lots_for_picking()

        no_pack_op_pickings = self.filtered(lambda picking: not picking.pack_operation_ids)
        no_pack_op_pickings.action_done()
        other_pickings = self - no_pack_op_pickings
        for picking in other_pickings:
            need_rereserve, all_op_processed = picking.picking_recompute_remaining_quantities()
            todo_moves = self.env['stock.move']
            toassign_moves = self.env['stock.move']

            # create extra moves in the picking (unexpected product moves coming from pack operations)
            if not all_op_processed:
                todo_moves |= picking._create_extra_moves()

            if need_rereserve or not all_op_processed:
                moves_reassign = any(x.origin_returned_move_id or x.move_orig_ids for x in picking.move_lines if x.state not in ['done', 'cancel'])
                if moves_reassign and picking.location_id.usage not in ("supplier", "production", "inventory"):
                    # unnecessary to assign other quants than those involved with pack operations as they will be unreserved anyways.
                    picking.with_context(reserve_only_ops=True, no_state_change=True).rereserve_quants(move_ids=picking.move_lines.ids)
                picking.do_recompute_remaining_quantities()

            # split move lines if needed
            for move in picking.move_lines:
                rounding = move.product_id.uom_id.rounding
                remaining_qty = move.remaining_qty
                if move.state in ('done', 'cancel'):
                    # ignore stock moves cancelled or already done
                    continue
                elif move.state == 'draft':
                    toassign_moves |= move
                if float_compare(remaining_qty, 0,  precision_rounding=rounding) == 0:
                    if move.state in ('draft', 'assigned', 'confirmed'):
                        todo_moves |= move
                elif float_compare(remaining_qty, 0, precision_rounding=rounding) > 0 and float_compare(remaining_qty, move.product_qty, precision_rounding=rounding) < 0:
                    # TDE FIXME: shoudl probably return a move - check for no track key, by the way
                    new_move_id = move.split(remaining_qty)
                    new_move = self.env['stock.move'].with_context(mail_notrack=True).browse(new_move_id)
                    todo_moves |= move
                    # Assign move as it was assigned before
                    toassign_moves |= new_move

            # TDE FIXME: do_only_split does not seem used anymore
            if todo_moves and not self.env.context.get('do_only_split'):
                todo_moves.action_done()
            elif self.env.context.get('do_only_split'):
                picking = picking.with_context(split=todo_moves.ids)

            picking._create_backorder()

        self.update_fecha_entrada(self.name, self.min_date[:10])
        return True

    
    def _create_backorder(self, backorder_moves=[]):
        """ Move all non-done lines into a new backorder picking. If the key 'do_only_split' is given in the context, then move all lines not in context.get('split', []) instead of all non-done lines.
        """
        # TDE note: o2o conversion, todo multi
        backorders = self.env['stock.picking']
        for picking in self:
            backorder_moves = backorder_moves or picking.move_lines
            if self._context.get('do_only_split'):
                not_done_bo_moves = backorder_moves.filtered(lambda move: move.id not in self._context.get('split', []))
            else:
                not_done_bo_moves = backorder_moves.filtered(lambda move: move.state not in ('done', 'cancel'))
            if not not_done_bo_moves:
                continue
            backorder_picking = picking.copy({
                'name': '/',
                'move_lines': [],
                'pack_operation_ids': [],
                'backorder_id': picking.id
            })
            picking.message_post(body=_("Back order <em>%s</em> <b>created</b>.") % (backorder_picking.name))
            not_done_bo_moves.write({'picking_id': backorder_picking.id})
            if not picking.date_done:
                picking.write({'date_done': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
                self.update_fecha_entrada(self.name, self.min_date[:10])
            backorder_picking.action_confirm()
            backorder_picking.action_assign()
            backorders |= backorder_picking
        return backorders

    
    def update_fecha_entrada(self, name, date_exp):
        # Actualizamos la fecha de los asientos por la de la fecha prevista
        tjacdmx_select_id_account_move = "SELECT am.id FROM account_move am \
                                        INNER JOIN account_move_line aml ON am.id = aml.move_id \
                                        WHERE aml.ref = '%s' \
                                        GROUP BY am.id;" % (name)

        self.env.cr.execute(tjacdmx_select_id_account_move)
        results = self.env.cr.fetchall()
        for ids in results:
            tjacdmx_update_status_account_move = "UPDATE account_move SET date = '%s' WHERE id =%s" % (date_exp,ids[0])
            self.env.cr.execute(tjacdmx_update_status_account_move)

            tjacdmx_update_status_account_move_line = "UPDATE account_move_line SET date = '%s', date_maturity='%s' WHERE move_id =%s" % (date_exp,date_exp,ids[0])
            self.env.cr.execute(tjacdmx_update_status_account_move_line)

    # 
    # def do_new_transfer(self):
    #     documentos = []
    #     obj_documento = self.env['presupuesto.documento']
    #     version = self.env['presupuesto.version'].search([], limit=1)
    #     cls_doc = self.env['presupuesto.clase_documento'].search([('tipo_documento','=','DEVENGADO')], limit=1)
    #     fecha = datetime.strptime(self.date, '%Y-%m-%d %H:%M:%S') if self.date else datetime.today()
    #     purchase_order = self.env['purchase.order'].search([('name', '=', self.origin)])
    #     items = self.env['purchase.order.line'].search([('order_id', '=', purchase_order.id)])
    #     for item in items:
    #         posicion_presupuestaria = item.product_id.product_tmpl_id.posicion_presupuestaria
    #         documento = {
    #             'clase_documento': cls_doc.id,
    #             'version': version.id,
    #             'ejercicio': fecha.year,
    #             'periodo': fecha.month,
    #             'fecha_contabilizacion': fecha.strftime("%Y-%m-%d"),
    #             'fecha_documento': fecha.strftime("%Y-%m-%d"),
    #             'detalle_documento_ids': [],
    #             'compra_id': purchase_order.id
    #         }
    #         detalle_doc = [0, False,
    #             {
    #             'centro_gestor': purchase_order.centro_gestor.id,
    #             'area_funcional': purchase_order.area_funcional.id,
    #             'fondo_economico': purchase_order.fondo_economico.id,
    #             'posicion_presupuestaria': posicion_presupuestaria.id,
    #             'importe': item.price_total,
    #             'momento_contable': 'DEVENGADO'
    #             }
    #         ]
    #         doc_idx = _check_exist_doc(documentos, documento)
    #         if doc_idx > -1:
    #             documentos[doc_idx]['detalle_documento_ids'].append(detalle_doc)
    #         else:
    #             documento['detalle_documento_ids'].append(detalle_doc)
    #             documentos.append(documento)
    #     for doc in documentos:
    #         obj_documento.create(doc)
    #     sale_search = self.env['purchase.order'].search([('name','=',self.origin)], limit=1)
    #     tjacdmx_update_status_mc = "UPDATE purchase_order SET status_account_move='DEVENGADO' WHERE id=%s" % (sale_search.id)
    #     self.env.cr.execute(tjacdmx_update_status_mc)
    #     return super(RecibirProductos, self).do_new_transfer()
    
    
    def compute_desglose(self):
        
        sql="""
                    SELECT pp.id
                        , pt.name AS producto
                        ,ppp.partida_presupuestal as partida
                         ,uom.name as unidad_medida
                        ,type
                        ,date_expected
                        ,product_qty as entradas
                        ,coalesce(price_unit, 0) as precio_unitario
                        ,coalesce(price_unit*product_qty,0) as importe_entrada
                        ,picking_id
                        ,state
                    FROM product_product pp
                    LEFT JOIN (SELECT  product_id, name, picking_id, date_expected, product_qty, price_unit, state
                            FROM stock_move
                            WHERE location_dest_id = 15
                            AND picking_id IS  NOT NULL) sm ON sm.product_id = pp.id
                    INNER JOIN product_template pt on pp.product_tmpl_id = pt.id
                    INNER JOIN presupuesto_partida_presupuestal ppp on pt.posicion_presupuestaria = ppp.id
                    INNER JOIN product_uom uom ON pt.uom_id = uom.id
                    WHERE picking_id = %s
                    ORDER BY ppp.partida_presupuestal, pt.name"""

        self.env.cr.execute(sql % (self.id))

        totales_compra = self.env.cr.dictfetchall()
        ids=[] 
        for i in totales_compra:
            partidas = {
                        'producto': i['producto'],
                        'partida': i['partida'],
                        'tipo': i['type'],
                        'date_expected': i['date_expected'],
                        'entradas': i['entradas'],
                        'unidad_medida': i['unidad_medida'],
                        'precio_unitario': i['precio_unitario'],
                        'importe_entrada': i['importe_entrada'],                        
                        'state': i['state'],
                        
                        }
            ids.append(partidas)
        html_items=""
        total_picking = 0
        for items in ids:
            producto=str(items['producto'].encode('ascii', 'ignore'))
            partida=str(items['partida'])
            unidad_medida=str(items['unidad_medida'])
            entradas=str(items['entradas'])
            tipo=str(items['tipo'])
            date_expected=str(items['date_expected'])
            state=str(items['state'])
            importe_entrada=items['importe_entrada']
            precio_unitario=items['precio_unitario']

            total_picking += importe_entrada
            
            html_items2="<tr>\
                            <td><p>"+producto+"</p></td> \
                            <td><p>"+partida+"</p></td> \
                            <td><p>"+tipo+"</p></td> \
                            <td><p>"+unidad_medida+"</p></td> \
                            <td><p>"+date_expected+"</p></td> \
                            <td><p>$"+str(precio_unitario)+"</p></td>\
                            <td><p>"+entradas+"</p></td> \
                            <td><p>$"+str(importe_entrada)+"</p></td>\
                            <td><p>"+state+"</p></td>\
                        </tr>"
            html_items+=html_items2.encode('ascii', 'ignore')

        html_items2="<tr><td><p></p></td> <td><p></p></td> <td><p></p></td> <td><p></p></td> <td><p></p></td>  <td><p></p></td>\
         <td><p>Total:</p></td> <td><h4>$"+str(total_picking)+"</h4></td></tr>"
        html_items+=html_items2.encode('ascii', 'ignore')
        html="""<table class="table">
                    <tr>
                        <td><p><strong>Producto</strong></p></td>
                        <td><p><strong>Partida</strong></p></td>
                        <td><p><strong>Tipo</strong></p></td>
                        <td><p><strong>Medida</strong></p></td>
                        <td><p><strong>Fecha_prevista</strong></p></td>
                        <td><p><strong>Precio unitario</strong></p></td>
                        <td><p><strong>Entradas</strong></p></td>
                        <td><p><strong>Importe entrada</strong></p></td>
                        <td><p><strong>Estado</strong></p></td>
                    </tr>
                    %s
            </table>""" % (html_items)
        self.totales=html

       

def _check_exist_doc(lista, doc):
    exist = -1
    for idx, item in enumerate(lista):
        if item['clase_documento'] == doc['clase_documento'] and \
            item['version'] == doc['version'] and \
            item['ejercicio'] == doc['ejercicio'] and \
            item['periodo'] == doc['periodo']:
            exist = idx
            break
    return exist



class SalidadeProductos(models.Model):
    _inherit = 'stock.scrap'

    product_id = fields.Many2one(comodel_name='product.product',string='Producto entregado',required=False, states={'done': [('readonly', True)]})
    area = fields.Many2one(comodel_name='presupuesto.areas.stok', string='Area')
    
    areas = fields.Char(string='Area')
    departamento = fields.Char(string='Departamento')
    ubicacion =fields.Char(string=u'Ubicación')

    justificacion = fields.Text(string=u'Justificación') 
    date_expected = fields.Datetime('Expected Date', default=fields.Datetime.now)
    origin = fields.Char(string='Source Document')
    lot_id = fields.Many2one(comodel_name=
        'stock.production.lot', string='Lot',
        states={'done': [('readonly', True)]}, domain="[('product_id', '=', product_id)]")
    package_id = fields.Many2one(comodel_name=
        'stock.quant.package',string='Package',
        states={'done': [('readonly', True)]})
    owner_id = fields.Many2one(comodel_name='res.partner',string='Owner', states={'done': [('readonly', True)]})
    scrap_qty = fields.Integer('Cantidad entregada', default=1.0,  states={'done': [('readonly', True)]})
    scrap_qty_clone = fields.Integer(string='Cantidad')
    product_uom_id = fields.Many2one(comodel_name='product.uom',string='Unit of Measure', required=False, states={'done': [('readonly', True)]})
    status = fields.Selection([('open','Abierto'),('cancel','Cancelado')],index=True, default='open')
    state = fields.Selection([
        ('cancel', 'Cancelado'),
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('delivered', 'Entregado')], string='Status', default="draft")
    partida_producto=fields.Char(string='Posición presupuestal',compute='_compute_partida',store=True)
    partida_producto_clone=fields.Char(string='Partida')
    importe_salida=fields.Float(string='Importe salida',compute='_compute_importe_slida',store=True)
    importe_salida_clone=fields.Float(string='Importe salida')

    salida_masiva_id = fields.Integer(string='salida_masiva_id')

    producto_solicit = fields.Char(compute="_get_linea_suministro", string='Producto solicitado')
    cantidad_solicit = fields.Integer(compute="_get_linea_suministro", string='Cantidad solicitada')
    
    linea_suministro = fields.Many2one(comodel_name='solicitud.suministro.lineas')


    
    def _get_linea_suministro(self):
        self.producto_solicit = self.linea_suministro.producto_solicit
        self.cantidad_solicit = self.linea_suministro.cantidad_solicit

    @api.onchange('product_id')
    
    def onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id.id
            total_salida =  '{0:.2f}'.format(float(self.product_id.standard_price * self.scrap_qty))
            self.update({'importe_salida': total_salida})
            self.update({'partida_producto': self.product_id.posicion_presupuestaria.partida_presupuestal})


    @api.onchange('scrap_qty')
    
    def replic(self):
        total_salida =  '{0:.2f}'.format(float(self.product_id.standard_price * self.scrap_qty))
        self.update({'importe_salida': total_salida})
        self.update({'scrap_qty_clone': self.scrap_qty})
    

    
    def _compute_partida(self):
        self.partida_producto=self.product_id.posicion_presupuestaria.partida_presupuestal

    
    def _compute_importe_slida(self):
        total_salida =  '{0:.2f}'.format(float(self.product_id.standard_price * self.scrap_qty))
        self.importe_salida = total_salida

    @api.onchange('product_id','scrap_qty')
    def _compute_importe_slida_2(self):
        total_salida =  '{0:.2f}'.format(float(self.product_id.standard_price * self.scrap_qty))
        self.update({'importe_salida_clone': total_salida})
        self.update({'partida_producto_clone': self.product_id.posicion_presupuestaria.partida_presupuestal})

    
    def action_ejecutar_salida(self):
        if(self.env['tjacdmx.cierre.inventario'].get_is_periodo_cerrado(
            datetime.strptime(self.date_expected, '%Y-%m-%d %H:%M:%S').month,
            datetime.strptime(self.date_expected, '%Y-%m-%d %H:%M:%S').year) == False):
            for scrap in self:
                moves = scrap._get_origin_moves() or self.env['stock.move']
                move = self.env['stock.move'].create(scrap._prepare_move_values())
                if move.product_id.type == 'product':
                    quants = self.env['stock.quant'].quants_get_preferred_domain(
                        move.product_qty, move,
                        domain=[
                            ('qty', '>', 0),
                            ('lot_id', '=', self.lot_id.id),
                            ('package_id', '=', self.package_id.id)],
                        preferred_domain_list=scrap._get_preferred_domain())
                    if any([not x[0] for x in quants]):
                        raise UserError(_('You cannot scrap a move without having available stock for %s. You can correct it with an inventory adjustment.') % move.product_id.name)
                    self.env['stock.quant'].quants_reserve(quants, move)
                move.action_done()
                scrap.write({'move_id': move.id, 'state': 'done'})
                moves.recalculate_move_state()

            self.update_importe_salida()
            return True
        else:
            return False



    
    def do_scrap(self):
        # Se mueve a la funcion action_ejecutar_salida(), se sobrecarga do_scrap para permitir status draft borrador
        # if(self.env['tjacdmx.cierre.inventario'].get_is_periodo_cerrado(
        #     datetime.strptime(self.date_expected, '%Y-%m-%d %H:%M:%S').month,
        #     datetime.strptime(self.date_expected, '%Y-%m-%d %H:%M:%S').year) == False):
        #     for scrap in self:
        #         moves = scrap._get_origin_moves() or self.env['stock.move']
        #         move = self.env['stock.move'].create(scrap._prepare_move_values())
        #         if move.product_id.type == 'product':
        #             quants = self.env['stock.quant'].quants_get_preferred_domain(
        #                 move.product_qty, move,
        #                 domain=[
        #                     ('qty', '>', 0),
        #                     ('lot_id', '=', self.lot_id.id),
        #                     ('package_id', '=', self.package_id.id)],
        #                 preferred_domain_list=scrap._get_preferred_domain())
        #             if any([not x[0] for x in quants]):
        #                 raise UserError(_('You cannot scrap a move without having available stock for %s. You can correct it with an inventory adjustment.') % move.product_id.name)
        #             self.env['stock.quant'].quants_reserve(quants, move)
        #         move.action_done()
        #         scrap.write({'move_id': move.id, 'state': 'done'})
        #         moves.recalculate_move_state()

        #     self.update_importe_salida()
        #     return True
        # else:
        #     return False
        return True
        
            
            
            
    
    
    def update_importe_salida(self):

        tjacdmx_select_importe_account_move = "SELECT sum(am.amount) AS importe \
                                                FROM account_move_line aml  \
                                                INNER JOIN account_move am ON aml.move_id = am.id \
                                                WHERE aml.name = '%s' AND aml.debit > 0 AND am.state != 'draft' \
                                                GROUP BY  aml.name" % (self.name)

        self.env.cr.execute(tjacdmx_select_importe_account_move)
        results = self.env.cr.fetchall()
        # if(results):
        importe_salida_move = results[0]
        self.update( { 'importe_salida_clone': importe_salida_move[0]} ) 
        self.update({'partida_producto_clone': self.product_id.posicion_presupuestaria.partida_presupuestal})
        
        # Actualizamos la fecha de los asientos por la de la fecha prevista
        tjacdmx_select_id_account_move = "SELECT am.id FROM account_move am \
                                        INNER JOIN account_move_line aml ON am.id = aml.move_id \
                                        WHERE aml.name = '%s' \
                                        GROUP BY am.id;" % (self.move_id.name)

        self.env.cr.execute(tjacdmx_select_id_account_move)
        results = self.env.cr.fetchall()
        for ids in results:
            tjacdmx_update_status_account_move = "UPDATE account_move SET date = '%s' WHERE id =%s" % (self.date_expected[:10],ids[0])
            self.env.cr.execute(tjacdmx_update_status_account_move)

        # Actualizamos la fecha de los asientos por la de la fecha prevista
        tjacdmx_select_id_move_lines = "SELECT aml.id FROM account_move_line aml \
                                        WHERE aml.name = '%s' " % (self.move_id.name)

        self.env.cr.execute(tjacdmx_select_id_move_lines)
        results = self.env.cr.fetchall()
        for ids in results:
            tjacdmx_update_status_account_move = "UPDATE account_move_line SET date = '%s', date_maturity='%s' WHERE id =%s" % (self.date_expected[:10],self.date_expected[:10],ids[0])
            self.env.cr.execute(tjacdmx_update_status_account_move)


        # "UPDATE stock_scrap scrap SET partida_producto = (SELECT partida_presupuestal FROM product_template pt INNER JOIN product_product pp ON pp.product_tmpl_id = pt.id INNER JOIN presupuesto_partida_presupuestal ppp ON pt.posicion_presupuestaria = ppp.id WHERE pp.id = scrap.product_id) WHERE scrap.id = %s" % (self.);
    
    
    def action_cancelar_salida(self):
        if(self.env['tjacdmx.cierre.inventario'].get_is_periodo_cerrado(
            datetime.strptime(self.date_expected, '%Y-%m-%d %H:%M:%S').month,
            datetime.strptime(self.date_expected, '%Y-%m-%d %H:%M:%S').year) == False):
            tjacdmx_select_id_move_lines = "SELECT am.id FROM account_move am \
                                            INNER JOIN account_move_line aml ON am.id = aml.move_id \
                                            WHERE aml.name = '%s' \
                                            GROUP BY am.id;" % (self.move_id.name)

            self.env.cr.execute(tjacdmx_select_id_move_lines)
            results = self.env.cr.fetchall()
            for ids in results:
                tjacdmx_update_status_account_move = "UPDATE account_move SET state = 'draft' WHERE id =%s" % (ids[0])
                self.env.cr.execute(tjacdmx_update_status_account_move)
                #self.env['account.move'].search([('id','=',account_move_line.move_id.id)], limit=1).unlink()
            
            self.move_id.quant_ids.update( { 'location_id': 15 } ) 
            self.update( { 'status': 'cancel' } ) 
            self.update( { 'state': 'cancel' } ) 
    
    
    def action_activar_salida(self):
        if(self.env['tjacdmx.cierre.inventario'].get_is_periodo_cerrado(
            datetime.strptime(self.date_expected, '%Y-%m-%d %H:%M:%S').month,
            datetime.strptime(self.date_expected, '%Y-%m-%d %H:%M:%S').year) == False):
            self.do_scrap()
            self.action_ejecutar_salida()
            self.update( { 'status': 'open' } ) 
            self.update( { 'state': 'done' } ) 
        
        
    
            
              

class PresupuestoTotalesPartida(models.Model):
    _name = 'presupuesto.totales.partida'
    _description = 'Totales por partida'

    partida=fields.Char(strig='Partida')
    total=fields.Float(string='Total')

class PresupuestoRequisicion(models.Model):
    _name = 'presupuesto.requisicion'
    _rec_name='req_nombre'
    _description = u'Requisición'
    _order = 'numero desc'

    descripcion=fields.Char(strig='Descripcion')
    numero=fields.Char(strig='Numero', required=True)
    indice=fields.Char(strig='Indice')
    area=fields.Char(strig='Area', required=True)
    partida=fields.Many2one(comodel_name='presupuesto.partida_presupuestal', string='Partida presupuestaria', required=True)
    req_nombre=fields.Char(compute='compute_nombre_req',string='Requisición')
    compras=fields.Html(compute='compute_compras',string='Entradas')

    
    def name_get(self):
        result = []
        for doc in self:
            name = '%s / %s' % (doc.req_nombre, doc.partida.partida_presupuestal if doc.partida.partida_presupuestal else '' )
            result.append((doc.id,name))
        return result

    
    def compute_nombre_req(self):
        descripcion_s= self.descripcion if self.descripcion else ''
        indice_s= self.indice if self.indice else ''
        nombre = str(self.numero)+" "+str(indice_s)+" "+str(self.area)
        self.req_nombre = nombre

    
    
    def compute_compras(self):
        
        sql="""
        select 
            po.id as compra_id, 
            po.name, 
            coalesce(importe_comprometido,0) as importe_comprometido, 
            coalesce(amount_total,0) as  amount_total,
            date_order,
            EXTRACT(MONTH FROM date_order) as periodo,
            EXTRACT(YEAR FROM date_order) as anio
         from presupuesto_requisicion req
        inner join purchase_order po on req.id = po.requisition_purchase
        where req.id=%s
        order by date_order DESC"""

        self.env.cr.execute(sql % (self.id))

        totales_compra = self.env.cr.dictfetchall()
        ids=[] 
        pediodos_all=[] 
        for i in totales_compra:
            partidas = {
                        'compra_id': i['compra_id'],
                        'name': i['name'],
                        'importe_comprometido': i['importe_comprometido'],
                        'amount_total': i['amount_total'],
                        'date_order': i['date_order'],
                        'periodo': i['periodo'],
                        'anio': i['anio'],
                        }
            ids.append(partidas)
            pediodos_all.append(i['periodo'])

        periodos= [x for x, y in collections.Counter(pediodos_all).items() if y >= 1]
 
        html_items=""
        total_compras = 0
        total_importe_comprometido = 0
        total_compras_grl = 0
        total_importe_comprometido_grl = 0
        
        
        for periodo in sorted(periodos, reverse=True):

            switcher = {
                1: "Enero",
                2: "Febrero",
                3: "Marzo",
                4: "Abril",
                5: "Mayo",
                6: "Junio",
                7: "Julio",
                8: "Agosto",
                9: "Septiembre",
                10: "Octubre",
                11: "Noviembre",
                12: "Diciembre"
            }
            
            mes = switcher.get(periodo, "Invalid month")
            html_items2="<tr>\
                                <td><p><strong>"+str(mes)+"</strong></p></td>\
                                <td><p></p></td> \
                                <td><p></p></td>\
                            </tr>"
            html_items+=html_items2.encode('ascii', 'ignore')

            ids_p = [x for x in ids if x['periodo'] == periodo]

            total_compras = 0
            total_importe_comprometido = 0
            
            for items in ids_p:
                compra_id=str(items['compra_id'])
                name=str(items['name'].encode('ascii', 'ignore'))
                importe_comprometido=items['importe_comprometido']
                amount_total=items['amount_total']
                date_order=items['date_order']

                disponible = importe_comprometido - amount_total

                total_compras += amount_total
                total_importe_comprometido += importe_comprometido
                
                html_items2="<tr>\
                                <td style=\"text-align: center;\"><p>"+date_order+"</p></td>\
                                <td style=\"text-align: center;\">\
                                    <a href=\"/web#id="+compra_id+"&view_type=form&model=purchase.order&menu_id=254&action=349\" target=\"_blank\" >\
                                        <p>"+name+"</p>\
                                    </a>\
                                </td> \
                                <td style=\"text-align: right;\"><p>$"+'{0:,.2f}'.format(importe_comprometido)+"</p></td>\
                                    <td style=\"text-align: right;\"><p>$"+'{0:,.2f}'.format(amount_total)+"</p></td>\
                            </tr>"
                html_items+=html_items2.encode('ascii', 'ignore')
            #Total por partida                            
            html_items2="<tr>\
                            <td><p> </p></td>\
                            <td><p> </p></td> \
                            <td style=\"text-align: right;\"><p><strong>$"+'{0:,.2f}'.format(total_importe_comprometido)+"</strong></p></td>\
                            <td style=\"text-align: right;\"><p><strong>$"+'{0:,.2f}'.format(total_compras)+"</strong></p></td>\
                         </tr>"
            html_items+=html_items2.encode('ascii', 'ignore')
            total_compras_grl += total_compras
            total_importe_comprometido_grl += total_importe_comprometido
        #Total general
        html_items2="<tr>\
                        <td><p></p></td> <td><p></p></td> <td><p></p></td> <td><p></p></td> \
                      </tr> \
                      <tr>  <td><p></p></td>  <td><p></p></td> \
                        <td style=\"text-align: right;\"><p><h4>$"+'{0:,.2f}'.format(total_importe_comprometido_grl)+"</h4></p></td>\
                        <td style=\"text-align: right;\"><p><h4>$"+'{0:,.2f}'.format(total_compras_grl)+"</h4></p></td>"
        html_items+=html_items2.encode('ascii', 'ignore')
        html="""<table class="table">
                    <thead>
                        <th style="text-align: center;"><p><strong>Fecha de compra</strong></p></th>
                        <th style="text-align: center;"><p><strong>Compra</strong></p></th>
                        <th style="text-align: center;"><p><strong>Importe comprometido</strong></p></th>
                        <th style="text-align: center;"><p><strong>Total compra</strong></p></th>
                    </thead>
                    %s
            </table>""" % (html_items)
        self.compras=html
 
 
