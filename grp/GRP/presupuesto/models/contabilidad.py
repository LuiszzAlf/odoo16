# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import api, fields, models, _, tools
from odoo.exceptions import ValidationError,UserError
from . import configuracion, catalogos
STATUS_DOC = [('close', 'Cerrado'),('open','Abierto')]
from dateutil.parser import parse

class MovimientoContable(models.Model):
    _name = 'account.move'
    _inherit = 'account.move'
    documento_id = fields.Many2one(comodel_name='presupuesto.documento', string='Documento', readonly=True)
    elaboro = fields.Char(string=u'Elaboró')
    reviso = fields.Char(string=u'Revisó')
    vobo = fields.Char(string=u'Vo.Bo.')
    autorizo = fields.Char(string=u'Autorizó')
    partida = fields.Char(compute='_compute_partida',string='Partida')
    concepto = fields.Text(string=u'Concepto')
    compra_id = fields.Many2one(comodel_name='purchase.order',string='Compra')
    reclasificacion_id = fields.Many2one(comodel_name='presupuesto.transferencia',string='Compra')
    id_move=fields.Integer(string='id_move')
    id_nomina=fields.Integer(string='No. Nomina')
    moment_budget=fields.Selection([('devengado','Devengado'),('ejercido','Ejercido'),('pagado','Pagado')])
    type_move_poliza=fields.Selection([('draft','Sin Validar'),('cierre','Poliza de cierre'),('apertura','Poliza de apertura')], required=True,default='draft')
    ley_ingresos=fields.Boolean(string='Ley de ingresos',default=False)

    
    
    @api.model
    def create(self,values):
        record = super(MovimientoContable, self).create(values)
        fecha = datetime.strptime(self.date, '%Y-%m-%d') if self.date else datetime.today()
        permiso = self.env['presupuesto.periodos.contables'].search([('periodo', '=', fecha.month),('ejercicio', '=',fecha.year),('state', '=','open')])
        if(permiso):
            if(record.type_move_poliza=='cierre'):
                am = self.env['account.move'].search([('id', '=', record.id)])
                query= "UPDATE account_move SET state='cierre' WHERE id=%s" % (am.id)
                self.env.cr.execute(query)
            elif(record.type_move_poliza=='apertura'):
                am = self.env['account.move'].search([('id', '=', record.id)])
                query= "UPDATE account_move SET state='apertura' WHERE id=%s" % (am.id)
                self.env.cr.execute(query)
        else:
            raise ValidationError("No es posible registrar el movimiento mientras el periodo este cerrado. Favor de verificar la fecha del registro.")
        return record

    # @api.one
    def post(self):
        invoice = self._context.get('invoice', False)
        self._post_validate()
        for move in self:
            fecha = datetime.strptime(move.date, '%Y-%m-%d') if move.date else datetime.today()
            permiso = self.env['presupuesto.periodos.contables'].search([('periodo', '=', fecha.month),('ejercicio', '=',fecha.year),('state', '=','open')])
            if(permiso):
                move.line_ids.create_analytic_lines()
                if move.name == '/':
                    new_name = False
                    journal = move.journal_id

                    if invoice and invoice.move_name and invoice.move_name != '/':
                        new_name = invoice.move_name
                    else:
                        if journal.sequence_id:
                            # If invoice is actually refund and journal has a refund_sequence then use that one or use the regular one
                            sequence = journal.sequence_id
                            if invoice and invoice.type in ['out_refund', 'in_refund'] and journal.refund_sequence:
                                if not journal.refund_sequence_id:
                                    raise UserError(_('Please define a sequence for the refunds'))
                                sequence = journal.refund_sequence_id

                            new_name = sequence.with_context(ir_sequence_date=move.date).next_by_id()
                        else:
                            raise UserError(_('Please define a sequence on the journal.'))

                    if new_name:
                        move.name = new_name
            else:
                raise ValidationError("No es posible validar el movimiento mientras el periodo este cerrado. Favor de verificar la fecha del registro.")

        return self.write({'state': 'posted'})
        
    
    def button_cancel(self):
        fecha = datetime.strptime(self.date, '%Y-%m-%d') if self.date else datetime.today()
        permiso = self.env['presupuesto.periodos.contables'].search([('periodo', '=', fecha.month),('ejercicio', '=',fecha.year),('state', '=','open')])
        if(permiso):
            for move in self:
                if not move.journal_id.update_posted:
                    raise UserError(_('You cannot modify a posted entry of this journal.\nFirst you should set the journal to allow cancelling entries.'))
            if self.ids:
                self.check_access_rights('write')
                self.check_access_rule('write')
                self._check_lock_date()
                self._cr.execute('UPDATE account_move '\
                        'SET state=%s '\
                        'WHERE id IN %s', ('draft', tuple(self.ids),))
                self.invalidate_cache()
            self._check_lock_date()
            return True
        else:
            raise ValidationError("No es posible cancelar el movimiento mientras el periodo este cerrado. Favor de verificar la fecha del registro.")


    
    def unlink(self):
        fecha = datetime.strptime(self.date, '%Y-%m-%d') if self.date else datetime.today()
        permiso = self.env['presupuesto.periodos.contables'].search([('periodo', '=', fecha.month),('ejercicio', '=',fecha.year),('state', '=','open')])
        if(permiso):
            for move in self:
                #check the lock date + check if some entries are reconciled
                move.line_ids._update_check()
                move.line_ids.unlink()
        else:
            raise ValidationError("No es posible eliminar el movimiento mientras el periodo este cerrado. Favor de verificar la fecha del registro.")
        return super(MovimientoContable, self).unlink()

    # @api.one
    def _compute_partida(self):
        if (self.line_ids):
            cuenta_comp = self.line_ids[0]
            i = cuenta_comp.account_id.code.split('.')
            self.partida  = i[2]
        else:
            self.partida  = 0

    
    def print_poliza_contable(self):
        datas = {}
        res = self.read(['date','name','concepto','elaboro','reviso','vobo','autorizo'])
        res = res and res[0] or {}
        datas['form'] = res
        tipo=self.name.split('/')[0]
        #raise ValidationError("%s" % (tipo))
        if(tipo == 'FACTURA'):
            datas['titulo'] = 'POLIZA DE EGRESOS'
            factura = self.env['account.invoice'].search([('number', '=', self.name)],limit=1)
            clc = self.env['presupuesto.clc'].search([('id_factura', '=', factura.id)],limit=1)
            datas['concepto'] = clc.no_clc
            datas['elaboro'] = self.write_uid.partner_id.name
        elif(tipo == 'MINI'):
            datas['titulo'] = 'POLIZA DE EGRESOS'
            pago = self.env['account.payment'].search([('move_name', '=', self.name)],limit=1)
            datas['concepto'] = pago.referencia
            datas['elaboro'] = self.write_uid.partner_id.name
        elif(tipo == 'I.G.'):
            datas['titulo'] = 'POLIZA DE INGRESOS'
            datas['concepto'] = self.ref
            datas['elaboro'] = self.write_uid.partner_id.name
        elif(tipo == 'GRAL'):
            datas['titulo'] = 'POLIZA DE DIARIO'
            datas['concepto'] = self.ref
            datas['elaboro'] = self.write_uid.partner_id.name
        elif(tipo == 'STJ'):
            datas['titulo'] = 'POLIZA DE DIARIO'
            datas['concepto'] = self.ref
            datas['elaboro'] = self.write_uid.partner_id.name
        else:
            datas['titulo'] = 'POLIZA DE EGRESOS'
            datas['concepto'] = self.ref
            datas['elaboro'] = self.write_uid.partner_id.name

        docs = self.env['account.move.line'].search([('move_id', '=', self.id)],order='account_id desc')
        cuentas = []
        suma_cargo = 0
        suma_abono = 0
        count = 0
        docs = self.env['account.move.line'].search([('move_id', '=', self.id)],order='account_id desc')
        for el in docs:
            account = el.account_id
            i = account.code.split('.')
            subcuenta_nombre = self.env['account.account'].search([('code', '=like', i[0] + '.' + i[1] + '.' + '%')])[0].name
            suma_cargo = suma_cargo + el.debit
            suma_abono = suma_abono + el.credit
            if(el.debit==0):
                parcial=el.credit
            else:
                parcial=el.debit
            cuenta = {
                'cuenta': i[0],             #cuenta               [0]
                'subcuenta': i[1],          #sub cuenta           [1]
                'cargo': '{0:,.2f}'.format(float(el.debit)),          #cargo                [5]
                'abono': '{0:,.2f}'.format(float(el.credit)),         #abono                [6]
                'parcial': '{0:,.2f}'.format(float(parcial)), 
            }
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
                cuenta_nombre = self.env['account.account'].search([('code', '=ilike', str(cuenta['cuenta']) + '.' + '%')])[0].name
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
                        'parcial': cuenta.get('parcial'),
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
                        'parcial': '',
                        'cargo': '',
                        'abono': '',
                        }
                        lineas.append(insert)
                        count += 1

        datas['lineas_cuenta'] = lineas
        datas['suma_abono'] = suma_abono
        datas['suma_cargo'] = suma_cargo
        #raise ValidationError("%s" % (lineas))
        return self.env['report'].get_action([], 'reportes.poliza_contable', data=datas)


    
    def print_poliza(self):
        datas = {}
        res = self.read(['date','name','concepto','elaboro','reviso','vobo','autorizo'])
        res = res and res[0] or {}
        datas['form'] = res
        cuentas = []
        suma_cargo = 0
        suma_abono = 0
        count = 0
        docs = self.env['account.move.line'].search([('move_id', '=', self.id)],order='account_id desc')
        for el in docs:
            account = el.account_id
            i = account.code.split('.')
            subcuenta_nombre = self.env['account.account'].search([('code', '=like', i[0] + '.' + i[1] + '.' + '%')])[0].name
            suma_cargo = suma_cargo + el.debit
            suma_abono = suma_abono + el.credit
            if(el.debit==0):
                parcial=el.credit
            else:
                parcial=el.debit
            cuenta = {
                'cuenta': i[0],             #cuenta               [0]
                'subcuenta': i[1],          #sub cuenta           [1]
                'cargo': '{0:,.2f}'.format(float(el.debit)),          #cargo                [5]
                'abono': '{0:,.2f}'.format(float(el.credit)),         #abono                [6]
                'parcial': '{0:,.2f}'.format(float(parcial)), 
            }
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
                cuenta_nombre = self.env['account.account'].search([('code', '=ilike', str(cuenta['cuenta']) + '.' + '%')])[0].name
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
                        'parcial': cuenta.get('parcial'),
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
                        'parcial': '',
                        'cargo': '',
                        'abono': '',
                        }
                        lineas.append(insert)
                        count += 1

        datas['lineas_cuenta'] = lineas
        datas['suma_abono'] = suma_abono
        datas['suma_cargo'] = suma_cargo
        #raise ValidationError("%s" % (lineas))
        return self.env['report'].get_action([], 'reportes.poliza_ac', data=datas)



class CuantasHijo(models.Model):
    _name = 'account.account.child'
    _description = u'Cuantas hijo'
    _rec_name = 'account'

    account_id = fields.Many2one(comodel_name='account.account', string='Reference', index=True)
    account = fields.Many2one(comodel_name='account.account', string='Cuenta')


class OrdenCuentas(models.Model):
    _name = "account.account"
    _inherit = 'account.account'

    account_padre = fields.Many2one(comodel_name='account.account', string='Cuenta padre')
    account_presupuesto = fields.Many2one(comodel_name='account.account', string='Cuenta presupuestal')
    nivel= fields.Integer(string="Nivel")
    tipo=fields.Selection([('acreedora','Acreedora'),('deudora','Deudora')])
    usable=fields.Boolean('Utilizable', default=True)
    account_child= fields.One2many('account.account.child', 'account_id', string='Cuentas hijo',copy=True)


    # 
    # def cal_account(self):
    #     account_account = self.env['account.account'].search([])
    #     truncate = """TRUNCATE TABLE public.account_account_child CONTINUE IDENTITY RESTRICT;"""
    #     self.env.cr.execute(truncate)
    #     for cuenta in account_account:
    #         sql_search_account = """with recursive account_tree AS ( 
    #                                         SELECT 
    #                                             a."id"
    #                                         FROM account_account a 
    #                                         where a.id= %s
    #                                     UNION  ALL 
    #                                         SELECT 
    #                                             a."id"
    #                                         FROM account_account a
    #                                         JOIN account_tree b ON b.id = a.account_padre 
    #                                 )
    #                                 select distinct* from account_tree  order by id;""" %(cuenta.id)
    #         self.env.cr.execute(sql_search_account)
    #         results = self.env.cr.fetchall()
    #         for ids in results:
    #             obj_account = self.env['account.account.child']
    #             ifexist=obj_account.search([('account','=',ids)])
    #             cuanta_create = obj_account.create({
    #                         'account_id': cuenta.id,
    #                         'account': ids
    #                     })
                    


        
    # 
    # @api.depends('name', 'code')
    # def name_get(self):
    #     result = super(OrdenCuentas, self).name_get()
    #     result = [] # reset result
    #     for account in self:
    #         name = '%s %s' % (account.code,account.name)
    #         result.append((account.id, name))
    #     return result





# class viewBalanzaCop(models.Model):
#     _name = 'contabilidad.view_bc'
#     _auto = False

#     code = fields.Char(string='Cuenta contable')
#     cuenta_padre = fields.Char(string='Cuenta padre')
#     # genero = fields.Char(string='Genero')
#     # grupo = fields.Char(string='Grupo')
#     # rubro = fields.Char(string='Rubro')
#     # cuenta = fields.Char(string='Cuenta')
#     # partida = fields.Char(string='Partida')
#     # indice = fields.Char(string='Indice')
#     anio = fields.Char(string='Año')
#     periodo = fields.Integer(string='Periodo')
#     saldo_inicial = fields.Float(string='Saldo inicial')
#     debe = fields.Float(string='Debe')
#     haber = fields.Float(string='Haber')
#     saldo = fields.Float(string='Saldo')

#     def _select(self):
#         select_str = """
#                     SELECT 
#                         ROW_NUMBER() OVER (ORDER BY 2) as id,
#                         id as id_cuenta,
#                         cuentas as code,
#                         cuentas_padre as cuenta_padre,
#                         anio,
#                         periodo,
#                         saldo_inicial,
#                         debe, 
#                         haber,
#                         saldo		
#                             """
#         return select_str

#     def _order_by(self):
#         order_by_str = """
#         """
#         return order_by_str

#     def init(self):
#         tools.drop_view_if_exists(self._cr, self._table)
#         self._cr.execute("""
#             CREATE view %s as
#                 %s
#                 FROM v_balanza_2
#                 %s
#         """ % (self._table, self._select(), self._order_by()))



# class res_partner_inherit(models.Model):
#     _inherit = 'res.partner'
#     @api.model
#     def get_cuenta(self):
#         return self.env['account.account'].search([('code','=','211.2.0001.21')])

#     property_account_payable_id = fields.Many2one(comodel_name='account.account', string="Account Payable", required=True, default=get_cuenta)
#     remisiones_count=fields.Integer(compute="_compute_remisiones", string='Entregas',copy=False, default=0)

#     def _compute_remisiones(self):
#         remision_origen=self.env['tjacdmx.remisiones'].search([('partner_id','=', self.id)])
#         self.remisiones_count = len(remision_origen)
    
    
#     
#     def view_remisiones(self):
#         remision_origen=self.env['tjacdmx.remisiones'].search([('partner_id','=', self.id)])
#         listids=[]
#         for each in remision_origen:
#             listids.append(each.id)
#         action = self.env.ref('presupuestos.action_remiciones')
#         res = self.env.ref('presupuestos.action_tjacdmx_remisiones_form', False)
#         search_remis_active = self.env['tjacdmx.remisiones'].search([('id','in',listids)])
#         if (search_remis_active):
#             result = action.read()[0]
#             result['context'] = {}
#             result['domain'] = "[('id','in',%s)]" % (listids)
#         else:
#             result = action.read()[0]
#             result['context'] = {}
#             result['domain'] = "[('id','=','0')]"
#         return result



class CierreEjercicio(models.Model):
    _name = 'tjacdmx.cuentas_cierre_ejercicio'
    _description = "Cuentas de cierre"
    _order = 'id desc'
    _rec_name = 'cuenta'
    _inherit = ['mail.thread']

    cuenta = fields.Many2one(comodel_name='account.account', string='Cuenta cierre',required=True)
    state = fields.Selection([
            ('draft','Borrador'),
            ('open', 'Proceso'),
            ], string='Estado', index=True, readonly=True, default='open',
            track_visibility='onchange', copy=False,
            help="")





# class MoveLine(models.Model):
#     _name = "account.move.line"
#     _inherit = 'account.move.line'


#     @api.onchange('account_id')
#     def change_account_id(self):
#         cuenta=self.env['account.account'].search([('id', '=', self.account_id.id)])
#         if(cuenta):
#             if(cuenta.usable==False):
#                 raise ValidationError("No se puede crear una póliza con cuentas acumulables.")
    
#     @api.model
#     def create(self,values):
#         record = super(MoveLine, self).create(values)
#         cuenta=self.env['account.account'].search([('id', '=', record.account_id.id)])
#         if(cuenta):
#             if(cuenta.usable==False):
#                 raise ValidationError("No se puede crear una póliza con cuentas acumulables.")
#         return record


class CierrePeriodoContable(models.Model):
    _name = 'presupuesto.periodos.contables'
    _description = "Control de periodos"
    _rec_name = 'id'
    _order = 'ejercicio desc, periodo asc'
    _inherit = ['mail.thread']

    periodo = fields.Selection(
        [(str(1),'Enero'),
        (str(2),'Febrero'),
        (str(3),'Marzo'),
        (str(4),'Abril'),
        (str(5),'Mayo'),
        (str(6),'Junio'),
        (str(7),'Julio'),
        (str(8),'Agosto'),
        (str(9),'Septiembre'),
        (str(10),'Octubre'),
        (str(11),'Noviembre'),
        (str(12),'Diciembre')], required=True)
    ejercicio = fields.Selection(catalogos.EJERCICIO_SELECT, required=True,track_visibility='onchange')
    state=fields.Selection(STATUS_DOC,string='Estatus', default='open',track_visibility='onchange',required=True)

#     @api.model
#     def create(self,values):
#         record = super(CierrePeriodoContable, self).create(values)
#         user_session = self.env['res.users'].browse(self.env.uid)
#         permisos = self.env['presupuesto.permisos.presupuestales'].search([('usuario_id','=',user_session.id),('control_periodos','=','open')])
#         if(permisos):
#             pass
#         else:
#             raise ValidationError("No cuenta con permisos para realizar esta operación, comuníquese con el administrador para revisar las operaciones autorizadas.")
#         return record
    
#     
#     def write(self, values):
#         record = super(CierrePeriodoContable, self).write(values)
#         user_session = self.env['res.users'].browse(self.env.uid)
#         permisos = self.env['presupuesto.permisos.presupuestales'].search([('usuario_id','=',user_session.id),('control_periodos','=','open')])
#         if(permisos):
#             pass
#         else:
#             raise ValidationError("No cuenta con permisos para realizar esta operación, comuníquese con el administrador para revisar las operaciones autorizadas.")
#         return record


# class NotasEstadosFinancieros(models.Model):
#     _name = 'tjacdmx.notas.estaods.financieros'
#     _description = "Notas a los estados financieros"
#     _rec_name = 'id'
#     _inherit = ['mail.thread']
    
#     archivo = fields.Binary(string='Archivo')
#     trimestre = fields.Selection(
#         [(str(1),'Primer trimestre'),
#         (str(2),'Segundo trimestre'),
#         (str(3),'Tercer trimestre'),
#         (str(4),'Cuarto trimestre')], required=True)
#     ejercicio = fields.Selection(catalogos.EJERCICIO_SELECT, required=True,track_visibility='onchange')
#     nota = fields.Char(string='Nota')

#     @api.model
#     def create(self,values):
#         record = super(NotasEstadosFinancieros, self).create(values)
#         user_session = self.env['res.users'].browse(self.env.uid)
#         permisos = self.env['presupuesto.permisos.presupuestales'].search([('usuario_id','=',user_session.id),('control_periodos','=','open')])
#         if(permisos):
#             pass
#         else:
#             raise ValidationError("No cuenta con permisos para realizar esta operación, comuníquese con el administrador para revisar las operaciones autorizadas.")
#         return record
    
#     
#     def write(self, values):
#         record = super(NotasEstadosFinancieros, self).write(values)
#         user_session = self.env['res.users'].browse(self.env.uid)
#         permisos = self.env['presupuesto.permisos.presupuestales'].search([('usuario_id','=',user_session.id),('control_periodos','=','open')])
#         if(permisos):
#             pass
#         else:
#             raise ValidationError("No cuenta con permisos para realizar esta operación, comuníquese con el administrador para revisar las operaciones autorizadas.")
#         return record

     
        