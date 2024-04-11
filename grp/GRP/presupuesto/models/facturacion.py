# -*- coding: utf-8 -*-

from datetime import datetime
from odoo import api, fields, models, _, tools
from odoo.exceptions import ValidationError,UserError
# from odoo.tools.translate import _
from num2words import num2words
from math import floor

def check_exist_doc(lista, doc):
    exist = -1
    for idx, item in enumerate(lista):
        if item['clase_documento'] == doc['clase_documento'] and \
            item['version'] == doc['version'] and \
            item['ejercicio'] == doc['ejercicio'] and \
            item['periodo'] == doc['periodo']:
            exist = idx
            break
    return exist

def calcular_precio_total(subtotal, impuestos, presupuestal=True):
    suma_imp = 0
    for imp in impuestos:
        amount = (imp.amount, 0)[presupuestal]
        if imp.amount > 0:
            amount = imp.amount
        suma_imp = suma_imp + (subtotal*amount/100)
    # raise ValidationError("Debug: %s" % (tot))
    return round(suma_imp + subtotal, 2)

class Factura(models.Model):
    _name = 'account.invoice'
    _description = u'Facturacion'
    _rec_name = 'fondo_economico'
    _inherit = ['mail.thread']
    
    @api.model
    def get_fondo(self):
        return self.env['presupuesto.fondo_economico'].search([('fuente_financiamiento','=','11')])
    @api.model
    def get_centro_g(self):
        return self.env['presupuesto.centro_gestor'].search([('clave','=','21A000')])
    @api.model
    def get_area_funci(self):
        return self.env['presupuesto.area_funcional'].search([('area_funcional','=','020400')])

    fondo_economico = fields.Many2one('presupuesto.fondo_economico',string='Fondo',  change_default=True, readonly=True,default=get_fondo)
    centro_gestor = fields.Many2one('presupuesto.centro_gestor',string='Centro gestor',  change_default=True, readonly=True,default=get_centro_g)
    area_funcional = fields.Many2one('presupuesto.area_funcional',string='Área funcional',  change_default=True, readonly=True,default=get_area_funci)
    clcs_count = fields.Integer(compute="_compute_clcs", string='CLC',copy=False, default=0)
    cla_line = fields.One2many('presupuesto.clc','id_factura',string='CLC')
    reference_provedor =fields.Char(string='Referencia de proveedor')
    fecha_pago =fields.Date(string='Fecha de pago')
    asientos_contables=fields.One2many('account.move.line', compute='_compute_o2m_field',string='Asientos')
    cuenta_prove = fields.Many2one('account.account',compute='_compute_cuenta_prov', string='Cuenta proveedor')
    cuenta_prove2 = fields.Many2one('account.account', string='Nueva cuenta',states={'draft_pre': [('readonly', False)],'draft': [('readonly', True)]})
    provision = fields.Boolean(u'Provisión', default=False)
    fecha_ejercido =fields.Date(string='Fecha de ejercido')
    type_invoice=fields.Boolean(string='Tipo de factura')
    stateinvoice=fields.Boolean(string='Status')

    state = fields.Selection([
            ('draft','Borrador'),
            ('draft_pre','Presupuesto'),
            ('open', 'Open'),
            ('clc', 'CLC'),
            ('in_payment', 'In Payment'),
            ('paid', 'Pago registrado'),
            ('paid_all', 'Pagado'),
            ('cancel', 'Cancelled'),
        ], string='Status', index=True, readonly=True, default='draft',
        track_visibility='onchange', copy=False,
        help=" * The 'Draft' status is used when a user is encoding a new and unconfirmed Invoice.\n"
             " * The 'CLC' status is used when it is sent to print CLC.\n"
             " * The 'Open' status is used when user creates invoice, an invoice number is generated. It stays in the open status till the user pays the invoice.\n"
             " * The 'In Payment' status is used when payments have been registered for the entirety of the invoice in a journal configured to post entries at bank reconciliation only, and some of them haven't been reconciled with a bank statement line yet.\n"
             " * The 'Paid' status is set automatically when the invoice is paid. Its related journal entries may or may not be reconciled.\n"
             " * The 'Cancelled' status is used when user cancel invoice.")

    invoice_line_ids = fields.One2many('account.invoice.line', 'invoice_id', string='Invoice Lines', oldname='invoice_line',
        readonly=True, states={'draft_pre': [('readonly', False)],'draft': [('readonly', False)]}, copy=True)
    date_invoice = fields.Date(string='Fecha factura',states={'draft_pre': [('readonly', False)],'draft': [('readonly', True)]}, copy=True)
    remision = fields.Many2one('tjacdmx.remisiones',string='remision')
    requicision = fields.Many2one('presupuesto.requisicion.compras.compromisos.line',string='requicision')
    origin_type = fields.Char(string='origen factura',compute='_compute_origin_fac')
    archivo_factura = fields.Binary(string='Factura digital')
    area_tb = fields.Many2one('areas.direccion', 'Area')
    vatios = fields.Float(string="kWh",required=False)
    litros = fields.Float(string="Litros",required=False)
    periodo_inicio = fields.Date(string='periodo inicio',required=False)
    periodo_fin = fields.Date(string='periodo fin',required=False)

    def toggle_provision(self):
        if(self.provision==True):
            self.provision=False
        else:
            self.provision=True

    @api.model
    def create(self, vals):
        result = super(Factura, self).create(vals)
        result.state = "draft"
        # Para realizar un pago la fatura debe tener state open
        return result
    
    
    def action_invoice_open(self):
        user_session = self.env['res.users'].browse(self.env.uid)
        permisos = self.env['presupuesto.permisos.presupuestales'].search([('usuario_id','=',user_session.id),('validar_factura_contable','=','open')])
        if(permisos):
            if(self.remision):
                remision_precess = self.env['tjacdmx.remisiones'].search([('id','=',self.remision.id)],limit=1)
                if(remision_precess.state == 'devengado' or remision_precess.state == 'lista_devengado'):
                    pass
                else:
                    raise ValidationError("La remisión origen aun no se encuentra devengada.")
            else:
                pass    
                
            # lots of duplicate calls to action_invoice_open, so we remove those already open
            to_open_invoices = self.filtered(lambda inv: inv.state != 'open')
            if to_open_invoices.filtered(lambda inv: inv.state not in ['proforma2', 'draft_pre','draft']):
                raise UserError(_("Invoice must be in draft or Pro-forma state in order to validate it."))
            to_open_invoices.action_date_assign()
            to_open_invoices.action_move_create()
            return to_open_invoices.invoice_validate()
        else:
            raise ValidationError("No cuenta con permisos para realizar esta operación, comuníquese con el administrador para revisar las operaciones autorizadas.")


    
    def action_move_create(self,date_remi=None):
        """ Creates invoice related analytics and financial move lines """
        account_move = self.env['account.move']

        for inv in self:
            if not inv.journal_id.sequence_id:
                raise UserError(_('Please define sequence on the journal related to this invoice.'))
            if not inv.invoice_line_ids:
                raise UserError(_('Please create some invoice lines.'))
            if inv.move_id:
                continue

            ctx = dict(self._context, lang=inv.partner_id.lang)

            if not inv.date_invoice:
                inv.with_context(ctx).write({'date_invoice': fields.Date.context_today(self)})
            company_currency = inv.company_id.currency_id

            # create move lines (one per invoice line + eventual taxes and analytic lines)
            iml = inv.invoice_line_move_line_get()
            iml += inv.tax_line_move_line_get()

            diff_currency = inv.currency_id != company_currency
            # create one move line for the total and possibly adjust the other lines amount
            total, total_currency, iml = inv.with_context(ctx).compute_invoice_totals(company_currency, iml)

            name = inv.name or '/'
            if inv.payment_term_id:
                totlines = inv.with_context(ctx).payment_term_id.with_context(currency_id=company_currency.id).compute(total, inv.date_invoice)[0]
                res_amount_currency = total_currency
                ctx['date'] = inv._get_currency_rate_date()
                for i, t in enumerate(totlines):
                    if inv.currency_id != company_currency:
                        amount_currency = company_currency.with_context(ctx).compute(t[1], inv.currency_id)
                    else:
                        amount_currency = False

                    # last line: add the diff
                    res_amount_currency -= amount_currency or 0
                    if i + 1 == len(totlines):
                        amount_currency += res_amount_currency

                    cuanta_id = self.env['res.partner'].search([('id','=', self.partner_id.id)])
                    cuanta_id_id = self.env['account.account'].search([('id','=', cuanta_id.property_account_payable_id.id)])
                    if(self.cuenta_prove2):
                        cuenta_proveedor=self.cuenta_prove2
                    else:
                        cuenta_proveedor=cuanta_id_id
                    #raise ValidationError("campo XD:")
                    self.write({'account_id': cuenta_proveedor.id})
                    iml.append({
                        'type': 'dest',
                        'name': name,
                        'price': t[1],
                        'account_id': cuenta_proveedor.id,
                        'date_maturity': t[0],
                        'amount_currency': diff_currency and amount_currency,
                        'currency_id': diff_currency and inv.currency_id.id,
                        'invoice_id': inv.id
                    })
            else:
                cuanta_id = self.env['res.partner'].search([('id','=', self.partner_id.id)])
                cuanta_id_id = self.env['account.account'].search([('id','=', cuanta_id.property_account_payable_id.id)])
                if(self.cuenta_prove2):
                    cuenta_proveedor=self.cuenta_prove2
                else:
                    cuenta_proveedor=cuanta_id_id
                #raise ValidationError("campo XD2: %s" % (cuenta_proveedor.id))
                self.write({'account_id': cuenta_proveedor.id})
                iml.append({
                    'type': 'dest',
                    'name': name,
                    'price': total,
                    'account_id': cuenta_proveedor.id,
                    'date_maturity': inv.date_due,
                    'amount_currency': diff_currency and total_currency,
                    'currency_id': diff_currency and inv.currency_id.id,
                    'invoice_id': inv.id
                })
            part = self.env['res.partner']._find_accounting_partner(inv.partner_id)
            line = [(0, 0, self.line_get_convert(l, part.id)) for l in iml]
            line = inv.group_lines(iml, line)

            journal = inv.journal_id.with_context(ctx)
            line = inv.finalize_invoice_move_lines(line)

            date = inv.date or inv.date_invoice
            move_vals = {
                'ref': inv.reference,
                'line_ids': line,
                'journal_id': journal.id,
                'date': date,
                'narration': inv.comment,
            }
            ctx['company_id'] = inv.company_id.id
            ctx['invoice'] = inv
            ctx_nolang = ctx.copy()
            ctx_nolang.pop('lang', None)
            move = account_move.with_context(ctx_nolang).create(move_vals)
            # Pass invoice in context in method post: used if you want to get the same
            # account move reference when creating the same invoice after a cancelled one:
            move.post()
            # make the invoice point to that move
            vals = {
                'move_id': move.id,
                'date': date,
                'move_name': move.name,
            }
            inv.with_context(ctx).write(vals)
        return True

    
    def _compute_cuenta_prov(self):
        cuanta_id = self.env['res.partner'].search([('id','=', self.partner_id.id)])
        cuanta_id_id = self.env['account.account'].search([('id','=', cuanta_id.property_account_payable_id.id)])
        self.cuenta_prove = cuanta_id_id

    
    def _compute_o2m_field(self):
        related_ids = []
        moves = self.env['account.move.line'].search([('move_id','=',self.move_id.id)])
        self.asientos_contables = moves

    def _compute_clcs(self):
        clcs = self.env['presupuesto.clc'].search([('id_factura','=',self.id)])
        self.clcs_count = len(clcs)
     
    def _compute_origin_fac(self):
        index=self.origin[0:2]
        self.origin_type = index

    
    def print_request_payment(self):
        return self.env['report'].get_action([], 'reportes.purchase_solicitud_pago')

    
    def status_momento_conta(self):
        action = self.env.ref('account.action_move_journal_line')
        result = action.read()[0]
        result.pop('id', None)
        result['context'] = {}
        asientos_ids = self.id
        if asientos_ids > 1:
            result['domain'] = "[('name','=', '%s')]" % (self.number)
        elif asientos_ids == 1:
            raise ValidationError("No se encontro momento para esta factura '%s' " % (self.number))

        return result


    
    def new_clc(self):
        action = self.env.ref('presupuestos.action_presupuesto_clc')
        result = action.read()[0]
        result['context'] = {}
        search_clc_active = self.env['presupuesto.clc'].search([('id_factura','=',self.id)], limit=1)
        if (search_clc_active):
            result['domain'] = "[('id_factura','=', %s)]" % (self.id)
        else:
            res = self.env.ref('presupuestos.view_tjacdmx_clc_form', False)
            result['context']['default_proveedor_c'] = self.partner_id.id
            result['context']['default_proveedor_c_id_fac'] = self.id
            result['views'] = [(res and res.id or False, 'form')]
            result['proveedor'] = self.partner_id.id

        return result


    
    def valida_fac(self):
        user_session = self.env['res.users'].browse(self.env.uid)
        permisos = self.env['presupuesto.permisos.presupuestales'].search([('usuario_id','=',user_session.id),('validar_factura_presupuestal','=','open')])
        if(permisos):
            self.write({'stateinvoice': 'True'})
            self.write({'state': 'draft_pre'})
        else:
            raise ValidationError("No cuenta con permisos para realizar esta operación, comuníquese con el administrador para revisar las operaciones autorizadas.")


    
    def cancel_ejercido_compra(self):
        user_session = self.env['res.users'].browse(self.env.uid)
        permisos = self.env['presupuesto.permisos.presupuestales'].search([('usuario_id','=',user_session.id),('cancelar_ejercido_presupuestal','=','open')])
        if(permisos):
            purchase_order = self.env['purchase.order'].search([('name','=',self.origin)], limit=1)
            return {
                'name': _("Cancelar documento Ejercido"),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'cancel_budget.wizard',
                'target': 'new',
                'type': 'ir.actions.act_window',
                'context': {'tipo': 'COPE','compra_id':purchase_order.id,'invoice_id':self.id}
            } 
        else:
            raise ValidationError("No cuenta con permisos para realizar esta operación, comuníquese con el administrador para revisar las operaciones autorizadas.")

    
    def cancel_ejercido_rem_compra(self):
        user_session = self.env['res.users'].browse(self.env.uid)
        permisos = self.env['presupuesto.permisos.presupuestales'].search([('usuario_id','=',user_session.id),('cancelar_ejercido_presupuestal','=','open')])
        if(permisos):
            purchase_order = self.env['purchase.order'].search([('name','=',self.origin)], limit=1)
            return {
                'name': _("Cancelar documento Ejercido"),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'cancel_budget_remi.wizard',
                'target': 'new',
                'type': 'ir.actions.act_window',
                'context': {'remision': self.remision.id,'requi_id': self.requicision.id,'invoice_id':self.id,'momento':'ejercido'}
            } 
        else:
            raise ValidationError("No cuenta con permisos para realizar esta operación, comuníquese con el administrador para revisar las operaciones autorizadas.")


    def cancel_pago_compra(self):
        user_session = self.env['res.users'].browse(self.env.uid)
        permisos = self.env['presupuesto.permisos.presupuestales'].search([('usuario_id','=',user_session.id),('cancelar_pago_presupuestal','=','open')])
        if(permisos):
            purchase_order = self.env['purchase.order'].search([('name','=',self.origin)], limit=1)
            return {
                'name': _("Cancelar documento Pagado"),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'cancel_budget.wizard',
                'target': 'new',
                'type': 'ir.actions.act_window',
                'context': {'tipo': 'COPP','compra_id':purchase_order.id,'invoice_id':self.id}
            } 
        else:
            raise ValidationError("No cuenta con permisos para realizar esta operación, comuníquese con el administrador para revisar las operaciones autorizadas.")
    

    def cancel_pago_rem_compra(self):
        user_session = self.env['res.users'].browse(self.env.uid)
        permisos = self.env['presupuesto.permisos.presupuestales'].search([('usuario_id','=',user_session.id),('cancelar_pago_presupuestal','=','open')])
        if(permisos):
            purchase_order = self.env['purchase.order'].search([('name','=',self.origin)], limit=1)
            return {
                'name': _("Cancelar documento Pagado"),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'cancel_budget_remi.wizard',
                'target': 'new',
                'type': 'ir.actions.act_window',
                'context': {'remision': self.remision.id,'requi_id': self.requicision.id,'invoice_id':self.id,'momento':'pagado'}
            } 
        else:
            raise ValidationError("No cuenta con permisos para realizar esta operación, comuníquese con el administrador para revisar las operaciones autorizadas.")
    


    
    def button_open_pagado_window(self):
        user_session = self.env['res.users'].browse(self.env.uid)
        permisos = self.env['presupuesto.permisos.presupuestales'].search([('usuario_id','=',user_session.id),('devengado','=','open')])
        ctrl_periodo = self.env['control.periodos.wizard']
        obj_date_purchase = self.env['purchase.order'].search([('name','=',self.origin)], limit=1)
        search_clc_active = self.env['presupuesto.clc'].search([('id_factura','=',self.id)], limit=1)

        if(permisos):
            return {
                'name': _("Pagar"),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'momentos_presupuestales.wizard',
                'target': 'new',
                'type': 'ir.actions.act_window',
                'context': {'compra': obj_date_purchase.id,'factura': self.id,'fecha': '','momento': str('pagado'),'provision': 'False','tipo_contrato':obj_date_purchase.tipo_contrato.id}
            } 
        else:
            raise ValidationError("No cuenta con permisos para realizar esta operación, comuníquese con el administrador para revisar las operaciones autorizadas.")
    
    def button_open_pagado_remi_window(self):
        user_session = self.env['res.users'].browse(self.env.uid)
        permisos = self.env['presupuesto.permisos.presupuestales'].search([('usuario_id','=',user_session.id),('devengado','=','open')])
        ctrl_periodo = self.env['control.periodos.wizard']
        obj_date_purchase = self.env['purchase.order'].search([('name','=',self.origin)], limit=1)
        search_clc_active = self.env['presupuesto.clc'].search([('id_factura','=',self.id)], limit=1)

        if(permisos):
            return {
                'name': _("Pagar"),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'momentos_presupuestales_remi.wizard',
                'target': 'new',
                'type': 'ir.actions.act_window',
                'context': {'remision': self.remision.id,'factura': self.id,'fecha': '','momento': str('pagado'),'provision': 'False',}
            } 
        else:
            raise ValidationError("No cuenta con permisos para realizar esta operación, comuníquese con el administrador para revisar las operaciones autorizadas.")

    
    def pago_compra(self):
        user_session = self.env['res.users'].browse(self.env.uid)
        permisos = self.env['presupuesto.permisos.presupuestales'].search([('usuario_id','=',user_session.id),('pagado','=','open')])
        ctrl_periodo = self.env['control.periodos.wizard']
        
        if(not ctrl_periodo.get_is_cerrado(self.fecha_pago)
         and permisos):
            obj_documento = self.env['presupuesto.documento']
            factura = self.invoice_line_ids
            obj_date_purchase = self.env['purchase.order'].search([('name','=',self.origin)], limit=1)
            date_pay=obj_date_purchase.date_order
            documentos = []
            amount = 0
            version = self.env['presupuesto.version'].search([], limit=1)
            cls_doc = self.env['presupuesto.clase_documento'].search([('tipo_documento','=','PAGADO')], limit=1)
            fecha = datetime.strptime(self.fecha_pago, '%Y-%m-%d') if self.fecha_pago else datetime.today()
            fecha_origen = datetime.strptime(date_pay, '%Y-%m-%d %H:%M:%S') if date_pay else datetime.today()
            # La fecha origen pude venir de una compra de un mes anterior por lo que se hace referencia a una comrpa origen 
            if(obj_date_purchase.referencia_compra 
                and obj_date_purchase.type_purchase == 'compra' 
                and obj_date_purchase.importe_comprometido == 0):
                fecha_origen = datetime.strptime(obj_date_purchase.referencia_compra.date_order, '%Y-%m-%d %H:%M:%S')

            
            for invoice_item in factura:
                producto = invoice_item.product_id
                importe_presupuestal = calcular_precio_total(invoice_item.price_subtotal, invoice_item.invoice_line_tax_ids)
                importe_pagar = calcular_precio_total(invoice_item.price_subtotal, invoice_item.invoice_line_tax_ids, False)
                documento = {
                    'clase_documento': cls_doc.id,
                    'version': version.id,
                    'ejercicio': fecha.year,
                    'periodo': fecha.month,
                    'periodo_origen': fecha_origen.month,
                    'fecha_contabilizacion': fecha.strftime('%Y-%m-%d %H:%M:%S'),
                    'fecha_documento': fecha.strftime('%Y-%m-%d %H:%M:%S'),
                    'detalle_documento_ids': [],
                    # 'referencia_pago': self.id,
                    'compra_id': obj_date_purchase.id
                }
                detalle_doc = [0, False,
                    {
                        'centro_gestor': self.centro_gestor.id,
                        'area_funcional': self.area_funcional.id,
                        'fondo_economico': self.fondo_economico.id,
                        'posicion_presupuestaria': producto.posicion_presupuestaria.id,
                        'importe': importe_presupuestal,
                        'momento_contable': 'PAGADO'
                    }
                ]
                doc_idx = check_exist_doc(documentos, documento)
                if doc_idx > -1:
                    documentos[doc_idx]['detalle_documento_ids'].append(detalle_doc)
                else:
                    documento['detalle_documento_ids'].append(detalle_doc)
                    documentos.append(documento)   
                amount += importe_pagar
            tot=self.amount_total
            #raise ValidationError("campo: %s / calculo %s" % (tot,floor(amount)))
            # if (amount - self.amount_total == 0.0 ):
            for doc in documentos:
                obj_documento.create(doc)
            sale_search = self.env['purchase.order'].search([('name','=',self.origin)], limit=1)
            tjacdmx_update_status_mc = "UPDATE purchase_order SET status_account_move='PAGADO' WHERE id=%s" % (sale_search.id)
            self.env.cr.execute(tjacdmx_update_status_mc)
            self.write({'state': "paid_all"})
            # else:
            #     raise ValidationError('El monto a pagar es diferente al monto de la factura, el monto debe ser igual al de la factura %s -> %s' % (amount, tot))
        else:
            raise ValidationError("No cuenta con permisos para realizar esta operación, comuníquese con el administrador para revisar las operaciones autorizadas.")
            
    
    def button_open_ejercido_window(self):
        user_session = self.env['res.users'].browse(self.env.uid)
        permisos = self.env['presupuesto.permisos.presupuestales'].search([('usuario_id','=',user_session.id),('ejercido','=','open')])
        ctrl_periodo = self.env['control.periodos.wizard']
        obj_date_purchase = self.env['purchase.order'].search([('name','=',self.origin)], limit=1)
        search_clc_active = self.env['presupuesto.clc'].search([('id_factura','=',self.id)], limit=1)
        if(self.provision==True):
            fecha = datetime.strptime(self.fecha_ejercido, '%Y-%m-%d') if self.fecha_ejercido else datetime.today()
        else:
            fecha = datetime.strptime(search_clc_active.fecha_expedicion, '%Y-%m-%d') if search_clc_active.fecha_expedicion else datetime.today()

        if(permisos):
            return {
                'name': _("Ejercer"),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'momentos_presupuestales.wizard',
                'target': 'new',
                'type': 'ir.actions.act_window',
                'context': {'compra': obj_date_purchase.id,'factura': self.id,'fecha': str(fecha),'momento': str('ejercido'),'provision': self.provision,'tipo_contrato':obj_date_purchase.tipo_contrato.id}
            } 
        else:
            raise ValidationError("No cuenta con permisos para realizar esta operación, comuníquese con el administrador para revisar las operaciones autorizadas.")

    
    def button_open_ejercido_remi_window(self):
        user_session = self.env['res.users'].browse(self.env.uid)
        permisos = self.env['presupuesto.permisos.presupuestales'].search([('usuario_id','=',user_session.id),('ejercido','=','open')])
        ctrl_periodo = self.env['control.periodos.wizard']
        search_clc_active = self.env['presupuesto.clc'].search([('id_factura','=',self.id)], limit=1)
        if(self.provision==True):
            fecha = datetime.strptime(self.fecha_ejercido, '%Y-%m-%d') if self.fecha_ejercido else datetime.today()
        else:
            fecha = datetime.strptime(search_clc_active.fecha_expedicion, '%Y-%m-%d') if search_clc_active.fecha_expedicion else datetime.today()
        if(permisos):
            return {
                'name': _("Ejercer"),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'momentos_presupuestales_remi.wizard',
                'target': 'new',
                'type': 'ir.actions.act_window',
                'context': {'remision': self.remision.id,'factura': self.id,'fecha': str(fecha),'momento': str('ejercido'),'provision': self.provision,}
            } 
        else:
            raise ValidationError("No cuenta con permisos para realizar esta operación, comuníquese con el administrador para revisar las operaciones autorizadas.")

    
    def print_clc(self):
        user_session = self.env['res.users'].browse(self.env.uid)
        permisos = self.env['presupuesto.permisos.presupuestales'].search([('usuario_id','=',user_session.id),('ejercido','=','open')])
        
        search_clc_active = self.env['presupuesto.clc'].search([('id_factura','=',self.id)], limit=1)
        ctrl_periodo = self.env['control.periodos.wizard']
        if(self.provision==True):
            fecha_ctrl = datetime.strptime(self.fecha_ejercido, '%Y-%m-%d') if self.fecha_ejercido else datetime.today()
        else:
            fecha_ctrl = datetime.strptime(search_clc_active.fecha_expedicion, '%Y-%m-%d') if search_clc_active.fecha_expedicion else datetime.today()


        if(not ctrl_periodo.get_is_cerrado(fecha_ctrl)
         and permisos):
            datas = {}
            search_clc_active = self.env['presupuesto.clc'].search([('id_factura','=',self.id)], limit=1)
            if (search_clc_active):
                obj_date_purchase = self.env['purchase.order'].search([('name','=',self.origin)], limit=1)
                date_pay=obj_date_purchase.date_order
                documentos = []
                obj_documento = self.env['presupuesto.documento']
                version = self.env['presupuesto.version'].search([], limit=1)
                cls_doc = self.env['presupuesto.clase_documento'].search([('tipo_documento','=','EJERCIDO')], limit=1)
                if(self.provision==True):
                    fecha = datetime.strptime(self.fecha_ejercido, '%Y-%m-%d') if self.fecha_ejercido else datetime.today()
                else:
                    fecha = datetime.strptime(search_clc_active.fecha_expedicion, '%Y-%m-%d') if search_clc_active.fecha_expedicion else datetime.today()

                fecha_origen = datetime.strptime(date_pay, '%Y-%m-%d %H:%M:%S') if date_pay else datetime.today()
                # La fecha origen pude venir de una compra de un mes anterior por lo que se hace referencia a una comrpa origen 
                if(obj_date_purchase.referencia_compra 
                    and obj_date_purchase.type_purchase == 'compra' 
                    and obj_date_purchase.importe_comprometido == 0):
                    fecha_origen = datetime.strptime(obj_date_purchase.referencia_compra.date_order, '%Y-%m-%d %H:%M:%S')

                for invoice_item in self.invoice_line_ids:
                    producto = invoice_item.product_id
                    documento = {
                        'clase_documento': cls_doc.id,
                        'version': version.id,
                        'ejercicio': fecha.year,
                        'periodo': fecha.month,
                        'fecha_contabilizacion': fecha.strftime("%Y-%m-%d"),
                        'fecha_documento': fecha.strftime("%Y-%m-%d"),
                        'periodo_origen': fecha_origen.month,
                        'detalle_documento_ids': [],
                        'referencia_factura': self.id,
                        'compra_id': obj_date_purchase.id
                    }
                    detalle_doc = [0, False,
                        {
                            'centro_gestor': self.centro_gestor.id,
                            'area_funcional': self.area_funcional.id,
                            'fondo_economico': self.fondo_economico.id,
                            'posicion_presupuestaria': producto.posicion_presupuestaria.id,
                            'importe': calcular_precio_total(invoice_item.price_subtotal, invoice_item.invoice_line_tax_ids),
                            'momento_contable': 'EJERCIDO'
                        }
                    ]
                    doc_idx = check_exist_doc(documentos, documento)
                    if doc_idx > -1:
                        documentos[doc_idx]['detalle_documento_ids'].append(detalle_doc)
                    else:
                        documento['detalle_documento_ids'].append(detalle_doc)
                        documentos.append(documento)
                for doc in documentos:
                    obj_documento.create(doc)
                self.write({'state': "clc"})
                sale_search = self.env['purchase.order'].search([('name','=',self.origin)], limit=1)
                tjacdmx_update_status_mc = "UPDATE purchase_order SET status_account_move='EJERCIDO' WHERE id=%s" % (sale_search.id)
                self.env.cr.execute(tjacdmx_update_status_mc)
                cantidad = self.amount_total
                cantidad = '{0:.2f}'.format(float(cantidad))
                importe = cantidad.split('.')[0]
                centavos = cantidad.split('.')[1]
                importe = (num2words(importe, lang='es').split(' punto ')[0]).upper()
                moneda = ' pesos '.upper()
                leyenda = '/100 m.n.'.upper()
                total_letra = importe + moneda + centavos + leyenda
                # asiento_contable=obj_date_purchase.line_asientos_contables[0].id
                # obj_line_ac = self.env['account.move.line'].search([('move_id','=',asiento_contable)], limit=2)
                datas['prov_nombre'] = search_clc_active.proveedor.name
                datas['prov_rfc'] = search_clc_active.rfc
                datas['prov_fecha_expedicion'] = search_clc_active.fecha_expedicion
                datas['prov_banco'] = search_clc_active.banco
                datas['prov_no_cuenta'] = search_clc_active.no_cuenta
                datas['prov_no_poliza'] = search_clc_active.no_poliza
                datas['prov_no_clc'] = search_clc_active.no_clc
                datas['prov_clave_presu'] = search_clc_active.clave_presu
                datas['prov_importe_letra'] = total_letra
                datas['reference_provedor'] = self.reference_provedor
                #linea de momento contable abono
                cuentas = []
                suma_cargo = 0
                suma_abono = 0
                count = 0
                get_move= self.env['account.move'].search([('name', '=', self.number)])
                docs = self.env['account.move.line'].search([('move_id', '=', get_move.id)])
                #obtener las cuentas
                for el in docs:
                    #obtener el id de la cuenta
                    account = el.account_id
                    i = account.code.split('.')
                    #buscar los nombres de las cuentas
                    cuenta_nombre = self.env['account.account'].search([('code', '=ilike', i[0] + '.' + '%')])[0].name
                    subcuenta_nombre = self.env['account.account'].search([('code', '=like', i[0] + '.' + i[1] + '.' + '%')])[0].name
                    suma_cargo = suma_cargo + el.debit
                    suma_abono = suma_abono + el.credit
                    #crear un arreglo con todos los elementos a mostrar
                    cuenta = {
                        'cuenta': i[0],             #cuenta               [0]
                        'subcuenta': i[1],          #sub cuenta           [1]
                        'cargo': '{0:,.2f}'.format(float(el.debit)),          #cargo                [5]
                        'abono': '{0:,.2f}'.format(float(el.credit)),         #abono                [6]
                    }
                    #raise ValidationError("Debug: %s" % (cuenta))
                    if len(i) > 2:
                        subsubcuenta_nombre = self.env['account.account'].search(
                            [('code', '=like', i[0] + '.' + i[1] + '.' + i[2] + '%')]
                            )[0].name
                        cuenta.update({'subsubcuenta': i[2], 'subsubcuenta_nombre': subsubcuenta_nombre})
                    if len(i) >= 3:
                        subsubsubcuenta_nombre = self.env['account.account'].search(
                            [('code', '=', account.code)]
                            )[0].name
                    if len(i) <= 3:
                        cuenta.update({'subsubsubcuenta': i[2], 'subsubsubcuenta_nombre': subsubsubcuenta_nombre})
                    else:
                        cuenta.update({'subsubsubcuenta': i[3], 'subsubsubcuenta_nombre': subsubsubcuenta_nombre})
                    cuentas.append(cuenta)
                    lineas = []
                    for cuenta in cuentas:
                        for count in range(1,5):
                            if count == 1:
                                insert = {
                                'nombre': cuenta_nombre,
                                'cuenta': cuenta.get('cuenta'),
                                'subcuenta': '',
                                'subsubcuenta': '',
                                'subsubsubcuenta': '',
                                'parcial': '',
                                'cargo': cuenta.get('cargo'),
                                'abono': cuenta.get('abono'),
                                }
                                lineas.append(insert)
                            if count == 2:
                                insert = {
                                'nombre': subcuenta_nombre,
                                'cuenta': '',
                                'subcuenta': cuenta.get('subcuenta'),
                                'subsubcuenta': '',
                                'subsubsubcuenta': '',
                                'parcial': cuenta.get('abono') if (cuenta.get('abono') != 0.0) else cuenta.get('cargo'),
                                'cargo': '',
                                'abono': '',
                                }
                                lineas.append(insert)
                            if count == 3:
                                insert = {
                                'nombre': cuenta.get('subsubcuenta_nombre'),
                                'cuenta': '',
                                'subcuenta': '',
                                'subsubcuenta': cuenta.get('subsubcuenta'),
                                'subsubsubcuenta': '',
                                'parcial': '',
                                'cargo': '',
                                'abono': '',
                                }
                                lineas.append(insert)
                            if count == 4:
                                insert = {
                                'nombre': cuenta.get('subsubsubcuenta_nombre'),
                                'cuenta': '',
                                'subcuenta': '',
                                'subsubcuenta': '',
                                'subsubsubcuenta': cuenta.get('subsubsubcuenta'),
                                'parcial': cuenta.get('abono') if (cuenta.get('abono') != 0.0) else cuenta.get('cargo'),
                                'cargo': '',
                                'abono': '',
                                }
                                lineas.append(insert)
                                count += 1
                datas['lineas_cuenta'] = lineas
                datas['suma_abono'] = suma_abono
                datas['suma_cargo'] = suma_cargo
                #raise ValidationError("%s" % (datas))
                return self.env['report'].get_action([], 'reportes.reporte_clc', data=datas)
            else:
                raise ValidationError("No se genero CLC para esta factura")
        else:
            raise ValidationError("No cuenta con permisos para realizar esta operación, comuníquese con el administrador para revisar las operaciones autorizadas.")

    
    def print_clc_before(self):
        datas = {}
        search_clc_active = self.env['presupuesto.clc'].search([('id_factura','=',self.id)], limit=1)
        if (search_clc_active):
            obj_date_purchase = self.env['purchase.order'].search([('name','=',self.origin)], limit=1)
            date_pay=obj_date_purchase.date_order
            #raise ValidationError("%s" % (date_pay))
            documentos = []
            obj_documento = self.env['presupuesto.documento']
            version = self.env['presupuesto.version'].search([], limit=1)
            cls_doc = self.env['presupuesto.clase_documento'].search([('tipo_documento','=','EJERCIDO')], limit=1)
            fecha = datetime.strptime(date_pay, '%Y-%m-%d %H:%M:%S') if date_pay else datetime.today()
            cantidad = self.amount_total
            cantidad = '{0:.2f}'.format(float(cantidad))
            importe = cantidad.split('.')[0]
            centavos = cantidad.split('.')[1]
            importe = (num2words(importe, lang='es').split(' punto ')[0]).upper()
            moneda = ' pesos '.upper()
            leyenda = '/100 m.n.'.upper()
            total_letra = importe + moneda + centavos + leyenda
            # asiento_contable=obj_date_purchase.line_asientos_contables[0].id


            datas['prov_nombre'] = search_clc_active.proveedor.name
            datas['prov_rfc'] = search_clc_active.rfc
            datas['prov_fecha_expedicion'] = search_clc_active.fecha_expedicion
            datas['prov_banco'] = search_clc_active.banco
            datas['prov_no_cuenta'] = search_clc_active.no_cuenta
            datas['prov_no_poliza'] = search_clc_active.no_poliza
            datas['prov_no_clc'] = search_clc_active.no_clc
            datas['prov_clave_presu'] = search_clc_active.clave_presu
            datas['prov_importe_letra'] = total_letra
            datas['reference_provedor'] = self.reference_provedor
            #linea de momento contable abono
            cuentas = []
            suma_cargo = 0
            suma_abono = 0
            count = 0
            get_move= self.env['account.move'].search([('name', '=', self.number)])
            docs = self.env['account.move.line'].search([('move_id', '=', get_move.id)])
            #raise ValidationError("Debug: %s" % (docs[0].account_id))
            #obtener las cuentas
            for el in docs:
                #obtener el id de la cuenta
                account = el.account_id
                i = account.code.split('.')

                #buscar los nombres de las cuentas
                cuenta_nombre = self.env['account.account'].search([('code', '=ilike', i[0] + '.' + '%')])[0].name
                subcuenta_nombre = self.env['account.account'].search([('code', '=like', i[0] + '.' + i[1] + '.' + '%')])[0].name
                suma_cargo = suma_cargo + el.debit
                suma_abono = suma_abono + el.credit
                #crear un arreglo con todos los elementos a mostrar
                cuenta = {
                    'cuenta': i[0],             #cuenta               [0]
                    'subcuenta': i[1],          #sub cuenta           [1]
                    'cargo': '{0:,.2f}'.format(float(el.debit)),          #cargo                [5]
                    'abono': '{0:,.2f}'.format(float(el.credit)),         #abono                [6]
                }
                #raise ValidationError("Debug: %s" % (cuenta))
                if len(i) > 2:
                    subsubcuenta_nombre = self.env['account.account'].search(
                        [('code', '=like', i[0] + '.' + i[1] + '.' + i[2] + '%')]
                        )[0].name
                    cuenta.update({'subsubcuenta': i[2], 'subsubcuenta_nombre': subsubcuenta_nombre})
                if len(i) >= 3:
                    subsubsubcuenta_nombre = self.env['account.account'].search(
                        [('code', '=', account.code)]
                        )[0].name
                    cuenta.update({'subsubsubcuenta': i[3], 'subsubsubcuenta_nombre': subsubsubcuenta_nombre})
                cuentas.append(cuenta)

                lineas = []
                
                for cuenta in cuentas:
                    for count in range(1,5):
                        if count == 1:
                            insert = {
                            'nombre': cuenta_nombre,
                            'cuenta': cuenta.get('cuenta'),
                            'subcuenta': '',
                            'subsubcuenta': '',
                            'subsubsubcuenta': '',
                            'parcial': '',
                            'cargo': cuenta.get('cargo'),
                            'abono': cuenta.get('abono'),
                            }
                            lineas.append(insert)
                        if count == 2:
                            insert = {
                            'nombre': subcuenta_nombre,
                            'cuenta': '',
                            'subcuenta': cuenta.get('subcuenta'),
                            'subsubcuenta': '',
                            'subsubsubcuenta': '',
                            'parcial': cuenta.get('abono') if (cuenta.get('abono') != 0.0) else cuenta.get('cargo'),
                            'cargo': '',
                            'abono': '',
                            }
                            lineas.append(insert)
                        if count == 3:
                            insert = {
                            'nombre': cuenta.get('subsubcuenta_nombre'),
                            'cuenta': '',
                            'subcuenta': '',
                            'subsubcuenta': cuenta.get('subsubcuenta'),
                            'subsubsubcuenta': '',
                            'parcial': '',
                            'cargo': '',
                            'abono': '',
                            }
                            lineas.append(insert)
                        if count == 4:
                            insert = {
                            'nombre': cuenta.get('subsubsubcuenta_nombre'),
                            'cuenta': '',
                            'subcuenta': '',
                            'subsubcuenta': '',
                            'subsubsubcuenta': cuenta.get('subsubsubcuenta'),
                            'parcial': cuenta.get('abono') if (cuenta.get('abono') != 0.0) else cuenta.get('cargo'),
                            'cargo': '',
                            'abono': '',
                            }
                            lineas.append(insert)
                            count += 1

        
            datas['lineas_cuenta'] = lineas
            datas['suma_abono'] = suma_abono
            datas['suma_cargo'] = suma_cargo
            #raise ValidationError("%s" % (datas))
            return self.env['report'].get_action([], 'reportes.reporte_clc', data=datas)
        else:
            raise ValidationError("No se genero CLC para esta factura")


        

    
    def importe_con_letra(self, cantidad):
        cantidad = '{0:.2f}'.format(float(cantidad))
        importe = cantidad.split('.')[0]
        centavos = cantidad.split('.')[1]
        importe = (num2words(importe, lang='es').split(' punto ')[0]).upper()
        moneda = ' pesos '.upper()
        leyenda = '/100 m.n.'.upper()
        return importe + moneda + centavos + leyenda


class account_abstract_payment_iner(models.Model):
    _inherit = "account.payment"
    referencia =fields.Text(string='Referencias')
    @api.model
    def create(self, vals):
        result = super(account_abstract_payment_iner, self).create(vals)
        factura = result.invoice_ids
        result.invoice_ids.state = "open" # Para realizar un pago la fatura debe tener state open
        return result

class FacturaLinea(models.Model):
    _name = "account.invoice.line"
    _description = 'Facturas linea'
    _inherit = ['mail.thread']

    invoice_id = fields.Many2one('account.invoice',string='Fondo')
    purchase_line_id = fields.Many2one('procurement.order.line',string='Fondo')
    partida_presupuestal=fields.Char(string='Partida', compute='_compute_partida')
    line_remision_id=fields.Integer(string='line_id_remi')
    invoice_line_tax_ids = fields.Many2many('account.tax','account_invoice_line_tax', 'invoice_line_id', 'tax_id',string='Taxes')
    vatios = fields.Float(string="kWh",required=False)
    litros = fields.Float(string="Litros",required=False)

    
    def _compute_partida(self):
        search_partida = self.env['product.template'].search([('id','=',self.product_id.product_tmpl_id.id)])
        self.partida_presupuestal=search_partida.posicion_presupuestaria.partida_presupuestal

