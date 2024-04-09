# -*- coding: utf-8 -*-
from odoo.tools.translate import _
import json
from lxml import etree
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.tools import float_is_zero, float_compare
from odoo.tools.misc import formatLang
from odoo.exceptions import UserError, RedirectWarning, ValidationError
import odoo.addons.decimal_precision as dp
import logging
import pytz
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from num2words import num2words

class Remisiones(models.Model):
    _name = 'tjacdmx.remisiones'
    _description = "Remision"
    _rec_name = 'number'
    _inherit = ['mail.thread']

    READONLY_STATES = {
        'purchase': [('readonly', True)],
        'done': [('readonly', True)],
        'cancel': [('readonly', True)],
    }

    @api.model
    def _default_requisicion_id(self):
        context = dict(self._context or {})
        requisicion_id = context.get('requisicion_id', False)
        if requisicion_id:
            data = requisicion_id
            return data
        return ''
    @api.model
    def _default_requisicion(self):
        context = dict(self._context or {})
        requicision = context.get('requicision', False)
        if requicision:
            data = requicision
            return data
        return ''
    @api.model
    def _default_number(self):
        context = dict(self._context or {})
        code_num = context.get('name_requi', False)
        if code_num:
            num_sm=self.env['tjacdmx.remisiones'].search([('origin.name','=',code_num)])
            identifi=len(num_sm)+1
            fecha = datetime.today()
            numero=code_num.split('/')[2]
            number_char="""ENTR/%s/%s%s""" % (str(fecha.year),str(numero),identifi)
            return number_char
    @api.model
    def _default_secuancia(self):
        context = dict(self._context or {})
        code_num = context.get('name_requi', False)
        if code_num:
            num_sm=self.env['tjacdmx.remisiones'].search([('origin.name','=',code_num)])
            identifi=len(num_sm)+1
            return identifi
    @api.model
    def get_fondo(self):
        return self.env['presupuesto.fondo_economico'].search([('fuente_financiamiento','=','11')])
    @api.model
    def get_centro_g(self):
        return self.env['presupuesto.centro_gestor'].search([('clave','=','21A000')])
    @api.model
    def get_area_funci(self):
        return self.env['presupuesto.area_funcional'].search([('area_funcional','=','020400')])

    @api.depends('remision_line_ids.price_total')
    def _amount_all(self):
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.remision_line_ids:
                amount_untaxed += line.price_subtotal
                # FORWARDPORT UP TO 10.0
                if order.company_id.tax_calculation_rounding_method == 'round_globally':
                    taxes = line.taxes_id.compute_all(line.price_unit, line.remision_id.currency_id, line.product_qty, product=line.product_id, partner=line.remision_id.partner_id)
                    amount_tax += sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
                else:
                    amount_tax += line.price_tax
            order.update({
                'amount_untaxed': order.currency_id.round(amount_untaxed),
                'amount_tax': order.currency_id.round(amount_tax),
                'amount_total': amount_untaxed + amount_tax,
            })
    @api.depends('remision_line_ids.date_planned')
    def _compute_date_planned(self):
        for order in self:
            min_date = False
            for line in order.remision_line_ids:
                if not min_date or line.date_planned < min_date:
                    min_date = line.date_planned
            if min_date:
                order.date_planned = min_date

    @api.model
    def _default_picking_type(self):
        type_obj = self.env['stock.picking.type']
        company_id = self.env.context.get('company_id') or self.env.user.company_id.id
        types = type_obj.search([('code', '=', 'incoming'), ('warehouse_id.company_id', '=', company_id)])
        if not types:
            types = type_obj.search([('code', '=', 'incoming'), ('warehouse_id', '=', False)])
        return types[:1]

    @api.depends('remision_line_ids.move_ids')
    def _compute_picking(self):
        for order in self:
            pickings = self.env['stock.picking']
            for line in order.remision_line_ids:
                # We keep a limited scope on purpose. Ideally, we should also use move_orig_ids and
                # do some recursive search, but that could be prohibitive if not done correctly.
                moves = line.move_ids | line.move_ids.mapped('returned_move_ids')
                moves = moves.filtered(lambda r: r.state != 'cancel')
                pickings |= moves.mapped('picking_id')
            order.picking_ids = pickings
            order.picking_count = len(pickings)

    @api.depends('picking_ids', 'picking_ids.state')
    def _compute_is_shipped(self):
        for order in self:
            if order.picking_ids and all([x.state == 'done' for x in order.picking_ids]):
                order.is_shipped = True

    number = fields.Char(default=_default_number)
    sequence = fields.Integer(default=_default_secuancia)
    name = fields.Char(string='Nombre', index=True, copy=False, help='')
    origin = fields.Many2one('presupuesto.requisicion.compras.compromisos.line',string='Origen',required=True,default=_default_requisicion_id)
    date_remision= fields.Date(string='Fecha', index=True,help="", copy=False,track_visibility='always',required=True)
    partner_id = fields.Many2one('res.partner', string='Proveedor',required=True)
    remision_line_ids= fields.One2many('tjacdmx.remisiones.line', 'remision_id', string='remision Lines',copy=True)
    invoice_id = fields.Many2one('account.invoice', string='Factura')
    amount_untaxed = fields.Monetary(string='Importe sin impuestos', store=True, readonly=True, compute='_amount_all', track_visibility='always')
    amount_tax = fields.Monetary(string='Impuestos', store=True, readonly=True, compute='_amount_all')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all')
    amount_si = fields.Monetary(string='sin impuestos retencion', store=True, readonly=True)
    company_id = fields.Many2one('res.company',string='Empresa', store=True, readonly=True)
    account_id = fields.Many2one('account.account', string='Cuenta',required=True, domain=[('deprecated', '=', False)],default=248)
    state = fields.Selection([
            ('draft','Borrador'),
            ('draft_pre', 'Enviado'),
            ('lista_devengado', 'En lista D.'),
            ('devengado', 'Devengado'),
            ('ejercido', 'Ejercido'),
            ('pagado', 'Pagado'),
            ('cancel', 'Cancelado'),
            ], string='Status', index=True, readonly=True, default='draft',
            track_visibility='onchange', copy=False,
            help="")
    tipo_remision=fields.Selection([('parcial', 'Factura Parcial'), ('final_parcial', 'Factura Parcial Completa'),('completa', 'Factura Completa')],strig='Tipo remision',default='completa',required=True)
    fondo_economico = fields.Many2one('presupuesto.fondo_economico',string='Fondo',required=True,readonly=1,  default=get_fondo)
    centro_gestor = fields.Many2one('presupuesto.centro_gestor',string='Centro gestor',required=True,readonly=1, default=get_centro_g)
    area_funcional = fields.Many2one('presupuesto.area_funcional',string='Área funcional',required=True, default=get_area_funci)
    currency_id = fields.Many2one('res.currency', 'Currency', required=True, states=READONLY_STATES, default=lambda self: self.env.user.company_id.currency_id.id)

    picking_type_id = fields.Many2one('stock.picking.type', 'Deliver To', states=READONLY_STATES, required=True, default=_default_picking_type,\
        help="This will determine picking type of incoming shipment")
    default_location_dest_id_usage = fields.Selection(related='picking_type_id.default_location_dest_id.usage', string='Destination Location Type',\
        help="Technical field used to display the Drop Ship Address", readonly=True)
    group_id = fields.Many2one('procurement.group', string="Procurement Group", copy=False)
    is_shipped = fields.Boolean(compute="_compute_is_shipped")
    picking_count = fields.Integer(compute='_compute_picking', string='Receptions', default=0)
    picking_ids = fields.Many2many('stock.picking', compute='_compute_picking', string='Receptions', copy=False)
    incoterm_id = fields.Many2one('stock.incoterms', 'Incoterm', states={'done': [('readonly', True)]}, help=u"Los términos comerciales internacionales son una serie de términos comerciales predefinidos utilizados en transacciones internacionales.")
    dest_address_id = fields.Many2one('res.partner', string='Drop Ship Address', states=READONLY_STATES,help=u"Ponga una dirección si desea entregar directamente del proveedor al cliente. De lo contrario, manténgase vacío para entregarlo a su propia empresa.")
    product_id = fields.Many2one('product.product', related='remision_line_ids.product_id', string='Product')
    create_uid = fields.Many2one('res.users', 'Responsible')
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True, states=READONLY_STATES, default=lambda self: self.env.user.company_id.id)
    date_planned = fields.Datetime(string='Scheduled Date', compute='_compute_date_planned', store=True, index=True)
    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position', oldname='fiscal_position')
    status_account_move = fields.Char(default='COMPROMETIDO')
    documentos= fields.One2many('presupuesto.documento', 'remision_id', string='Documentos',copy=True)
    no_factura= fields.Char(string='No. Factura')
    vrem = fields.Char(string='Tiene factura', store=True, compute='_compute_vrem')
    is_list_devengado = fields.Boolean(default=False)
    concepto_list = fields.Char(string='Concepto')
    importe_devengado_list =  fields.Float(select="Importe")
    devengado_doc = fields.Many2one('presupuesto.documento', string='Documento',compute='_compute_doc_devengados')
    pendiente = fields.Boolean(default=False)
    state_pendiente = fields.Selection([
            ('draft','Pendiente'),
            ('open','Abierto'),
            ('send', 'Enviado'),
            ], string='estado pendiente', index=True, readonly=True, default='draft', copy=False)


    @api.onchange('pendiente')
    def onchange_factura(self):
        if(self.pendiente==True):  
            pass
            #self.update({'no_factura': 'PENDIENTE'})  
            #self.update({'state_pendiente': 'open'})  


    def toggle_is_list_devengado(self):
        if(self.is_list_devengado==True):
            documento_valida=self.env['presupuesto.documento'].search([('remision_id','=', self.id)])
            if(documento_valida):
                raise ValidationError("Esta entrega ya esta en lista de devengados.")
            self.is_list_devengado=False
        else:
            self.is_list_devengado=True

    # @api.one
    def _compute_total_lines(self):
        total=0
        for it in self.remision_line_ids:
            total=total+float(it['price_subtotal'])
        self.devengado_doc = total
    
    # @api.one
    def _compute_doc_devengados(self):
        documento=self.env['presupuesto.documento']
        documento_valida=documento.search([('remision_id','=', self.id),('clase_documento','=', 7)],limit=1)
        self.devengado_doc = documento_valida
    
    # @api.one
    def _compute_vrem(self):
        remision=self.env['tjacdmx.remisiones']
        remision_valida=remision.search([('origin','=', self._default_requisicion_id()),('tipo_remision','in', ('parcial'))])
        facturas=[]
        for f in remision_valida:
            facturas.append(f.id)
        if(remision_valida):
            res='true' 
        else:
            res='false'
        self.vrem = res
        

    # 
    # def write(self, values):
    #     res = super(ResPartner, self).write(values)
    #     # here you can do accordingly
    #     return res

    
    @api.onchange('tipo_remision','partner_id')
    def _onchange_periodo(self):
        if(self.tipo_remision=='parcial'):
            remision=self.env['tjacdmx.remisiones']
            remision_valida=remision.search([('origin','=', self._default_requisicion_id()),('tipo_remision','=', 'parcial')])
            facturas=[]
            #raise ValidationError("debug:%s"%(remision_valida))
            for f in remision_valida:
                facturas.append(f.invoice_id.id)
            return {'domain': {'invoice_id': [('id', 'in', facturas)]}}
        else:
            pass

    
    def create_devengado_list(self):
        user_session = self.env['res.users'].browse(self.env.uid)
        permisos = self.env['presupuesto.permisos.presupuestales'].search([('usuario_id','=',user_session.id),('comprometido','=','open')])
        ctrl_periodo = self.env['control.periodos.wizard']
        if(permisos):
            if(self.concepto_list and self.importe_devengado_list):
                fecha = datetime.strptime(self.date_remision, '%Y-%m-%d') if self.date_remision else datetime.today()
                devengado=self.env['tjacdmx.devengados.line']
                devengado_list=self.env['tjacdmx.lista_devengados']
                detalle_dev={
                                'name': str(self.number.encode('utf-8'))+' - '+str(self.concepto_list.encode('utf-8')),
                                'fecha': self.date_remision,
                                'periodo': fecha.month,
                                'importe_origen': self.importe_devengado_list,
                                'importe': self.importe_devengado_list,
                                'state': 'send',
                                'area':self.origin.area,
                                'requisicion_compra':self.origin.requisicion_compra.id,
                                'partida':self.origin.requisicion_compra.partida.partida_presupuestal,
                                'remision_id': self.id
                            }
                devengado_created=devengado.create(detalle_dev)
                #devengado_created.action_devengar()
                if(devengado_created):
                    detalle_dev_list={
                                    'fecha': self.date_remision,
                                    'remision': self.id,
                                    'devengado_doc': devengado_created.id,
                                    'state': 'send'
                                }
                    devengado_list_created=devengado_list.create(detalle_dev_list)
                    self.write({'is_list_devengado': True}) 
                    self.write({'state': 'draft_pre'}) 
            else:
                raise ValidationError("Campos faltantes (Concepto y/o importe)")
        else:
            raise ValidationError("No cuenta con permisos para realizar esta operación, comuníquese con el administrador para revisar las operaciones autorizadas.")

    
    def cancel_remision(self):
        user_session = self.env['res.users'].browse(self.env.uid)
        permisos = self.env['presupuesto.permisos.presupuestales'].search([('usuario_id','=',user_session.id),('devengado','=','open')])
        ctrl_periodo = self.env['control.periodos.wizard']
        if(permisos):
            if(self.state=='draft_pre'):
                factura=self.env['account.invoice'].search([('id','=', self.invoice_id.id)])
                if(factura.state=='draft' or factura.state=='draft_pre'):
                    fecha = datetime.strptime(self.date_remision, '%Y-%m-%d') if self.date_remision else datetime.today()
                    query7 = "DELETE FROM tjacdmx_lista_devengados WHERE remision=%s" % (self.id)
                    query5 = "DELETE FROM tjacdmx_devengados_line WHERE remision_id=%s" % (self.id)
                    query6 = "DELETE FROM account_invoice WHERE remision=%s" % (self.id)
                    self.env.cr.execute(query7)
                    self.env.cr.execute(query5)
                    self.env.cr.execute(query6)
                    self.write({'state': 'draft'}) 
                else:
                    raise ValidationError("La entrega ya esta en proceso")    
            else:
                raise ValidationError("Campos faltantes (Concepto y/o importe)")
        else:
            raise ValidationError("No cuenta con permisos para realizar esta operación, comuníquese con el administrador para revisar las operaciones autorizadas.")
    
    
    def cancel_rem(self):
        user_session = self.env['res.users'].browse(self.env.uid)
        permisos = self.env['presupuesto.permisos.presupuestales'].search([('usuario_id','=',user_session.id),('comprometido','=','open')])
        ctrl_periodo = self.env['control.periodos.wizard']
        if(permisos):
            if(self.state=='draft'):
                self.write({'state': 'cancel'}) 
            else:
                raise ValidationError("Para cancelar es necesario que este en borrador")
        else:
            raise ValidationError("No cuenta con permisos para realizar esta operación, comuníquese con el administrador para revisar las operaciones autorizadas.")
    

    
    def validate_pres_devengado(self):
        user_session = self.env['res.users'].browse(self.env.uid)
        permisos = self.env['presupuesto.permisos.presupuestales'].search([('usuario_id','=',user_session.id),('comprometido','=','open')])
        ctrl_periodo = self.env['control.periodos.wizard']
        if(not ctrl_periodo.get_is_cerrado(self.date_remision)):
            if(permisos):
                if(self.remision_line_ids):
                    remision=self.env['tjacdmx.remisiones']
                    factura_model=self.env['account.invoice']
                    #raise ValidationError("debug: %s"%(self))
                    fecha = datetime.strptime(self.date_remision, '%Y-%m-%d') if self.date_remision else datetime.today()
                    devengado=self.env['tjacdmx.devengados.line']
                    amount_is_total=0.0

                    for line in self.remision_line_ids:
                        amount_tax_line = 0.0
                        for t in line.taxes_id:
                            if(t.amount>0):
                                pors='0.%s'%(int(t.amount))
                                amount_tax_line += line.price_subtotal*float(pors)
                            else:
                                amount_tax_line+=0
                                pass
                        amount_is_total+=amount_tax_line+line.price_subtotal
                    self.amount_si=amount_is_total
                    #raise ValidationError("debug: %s"%(self.amount_si))  
                    detalle_dev={
                                    'name': self.number,
                                    'fecha': fecha,
                                    'periodo': fecha.month,
                                    'importe_origen': self.amount_si,
                                    'importe': self.amount_si,
                                    'state': 'send',
                                    'area':self.origin.area,
                                    'requisicion_compra':self.origin.requisicion_compra.id,
                                    'partida':self.origin.requisicion_compra.partida.partida_presupuestal,
                                    'remision_id': self.id
                                }
                    if(self.tipo_remision=='completa'):
                        lines_factura=[]
                        for it in  self.remision_line_ids:
                            remision_line=self.env['tjacdmx.remisiones.line'].search([('id','=', it['id'])])
                            lines_factura.append((0,0, {
                                    'name': remision_line.name,
                                    'sequence': remision_line.sequence,
                                    'account_id': remision_line.account_id.id,
                                    'price_unit': remision_line.price_unit,
                                    'quantity': remision_line.product_qty,
                                    'product_id': remision_line.product_id.id,
                                    'line_remision_id': remision_line.id,
                                    'uom_id': remision_line.product_uom.id,
                                    'partner_id': self.partner_id.id,
                                    'tax_line_ids': remision_line.taxes_id
                                }))
                        factura_model_create=factura_model.create({
                                    'partner_id': self.partner_id.id,
                                    'origin': self.origin.name,
                                    'remision': self.id,
                                    'date_due': self.date_remision,
                                    'date_invoice': self.date_remision,
                                    'reference_provedor': self.no_factura,
                                    'account_id': self.account_id.id,
                                    'state': 'draft',
                                    'stateinvoice': 'true',
                                    'type':'in_invoice',
                                    'journal_id':2,
                                    'invoice_line_ids':lines_factura,
                                    'requicision': self.origin.id,
                                })
                        
                        if(factura_model_create):
                            for line_fac in factura_model_create.invoice_line_ids:
                                remision_line=self.env['tjacdmx.remisiones.line'].search([('id','=', line_fac.line_remision_id)])
                                for tax in remision_line.taxes_id:
                                    query = "INSERT INTO account_invoice_line_tax values(%s,%s)" % (line_fac.id,tax.id)
                                    self.env.cr.execute(query)
                            taxes=self.env['account.invoice.tax']
                            for line_fac in factura_model_create.invoice_line_ids:
                                remision_line=self.env['tjacdmx.remisiones.line'].search([('id','=', line_fac.line_remision_id)])
                                for tax in remision_line.taxes_id:
                                    if(tax.amount<0):
                                        if(tax.id==27):
                                            preTax=abs(tax.amount)
                                            tax27=str(preTax).replace(".", "")
                                            pors='-0.0%s'%(tax27)
                                        else:
                                            taxv=int(tax.amount)*-1
                                            if(taxv>9):
                                                pors='-0.%s'%(taxv)
                                            else:
                                                pors='-0.0%s'%(taxv)
                                    else:
                                        pors='0.%s'%(int(tax.amount))
                                    total=line_fac.price_unit*float(pors)
                                    #raise ValidationError("debug: %s"%(total))  
                                    vals = {
                                        'invoice_id': factura_model_create.id,
                                        'name': tax.name,
                                        'tax_id': tax.id,
                                        'amount': total,
                                        'manual': False,
                                        'sequence': 1,
                                        'account_analytic_id': remision_line.account_analytic_id.id,
                                        'account_id': tax.account_id.id
                                    }
                                    taxes_create=taxes.create(vals)
                            if(self.is_list_devengado==False):
                                if(self.pendiente==False):
                                    devengado_created=devengado.create(detalle_dev)
                                
                                
                            self.write({'invoice_id': factura_model_create.id})
                            self.write({'state': 'draft_pre'})
                            if(self.tipo_remision=='completa'):
                                if(factura_model_create.state=='draft'):
                                    factura_model_create.write({'state': 'draft'})
                                elif(factura_model_create.state=='draft_pre'):
                                    factura_model_create.write({'state': 'draft_pre'})
                                elif(factura_model_create.state=='open'):
                                    factura_model_create.write({'state': 'open'})
                                elif(factura_model_create.state=='clc'):
                                    factura_model_create.write({'state': 'clc'})
                                elif(factura_model_create.state=='paid'):
                                    factura_model_create.write({'state': 'paid'})
                            elif(self.tipo_remision=='parcial'):
                                if(factura_model_create.state=='draft'):
                                    factura_model_create.write({'state': 'draft'})
                                elif(factura_model_create.state=='draft_pre'):
                                    factura_model_create.write({'state': 'draft_pre'})
                                elif(factura_model_create.state=='open'):
                                    factura_model_create.write({'state': 'open'})
                                elif(factura_model_create.state=='clc'):
                                    factura_model_create.write({'state': 'clc'})
                                elif(factura_model_create.state=='paid'):
                                    factura_model_create.write({'state': 'paid'})
                            
                    else:
                        remision_origen=self.env['tjacdmx.remisiones'].search([('origin','=', self.origin.id),('sequence','=',1)])
                        factura=self.env['account.invoice'].search([('id','=', remision_origen.invoice_id.id)])
                        if(factura):
                            if(self.tipo_remision=='parcial' and factura.state=='draft' or self.tipo_remision=='final_parcial'):
                                factura_lines_model=self.env['account.invoice.line']
                                lines_factura=[]
                                for it in  self.remision_line_ids:
                                    order_line=self.env['tjacdmx.remisiones.line'].search([('id','=', it['id'])])
                                    factura_model_create=factura_lines_model.create({
                                                'invoice_id': factura.id,
                                                'name': order_line.name,
                                                'sequence': order_line.sequence,
                                                'account_id': order_line.account_id.id,
                                                'price_unit': order_line.price_unit,
                                                'quantity': order_line.product_qty,
                                                'product_id': order_line.product_id.id,
                                                'line_remision_id': order_line.remision_id,
                                                'uom_id': order_line.product_uom.id,
                                                'partner_id': self.partner_id.id,
                                                'invoice_line_tax_ids': order_line.taxes_id
                                            })
                                if(self.tipo_remision=='final_parcial'):
                                    remision_related=self.env['tjacdmx.remisiones'].search([('origin','=', self.origin.id),('invoice_id','=',factura.id)])
                                    if(self.pendiente==False):
                                        devengado_created=devengado.create(detalle_dev)
                                        
                                    self.write({'invoice_id': factura.id})
                                    self.write({'state': 'draft_pre'})
                                    remision_related.write({'state': 'draft_pre'})
                                    if(factura_model_create.state=='draft'):
                                        factura_model_create.write({'state': 'draft'})
                                    elif(factura_model_create.state=='draft_pre'):
                                        factura_model_create.write({'state': 'draft_pre'})
                                    elif(factura_model_create.state=='open'):
                                        factura_model_create.write({'state': 'open'})
                                    elif(factura_model_create.state=='clc'):
                                        factura_model_create.write({'state': 'clc'})
                                    elif(factura_model_create.state=='paid'):
                                        factura_model_create.write({'state': 'paid'})
                                elif(self.tipo_remision=='completa'):
                                    self.write({'state': 'draft_pre'})
                                    if(factura_model_create.state=='draft'):
                                        factura_model_create.write({'state': 'draft'})
                                    elif(factura_model_create.state=='draft_pre'):
                                        factura_model_create.write({'state': 'draft_pre'})
                                    elif(factura_model_create.state=='open'):
                                        factura_model_create.write({'state': 'open'})
                                    elif(factura_model_create.state=='clc'):
                                        factura_model_create.write({'state': 'clc'})
                                    elif(factura_model_create.state=='paid'):
                                        factura_model_create.write({'state': 'paid'})
                                elif(self.tipo_remision=='parcial'):
                                    self.write({'state': 'draft_pre'})
                                    if(factura_model_create.state=='draft'):
                                        factura_model_create.write({'state': 'draft'})
                                    elif(factura_model_create.state=='draft_pre'):
                                        factura_model_create.write({'state': 'draft_pre'})
                                    elif(factura_model_create.state=='open'):
                                        factura_model_create.write({'state': 'open'})
                                    elif(factura_model_create.state=='clc'):
                                        factura_model_create.write({'state': 'clc'})
                                    elif(factura_model_create.state=='paid'):
                                        factura_model_create.write({'state': 'paid'})
                            else:
                                raise ValidationError("La factura seleccionado para esta entrega ya esta en proceso, favor de verificar la información.")
                        else:
                            raise ValidationError("Aun no se ha validado la primera entrega, favor de revisar e internar de nuevo")
                else:
                    raise ValidationError("No hay elementos en la entrega para continuar")
            else:
                raise ValidationError("No cuenta con permisos para realizar esta operación, comuníquese con el administrador para revisar las operaciones autorizadas.")
    
    def validate_pres_devengado_befo(self):
        user_session = self.env['res.users'].browse(self.env.uid)
        permisos = self.env['presupuesto.permisos.presupuestales'].search([('usuario_id','=',user_session.id),('comprometido','=','open')])
        ctrl_periodo = self.env['control.periodos.wizard']
        if(self.is_list_devengado==False):
            fecha_fact=self.date_remision
        else:
            tz_NY = pytz.timezone('America/Mexico_City') 
            datetime_CDMX = datetime.now(tz_NY)
            fecha=datetime_CDMX.strftime('%Y-%m-%d')
            fecha_fact=fecha
        if(not ctrl_periodo.get_is_cerrado(fecha_fact)):
            if(permisos):
                if(self.remision_line_ids):
                    remision=self.env['tjacdmx.remisiones']
                    factura_model=self.env['account.invoice']
                    #raise ValidationError("debug: %s"%(self))
                    fecha = datetime.strptime(self.date_remision, '%Y-%m-%d') if self.date_remision else datetime.today()
                    devengado=self.env['tjacdmx.devengados.line']
                    amount_is_total=0.0

                    for line in self.remision_line_ids:
                        amount_tax_line = 0.0
                        for t in line.taxes_id:
                            if(t.amount>0):
                                pors='0.%s'%(int(t.amount))
                                amount_tax_line += line.price_subtotal*float(pors)
                            else:
                                amount_tax_line+=0
                                pass
                        amount_is_total+=amount_tax_line+line.price_subtotal
                    self.amount_si=amount_is_total
                    #raise ValidationError("debug: %s"%(self.amount_si))  
                    detalle_dev={
                                    'name': self.number,
                                    'fecha': fecha,
                                    'periodo': fecha.month,
                                    'importe_origen': self.amount_si,
                                    'importe': self.amount_si,
                                    'state': 'send',
                                    'area':self.origin.area,
                                    'requisicion_compra':self.origin.requisicion_compra.id,
                                    'partida':self.origin.requisicion_compra.partida.partida_presupuestal,
                                    'remision_id': self.id
                                }
                    if(self.tipo_remision=='completa'):
                        lines_factura=[]
                        for it in  self.remision_line_ids:
                            remision_line=self.env['tjacdmx.remisiones.line'].search([('id','=', it['id'])])
                            lines_factura.append((0,0, {
                                    'name': remision_line.name,
                                    'sequence': remision_line.sequence,
                                    'account_id': remision_line.account_id.id,
                                    'price_unit': remision_line.price_unit,
                                    'quantity': remision_line.product_qty,
                                    'product_id': remision_line.product_id.id,
                                    'line_remision_id': remision_line.id,
                                    'uom_id': remision_line.product_uom.id,
                                    'partner_id': self.partner_id.id,
                                    'tax_line_ids': remision_line.taxes_id
                                }))
                        factura_model_create=factura_model.create({
                                    'partner_id': self.partner_id.id,
                                    'origin': self.origin.name,
                                    'remision': self.id,
                                    'date_due': self.date_remision,
                                    'date_invoice': self.date_remision,
                                    'reference_provedor': self.no_factura,
                                    'account_id': self.account_id.id,
                                    'state': 'draft',
                                    'stateinvoice': 'true',
                                    'type':'in_invoice',
                                    'journal_id':2,
                                    'invoice_line_ids':lines_factura,
                                    'requicision': self.origin.id,
                                })
                        
                        if(factura_model_create):
                            for line_fac in factura_model_create.invoice_line_ids:
                                remision_line=self.env['tjacdmx.remisiones.line'].search([('id','=', line_fac.line_remision_id)])
                                for tax in remision_line.taxes_id:
                                    query = "INSERT INTO account_invoice_line_tax values(%s,%s)" % (line_fac.id,tax.id)
                                    self.env.cr.execute(query)
                            taxes=self.env['account.invoice.tax']
                            for line_fac in factura_model_create.invoice_line_ids:
                                remision_line=self.env['tjacdmx.remisiones.line'].search([('id','=', line_fac.line_remision_id)])
                                for tax in remision_line.taxes_id:
                                    if(tax.amount<0):
                                        if(tax.id==27):
                                            preTax=abs(tax.amount)
                                            tax27=str(preTax).replace(".", "")
                                            pors='-0.0%s'%(tax27)
                                        else:
                                            taxv=int(tax.amount)*-1
                                            if(taxv>9):
                                                pors='-0.%s'%(taxv)
                                            else:
                                                pors='-0.0%s'%(taxv)
                                    else:
                                        pors='0.%s'%(int(tax.amount))
                                    total=line_fac.price_unit*float(pors)
                                    #raise ValidationError("debug: %s"%(total))  
                                    vals = {
                                        'invoice_id': factura_model_create.id,
                                        'name': tax.name,
                                        'tax_id': tax.id,
                                        'amount': total,
                                        'manual': False,
                                        'sequence': 1,
                                        'account_analytic_id': remision_line.account_analytic_id.id,
                                        'account_id': tax.account_id.id
                                    }
                                    taxes_create=taxes.create(vals)
                                
                            self.write({'invoice_id': factura_model_create.id})
                            self.write({'state': 'devengado'})
                            self.write({'pendiente':False})
                            if(self.tipo_remision=='completa'):
                                if(factura_model_create.state=='draft'):
                                    factura_model_create.write({'state': 'draft'})
                                elif(factura_model_create.state=='draft_pre'):
                                    factura_model_create.write({'state': 'draft_pre'})
                                elif(factura_model_create.state=='open'):
                                    factura_model_create.write({'state': 'open'})
                                elif(factura_model_create.state=='clc'):
                                    factura_model_create.write({'state': 'clc'})
                                elif(factura_model_create.state=='paid'):
                                    factura_model_create.write({'state': 'paid'})
                            elif(self.tipo_remision=='parcial'):
                                if(factura_model_create.state=='draft'):
                                    factura_model_create.write({'state': 'draft'})
                                elif(factura_model_create.state=='draft_pre'):
                                    factura_model_create.write({'state': 'draft_pre'})
                                elif(factura_model_create.state=='open'):
                                    factura_model_create.write({'state': 'open'})
                                elif(factura_model_create.state=='clc'):
                                    factura_model_create.write({'state': 'clc'})
                                elif(factura_model_create.state=='paid'):
                                    factura_model_create.write({'state': 'paid'})
                            
                    else:
                        remision_origen=self.env['tjacdmx.remisiones'].search([('origin','=', self.origin.id),('sequence','=',1)])
                        factura=self.env['account.invoice'].search([('id','=', remision_origen.invoice_id.id)])
                        if(factura):
                            if(self.tipo_remision=='parcial' and factura.state=='draft' or self.tipo_remision=='final_parcial'):
                                factura_lines_model=self.env['account.invoice.line']
                                lines_factura=[]
                                for it in  self.remision_line_ids:
                                    order_line=self.env['tjacdmx.remisiones.line'].search([('id','=', it['id'])])
                                    factura_model_create=factura_lines_model.create({
                                                'invoice_id': factura.id,
                                                'name': order_line.name,
                                                'sequence': order_line.sequence,
                                                'account_id': order_line.account_id.id,
                                                'price_unit': order_line.price_unit,
                                                'quantity': order_line.product_qty,
                                                'product_id': order_line.product_id.id,
                                                'line_remision_id': order_line.remision_id,
                                                'uom_id': order_line.product_uom.id,
                                                'partner_id': self.partner_id.id,
                                                'invoice_line_tax_ids': order_line.taxes_id
                                            })
                                if(self.tipo_remision=='final_parcial'):
                                    remision_related=self.env['tjacdmx.remisiones'].search([('origin','=', self.origin.id),('invoice_id','=',factura.id)])
                                    if(self.is_list_devengado==False):
                                        devengado_created=devengado.create(detalle_dev)
                                        
                                    self.write({'invoice_id': factura.id})
                                    self.write({'state': 'devengado'})
                                    remision_related.write({'state': 'devengado'})
                                    factura.write({'state': 'draft_pre'})
                                elif(self.tipo_remision=='completa'):
                                    self.write({'state': 'devengado'})
                                    factura.write({'state': 'draft_pre'})
                                elif(self.tipo_remision=='parcial'):
                                    self.write({'state': 'devengado'})
                                    factura.write({'state': 'draft_pre'})
                                self.write({'pendiente':False})
                            else:
                                raise ValidationError("La factura seleccionado para esta entrega ya esta en proceso, favor de verificar la información.")
                        else:
                            raise ValidationError("Aun no se ha validado la primera entrega, favor de revisar e internar de nuevo")
                else:
                    raise ValidationError("No hay elementos en la entrega para continuar")
            else:
                raise ValidationError("No cuenta con permisos para realizar esta operación, comuníquese con el administrador para revisar las operaciones autorizadas.")

    
    def validate_pres_devengado_before(self):
        user_session = self.env['res.users'].browse(self.env.uid)
        permisos = self.env['presupuesto.permisos.presupuestales'].search([('usuario_id','=',user_session.id),('comprometido','=','open')])
        ctrl_periodo = self.env['control.periodos.wizard']
        if(permisos):
            if(self.remision_line_ids):
                remision=self.env['tjacdmx.remisiones']
                factura_model=self.env['account.invoice']
                #raise ValidationError("debug: %s"%(self))
                fecha = datetime.strptime(self.date_remision, '%Y-%m-%d') if self.date_remision else datetime.today()
                devengado=self.env['tjacdmx.devengados.line']
                amount_is_total=0.0
                for line in self.remision_line_ids:
                    amount_tax_line = 0.0
                    for t in line.taxes_id:
                        if(t.amount>0):
                            pors='0.%s'%(int(t.amount))
                            amount_tax_line += line.price_unit*float(pors)
                        else:
                            amount_tax_line+=0
                            pass
                    amount_is_total+=amount_tax_line+line.price_unit
                self.amount_si=amount_is_total
                # remision_origen=self.env['tjacdmx.remisiones'].search([('origin','=', self.origin.id),('sequence','=',1)])
                factura=self.env['account.invoice'].search([('remision','=', self.id)])
                if(factura):
                    if(factura.state=='draft_pre' or factura.state=='draft' or self.tipo_remision=='final_parcial'):
                        factura.write({'reference_provedor':self.no_factura})
                        self.write({'pendiente':False})
                        factura_lines_model=self.env['account.invoice.line']
                        lines_factura=[]
                        factura_line=self.env['account.invoice.line'].search([('invoice_id','=', factura.id)])
                        if(factura_line):
                            query_line_invoice = "DELETE FROM account_invoice_line WHERE invoice_id=%s" % (factura.id)
                            query_tax = "DELETE FROM account_invoice_tax WHERE invoice_id=%s" % (factura.id)
                            self.env.cr.execute(query_line_invoice)
                            self.env.cr.execute(query_tax)
                        taxes_created=[]
                        for it in  self.remision_line_ids:
                            order_line=self.env['tjacdmx.remisiones.line'].search([('id','=', it['id'])])
                            factura_model_create=factura_lines_model.create({
                                        'invoice_id': factura.id,
                                        'name': order_line.name,
                                        'sequence': order_line.sequence,
                                        'account_id': order_line.account_id.id,
                                        'price_unit': order_line.price_unit,
                                        'quantity': order_line.product_qty,
                                        'product_id': order_line.product_id.id,
                                        'line_remision_id': order_line.remision_id,
                                        'uom_id': order_line.product_uom.id,
                                        'partner_id': self.partner_id.id,
                                        'invoice_line_tax_ids': order_line.taxes_id
                                    })
                            for tax in order_line.taxes_id:
                                query = "INSERT INTO account_invoice_line_tax values(%s,%s)" % (factura_model_create.id,tax.id)
                                self.env.cr.execute(query)
                            taxes_created.append({
                                        'invoice_id': factura.id,
                                        'price_unit': order_line.price_unit,
                                        'line_remision_id': order_line.remision_id,
                                        'invoice_line_tax_ids': order_line.taxes_id
                                    })
                        for line_fac in taxes_created:
                            taxes=self.env['account.invoice.tax']
                            remision_line=self.env['tjacdmx.remisiones.line'].search([('id','=', line_fac['line_remision_id'].id)])
                            for tax in line_fac['invoice_line_tax_ids']:
                                if(tax.amount<0):
                                    taxv=int(tax.amount)*-1
                                    if(taxv>9):
                                        pors='-0.%s'%(taxv)
                                    else:
                                        pors='-0.0%s'%(taxv)
                                else:
                                    pors='0.%s'%(int(tax.amount))
                                total=line_fac['price_unit']*float(pors)
                                vals = {
                                    'invoice_id': line_fac['invoice_id'],
                                    'name': tax.name,
                                    'tax_id': tax.id,
                                    'amount': total,
                                    'manual': False,
                                    'sequence': 1,
                                    'account_analytic_id': remision_line.account_analytic_id.id,
                                    'account_id': tax.account_id.id
                                }
                                taxes_create=taxes.create(vals)
                        if(self.tipo_remision=='final_parcial'):
                            remision_related=self.env['tjacdmx.remisiones'].search([('origin','=', self.origin.id),('invoice_id','=',factura.id)])
                            self.write({'invoice_id': factura.id})
                            self.write({'state': 'devengado'})
                            remision_related.write({'state': 'devengado'})
                            if(factura.state=='draft'):
                                factura.write({'state': 'draft'})
                            elif(factura.state=='draft_pre'):
                                factura.write({'state': 'draft_pre'})
                            elif(factura.state=='open'):
                                factura.write({'state': 'open'})
                            elif(factura.state=='clc'):
                                factura.write({'state': 'clc'})
                            elif(factura.state=='paid'):
                                factura.write({'state': 'paid'})
                        elif(self.tipo_remision=='completa'):
                            self.write({'state': 'devengado'})
                            if(factura.state=='draft'):
                                factura.write({'state': 'draft'})
                            elif(factura.state=='draft_pre'):
                                factura.write({'state': 'draft_pre'})
                            elif(factura.state=='open'):
                                factura.write({'state': 'open'})
                            elif(factura.state=='clc'):
                                factura.write({'state': 'clc'})
                            elif(factura.state=='paid'):
                                factura.write({'state': 'paid'})

                        elif(self.tipo_remision=='parcial'):
                            self.write({'state': 'devengado'})
                            if(factura.state=='draft'):
                                factura.write({'state': 'draft'})
                            elif(factura.state=='draft_pre'):
                                factura.write({'state': 'draft_pre'})
                            elif(factura.state=='open'):
                                factura.write({'state': 'open'})
                            elif(factura.state=='clc'):
                                factura.write({'state': 'clc'})
                            elif(factura.state=='paid'):
                                factura.write({'state': 'paid'})
                    else:
                        raise ValidationError("La factura seleccionado para esta entrega ya esta en proceso, favor de verificar la información.")
                else:
                    self.validate_pres_devengado_befo()
            else:
                raise ValidationError("No hay elementos en la entrega para continuar")
        else:
            raise ValidationError("No cuenta con permisos para realizar esta operación, comuníquese con el administrador para revisar las operaciones autorizadas.")


###abre ventana para crear devengado presupuestalmente 
    
    def button_open_devengado_window(self):
        user_session = self.env['res.users'].browse(self.env.uid)
        permisos = self.env['presupuesto.permisos.presupuestales'].search([('usuario_id','=',user_session.id),('devengado','=','open')])
        ctrl_periodo = self.env['control.periodos.wizard']
        if(permisos):
            if(self.remision_line_ids):
                return {
                    'name': _("Recibir pedido"),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'momentos_presupuestales_remi.wizard',
                    'target': 'new',
                    'type': 'ir.actions.act_window',
                    'context': {'remision': self.id,'momento': str('devengado'),'provision': 'False','is_devengado': self.is_list_devengado,}
                } 
            else:
                raise ValidationError("Necesita al menos un concepto para continuar.")
        else:
            raise ValidationError("No cuenta con permisos para realizar esta operación, comuníquese con el administrador para revisar las operaciones autorizadas.")

    
    def add_line_remision_to_invoice(self):
        if(self.sequence==1):
            factura_model=self.env['account.invoice'].search([('id','=', self.invoice_id.id)])
            factura_model.action_invoice_open()
            sql_put = "UPDATE account_invoice SET state='draft' WHERE id=%s" % (factura_model.id)
            self.env.cr.execute(sql_put)
            self.write({'state': 'open'})
        else:
            print('process')

    
    def _get_destination_location(self):
        self.ensure_one()
        if self.dest_address_id:
            return self.dest_address_id.property_stock_customer.id
        return self.picking_type_id.default_location_dest_id.id

    @api.model
    def _prepare_picking(self):
        if not self.group_id:
            self.group_id = self.group_id.create({
                'name': self.number,
                'partner_id': self.partner_id.id
            })
        if not self.partner_id.property_stock_supplier.id:
            raise UserError(_("You must set a Vendor Location for this partner %s") % self.partner_id.name)
        return {
            'picking_type_id': self.picking_type_id.id,
            'partner_id': self.partner_id.id,
            'date': self.date_remision,
            'origin': self.number,
            'location_dest_id': self._get_destination_location(),
            'location_id': self.partner_id.property_stock_supplier.id,
            'company_id': self.company_id.id,
        }


    
    def delete_picking_before(self):
        stock=self.env['stock.picking'].search([('origin', '=', self.number)])
        stock_move=self.env['stock.move'].search([('picking_id', '=', stock.id)])
        if(stock.state=='draft' or stock.state=='cancel' or stock.state=='assigned'):
            for pik in stock:
                stick_ids= pik.id if pik.id else 0
                query5 = "DELETE FROM stock_pack_operation WHERE picking_id=%s" % (stick_ids)
                query6 = "DELETE FROM stock_move WHERE picking_id=%s" % (stick_ids)
                query7 = "DELETE FROM stock_picking WHERE id=%s" % (stick_ids)
                if(stock_move):
                    for mov in stock_move:
                        query8 = """SELECT * from stock_quant_move_rel WHERE move_id=%s"""
                        self.env.cr.execute(query8 % (mov.id))
                        rows_sql = self.env.cr.dictfetchall()
                        # raise UserError(_("debug: %s--%s" % (rows_sql,stock_move.id)))
                        if(rows_sql):
                            query9 = "DELETE FROM stock_quant WHERE id=%s" % (rows_sql.quant_id)
                            self.env.cr.execute(query9)
                self.env.cr.execute(query5)
                self.env.cr.execute(query6)
                self.env.cr.execute(query7)
        else:
            raise UserError(_("Ya se encuentran movimientos de almacén validados."))

    
    def create_picking_before(self):
        self._create_picking()
       
        
        


    
    def _create_picking(self):
        StockPicking = self.env['stock.picking']
        for order in self:
            if any([ptype in ['product', 'consu'] for ptype in order.remision_line_ids.mapped('product_id.type')]):
                
                pickings = order.picking_ids.filtered(lambda x: x.state not in ('done','cancel'))
                if not pickings:
                    
                    res = order._prepare_picking()
                    picking = StockPicking.create(res)
                else:
                    picking = pickings[0]
                moves = order.remision_line_ids._create_stock_moves(picking)
                moves = moves.filtered(lambda x: x.state not in ('done', 'cancel')).action_confirm()
                seq = 0
                for move in sorted(moves, key=lambda move: move.date_expected):
                    seq += 5
                    move.sequence = seq
                moves.force_assign()
                picking.message_post_with_view('mail.message_origin_link',
                    values={'self': picking, 'origin': order},
                    subtype_id=self.env.ref('mail.mt_note').id)
        return True

    
    def _add_supplier_to_product(self):
        # Add the partner in the supplier list of the product if the supplier is not registered for
        # this product. We limit to 10 the number of suppliers for a product to avoid the mess that
        # could be caused for some generic products ("Miscellaneous").
        for line in self.remision_line_ids:
            # Do not add a contact as a supplier
            partner = self.partner_id if not self.partner_id.parent_id else self.partner_id.parent_id
            if partner not in line.product_id.seller_ids.mapped('name') and len(line.product_id.seller_ids) <= 10:
                currency = partner.property_purchase_currency_id or self.env.user.company_id.currency_id
                supplierinfo = {
                    'name': partner.id,
                    'sequence': max(line.product_id.seller_ids.mapped('sequence')) + 1 if line.product_id.seller_ids else 1,
                    'product_uom': line.product_uom.id,
                    'min_qty': 0.0,
                    'price': self.currency_id.compute(line.price_unit, currency),
                    'currency_id': currency.id,
                    'delay': 0,
                }
                vals = {
                    'seller_ids': [(0, 0, supplierinfo)],
                }
                try:
                    line.product_id.write(vals)
                except AccessError:  # no write access rights -> just ignore
                    break

    
    def action_view_picking(self):
        '''
        This function returns an action that display existing picking orders of given purchase order ids.
        When only one found, show the picking immediately.
        '''
        action = self.env.ref('stock.action_picking_tree')
        result = action.read()[0]

        #override the context to get rid of the default filtering on picking type
        result.pop('id', None)
        result['context'] = {}
        pick_ids = sum([order.picking_ids.ids for order in self], [])
        #choose the view_mode accordingly
        if len(pick_ids) > 1:
            result['domain'] = "[('id','in',[" + ','.join(map(str, pick_ids)) + "])]"
        elif len(pick_ids) == 1:
            res = self.env.ref('stock.view_picking_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = pick_ids and pick_ids[0] or False
        return result








class RemisionesLine(models.Model):
    _name = "tjacdmx.remisiones.line"
    _description = "Remision Line"
    _order = 'sequence, id'


    @api.depends('product_qty', 'price_unit', 'taxes_id')
    def _compute_amount(self):
        for line in self:
            taxes = line.taxes_id.compute_all(line.price_unit, line.remision_id.currency_id, line.product_qty, product=line.product_id, partner=line.remision_id.partner_id)
            line.update({
                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })

    
    def _compute_tax_id(self):
        for line in self:
            fpos = line.remision_id.fiscal_position_id or line.remision_id.partner_id.property_account_position_id
            # If company_id is set, always filter taxes by the company
            taxes = line.product_id.supplier_taxes_id.filtered(lambda r: not line.company_id or r.company_id == line.company_id)
            line.taxes_id = fpos.map_tax(taxes, line.product_id, line.remision_id.partner_id) if fpos else taxes

    @api.depends('invoice_lines.invoice_id.state')
    def _compute_qty_invoiced(self):
        for line in self:
            qty = 0.0
            for inv_line in line.invoice_lines:
                if inv_line.invoice_id.state not in ['cancel']:
                    if inv_line.invoice_id.type == 'in_invoice':
                        qty += inv_line.uom_id._compute_quantity(inv_line.quantity, line.product_uom)
                    elif inv_line.invoice_id.type == 'in_refund':
                        qty -= inv_line.uom_id._compute_quantity(inv_line.quantity, line.product_uom)
            line.qty_invoiced = qty

    @api.depends('remision_id.state', 'move_ids.state')
    def _compute_qty_received(self):
        for line in self:
            if line.remision_id.state not in ['purchase', 'done']:
                line.qty_received = 0.0
                continue
            if line.product_id.type not in ['consu', 'product']:
                line.qty_received = line.product_qty
                continue
            total = 0.0
            for move in line.move_ids:
                if move.state == 'done':
                    if move.product_uom != line.product_uom:
                        total += move.product_uom._compute_quantity(move.product_uom_qty, line.product_uom)
                    else:
                        total += move.product_uom_qty
            line.qty_received = total

    @api.model
    def create(self, values):
        line = super(RemisionesLine, self).create(values)
        if line.remision_id.state == 'draft':
            line.remision_id._create_picking()
            msg = _("Extra line with %s ") % (line.product_id.display_name,)
            line.remision_id.message_post(body=msg)
        return line

    
    def write(self, values):
        orders = False
        if 'product_qty' in values:
            changed_lines = self.filtered(lambda x: x.remision_id.state == 'purchase')
            if changed_lines:
                orders = changed_lines.mapped('remision_id')
                for order in orders:
                    order_lines = changed_lines.filtered(lambda x: x.remision_id == order)
                    msg = ""
                    if any([values['product_qty'] < x.product_qty for x in order_lines]):
                        msg += "<b>" + _('The ordered quantity has been decreased. Do not forget to take it into account on your bills and receipts.') + '</b><br/>'
                    msg += "<ul>"
                    for line in order_lines:
                        msg += "<li> %s:" % (line.product_id.display_name,)
                        msg += "<br/>" + _("Ordered Quantity") + ": %s -> %s <br/>" % (line.product_qty, float(values['product_qty']),)
                        if line.product_id.type in ('product', 'consu'):
                            msg += _("Received Quantity") + ": %s <br/>" % (line.qty_received,)
                        msg += _("Billed Quantity") + ": %s <br/></li>" % (line.qty_invoiced,)
                    msg += "</ul>"
                    order.message_post(body=msg)
        # Update expectged date of corresponding moves
        if 'date_planned' in values:
            self.env['stock.move'].search([
                ('remisiones_line_id', 'in', self.ids), ('state', '!=', 'done')
            ]).write({'date_expected': values['date_planned']})
        result = super(RemisionesLine, self).write(values)
        if orders:
            orders._create_picking()
        return result

    

    id_line = fields.Integer(string='ID')
    name = fields.Text(string='Description')
    sequence = fields.Integer(string='Sequence', default=10)
    product_qty = fields.Float(string='Cantidad', default=1, digits=dp.get_precision('Product Unit of Measure'))
    date_planned = fields.Date(string='Fecha prevista', index=True)
    taxes_id = fields.Many2many('account.tax', string='Impuestos', domain=['|', ('active', '=', False), ('active', '=', True)])
    product_uom = fields.Many2one('product.uom', string='Unidad de medida')
    product_id = fields.Many2one('product.product', string='Producto', domain=[('purchase_ok', '=', True)], change_default=True)
    move_ids = fields.One2many('stock.move', 'remisiones_line_id', string='Reservation', readonly=True, ondelete='set null', copy=False)
    price_unit = fields.Float(string='Unit Price', digits=dp.get_precision('Precio'))
    remision_id = fields.Many2one('tjacdmx.remisiones', string='Reference', index=True)
    account_analytic_id = fields.Many2one('account.analytic.account', string='Cuenta analitica')
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')
    company_id = fields.Many2one('res.company', related='remision_id.company_id', string='Empresa', store=True, readonly=True)
    state = fields.Selection(related='remision_id.state', store=True)
    price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', store=True)
    price_tax = fields.Monetary(compute='_compute_amount', string='Impuesto', store=True)
    # invoice_lines = fields.One2many('account.invoice.line', 'purchase_line_id', string="Linea de factura", readonly=True, copy=False)
    qty_invoiced = fields.Float(string="Cantidad a facturar", digits=dp.get_precision('Product Unit of Measure'), store=True)
    qty_received = fields.Float(string="Cantidad a facturar", digits=dp.get_precision('Product Unit of Measure'), store=True)
    # procurement_ids = fields.One2many('procurement.order', 'purchase_line_id', string='Adquisiciones asociadas', copy=False)
    currency_id = fields.Many2one(related='remision_id.currency_id', store=True, string='Moneda', readonly=True)
    partner_id = fields.Many2one('res.partner', related='remision_id.partner_id', string='Proveedor', readonly=True, store=True)
    partida_producto = fields.Char(compute='_compute_partida', string='Partida')
    account_id = fields.Many2one('account.account', string='Cuenta', required=True)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        domain = {}
        fpos = ''
        company = 1
        currency = 34
        type = 'in_invoice'


        if not self.product_id:
            if type not in ('in_invoice', 'in_refund'):
                self.price_unit = 0.0
            domain['uom_id'] = []
        else:
            product = self.product_id
            self.name = product.partner_ref
            account = self.get_invoice_line_account(type, product, fpos, company)
            if account:
                self.account_id = account.id
            if type in ('in_invoice', 'in_refund'):
                if product.description_purchase:
                    self.name += '\n' + product.description_purchase
            else:
                if product.description_sale:
                    self.name += '\n' + product.description_sale

            if not self.product_uom or product.uom_id.category_id.id != self.product_uom.category_id.id:
                self.product_uom = product.uom_id.id
            domain['uom_id'] = [('category_id', '=', product.uom_id.category_id.id)]

            if company and currency:
                if self.product_uom and self.product_uom.id != product.uom_id.id:
                    self.price_unit = product.uom_id._compute_price(self.price_unit, self.product_uom)
        return {'domain': domain}
    # @api.v8
    def get_invoice_line_account(self, type, product, fpos, company):
        accounts = product.product_tmpl_id.get_product_accounts(fpos)
        if type in ('out_invoice', 'out_refund'):
            return accounts['income']
        return accounts['expense']

    # @api.one
    def _compute_partida(self):
        self.partida_producto=self.product_id.posicion_presupuestaria.partida_presupuestal


    
    def _create_stock_moves(self, picking):
        moves = self.env['stock.move']
        done = self.env['stock.move'].browse()
        for line in self:
            for val in line._prepare_stock_moves(picking):
                done += moves.create(val)
        return done
    

    
    def _get_stock_move_price_unit(self):
        self.ensure_one()
        line = self[0]
        order = line.remision_id
        price_unit = line.price_unit
        if line.taxes_id:
            price_unit = line.taxes_id.with_context(round=False).compute_all(
                price_unit, currency=line.remision_id.currency_id, quantity=1.0, product=line.product_id, partner=line.remision_id.partner_id
            )['total_excluded']
        if line.product_uom.id != line.product_id.uom_id.id:
            price_unit *= line.product_uom.factor / line.product_id.uom_id.factor
        if order.currency_id != order.company_id.currency_id:
            price_unit = order.currency_id.compute(price_unit, order.company_id.currency_id, round=False)
        return price_unit

    
    def _prepare_stock_moves(self, picking):
        """ Prepare the stock moves data for one order line. This function returns a list of
        dictionary ready to be used in stock.move's create()
        """
        self.ensure_one()
        res = []
        if self.product_id.type not in ['product', 'consu']:
            return res
        qty = 0.0
        price_unit = self._get_stock_move_price_unit()
        for move in self.move_ids.filtered(lambda x: x.state != 'cancel'):
            qty += move.product_qty
        template = {
            'name': self.name or '',
            'product_id': self.product_id.id,
            'product_uom': self.product_uom.id,
            'date': self.remision_id.date_remision,
            'date_expected': self.date_planned,
            'location_id': self.remision_id.partner_id.property_stock_supplier.id,
            'location_dest_id': self.remision_id._get_destination_location(),
            'picking_id': picking.id,
            'partner_id': self.remision_id.dest_address_id.id,
            'move_dest_id': False,
            'state': 'draft',
            'remisiones_line_id': self.id,
            'company_id': self.remision_id.company_id.id,
            'price_unit': price_unit,
            'picking_type_id': self.remision_id.picking_type_id.id,
            'group_id': self.remision_id.group_id.id,
            'procurement_id': False,
            'origin': self.remision_id.name,
            'route_ids': self.remision_id.picking_type_id.warehouse_id and [(6, 0, [x.id for x in self.remision_id.picking_type_id.warehouse_id.route_ids])] or [],
            'warehouse_id': self.remision_id.picking_type_id.warehouse_id.id,
        }
        # Fullfill all related procurements with this po line
        diff_quantity = self.product_qty - qty
        for procurement in self.procurement_ids.filtered(lambda p: p.state != 'cancel'):
            # If the procurement has some moves already, we should deduct their quantity
            sum_existing_moves = sum(x.product_qty for x in procurement.move_ids if x.state != 'cancel')
            existing_proc_qty = procurement.product_id.uom_id._compute_quantity(sum_existing_moves, procurement.product_uom)
            procurement_qty = procurement.product_uom._compute_quantity(procurement.product_qty, self.product_uom) - existing_proc_qty
            if float_compare(procurement_qty, 0.0, precision_rounding=procurement.product_uom.rounding) > 0 and float_compare(diff_quantity, 0.0, precision_rounding=self.product_uom.rounding) > 0:
                tmp = template.copy()
                tmp.update({
                    'product_uom_qty': min(procurement_qty, diff_quantity),
                    'move_dest_id': procurement.move_dest_id.id,  # move destination is same as procurement destination
                    'procurement_id': procurement.id,
                    'propagate': procurement.rule_id.propagate,
                })
                res.append(tmp)
                diff_quantity -= min(procurement_qty, diff_quantity)
        if float_compare(diff_quantity, 0.0,  precision_rounding=self.product_uom.rounding) > 0:
            template['product_uom_qty'] = diff_quantity
            res.append(template)
        return res

    
    def _create_stock_moves(self, picking):
        moves = self.env['stock.move']
        done = self.env['stock.move'].browse()
        for line in self:
            for val in line._prepare_stock_moves(picking):
                done += moves.create(val)
        return done

    
    def unlink(self):
        for line in self:
            if line.remision_id.state in ['purchase', 'done']:
                raise UserError(_('Cannot delete a purchase order line which is in state \'%s\'.') %(line.state,))
            for proc in line.procurement_ids:
                proc.message_post(body=_('remision line deleted.'))
            line.procurement_ids.filtered(lambda r: r.state != 'cancel').write({'state': 'exception'})
        return super(RemisionesLine, self).unlink()

    @api.model
    def _get_date_planned(self, seller, po=False):
        """Return the datetime value to use as Schedule Date (``date_planned``) for
           PO Lines that correspond to the given product.seller_ids,
           when ordered at `date_order_str`.

           :param browse_record | False product: product.product, used to
               determine delivery delay thanks to the selected seller field (if False, default delay = 0)
           :param browse_record | False po: purchase.order, necessary only if
               the PO line is not yet attached to a PO.
           :rtype: datetime
           :return: desired Schedule Date for the PO line
        """
        date_order = po.date_remision if po else self.remision_id.date_remision
        if date_order:
            return datetime.strptime(date_order, '%Y-%m-%d') + relativedelta(days=seller.delay if seller else 0)
        else:
            return datetime.today() + relativedelta(days=seller.delay if seller else 0)

    @api.onchange('product_id')
    def onchange_product_id(self):
        result = {}
        if not self.product_id:
            return result

        # Reset date, price and quantity since _onchange_quantity will provide default values
        self.date_planned = datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        self.price_unit = self.product_qty = 0.0
        self.product_uom = self.product_id.uom_po_id or self.product_id.uom_id
        result['domain'] = {'product_uom': [('category_id', '=', self.product_id.uom_id.category_id.id)]}

        product_lang = self.product_id.with_context(
            lang=self.partner_id.lang,
            partner_id=self.partner_id.id,
        )
        self.name = product_lang.display_name
        if product_lang.description_purchase:
            self.name += '\n' + product_lang.description_purchase

        fpos = self.remision_id.fiscal_position_id
        if self.env.uid == SUPERUSER_ID:
            company_id = self.env.user.company_id.id
            self.taxes_id = fpos.map_tax(self.product_id.supplier_taxes_id.filtered(lambda r: r.company_id.id == company_id))
        else:
            self.taxes_id = fpos.map_tax(self.product_id.supplier_taxes_id)

        self._suggest_quantity()
        self._onchange_quantity()

        return result

    @api.onchange('product_id')
    def onchange_product_id_warning(self):
        if not self.product_id:
            return
        warning = {}
        title = False
        message = False

        product_info = self.product_id

        if product_info.purchase_line_warn != 'no-message':
            title = _("Warning for %s") % product_info.name
            message = product_info.purchase_line_warn_msg
            warning['title'] = title
            warning['message'] = message
            if product_info.purchase_line_warn == 'block':
                self.product_id = False
            return {'warning': warning}
        return {}

    @api.onchange('product_qty', 'product_uom')
    def _onchange_quantity(self):
        if not self.product_id:
            return

        seller = self.product_id._select_seller(
            partner_id=self.partner_id,
            quantity=self.product_qty,
            date=self.remision_id.date_remision and self.remision_id.date_remision[:10],
            uom_id=self.product_uom)

        if seller or not self.date_planned:
            self.date_planned = self._get_date_planned(seller).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        if not seller:
            return

        price_unit = self.env['account.tax']._fix_tax_included_price_company(seller.price, self.product_id.supplier_taxes_id, self.taxes_id, self.company_id) if seller else 0.0
        if price_unit and seller and self.remision_id.currency_id and seller.currency_id != self.remision_id.currency_id:
            price_unit = seller.currency_id.compute(price_unit, self.remision_id.currency_id)

        if seller and self.product_uom and seller.product_uom != self.product_uom:
            price_unit = seller.product_uom._compute_price(price_unit, self.product_uom)

        self.price_unit = price_unit

    @api.onchange('product_qty')
    def _onchange_product_qty(self):
        if (self.state == 'purchase' or self.state == 'to approve') and self.product_id.type in ['product', 'consu'] and self.product_qty < self._origin.product_qty:
            warning_mess = {
                'title': _('Ordered quantity decreased!'),
                'message' : _('You are decreasing the ordered quantity!\nYou must update the quantities on the reception and/or bills.'),
            }
            return {'warning': warning_mess}

    def _suggest_quantity(self):
        '''
        Suggest a minimal quantity based on the seller
        '''
        if not self.product_id:
            return

        seller_min_qty = self.product_id.seller_ids\
            .filtered(lambda r: r.name == self.remision_id.partner_id)\
            .sorted(key=lambda r: r.min_qty)
        if seller_min_qty:
            self.product_qty = seller_min_qty[0].min_qty or 1.0
            self.product_uom = seller_min_qty[0].product_uom
        else:
            self.product_qty = 1.0