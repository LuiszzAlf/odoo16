from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import ValidationError,UserError
from odoo.tools.translate import _
from num2words import num2words

PERIODO_SELECT = [(periodo, periodo) for periodo in range(1,13)]
EJERCICIO_SELECT = [ (year, year) for year in range(2019, 2031)]

class wizard_cierre_ejercicio(models.TransientModel):
    _name='tjacdmx_cierre_ejercicio'
    _description=u'Cierre de ejercicio'
    
    @api.model
    def _select_anio(self):
        fecha = datetime.today()
        return  fecha.year
    
    @api.model
    def _select_periodo(self):
        fecha = datetime.today()
        return  int(fecha.month)

    cuenta = fields.Many2one('account.account', string='Cuenta cierre',required=True)
    fecha=fields.Date(required=True)


    @api.multi
    def create_move(self):
        line_ids=[]
        account_move = self.env['account.move']
        fecha = datetime.strptime(self.fecha, '%Y-%m-%d') if self.fecha else datetime.today()
        cuentas_cierre = self.env['tjacdmx.cuentas_cierre_ejercicio'].search([('state', '=', 'open')])
        cuentas_open=[]
        for each in cuentas_cierre:
            cuentas_open.append(each.cuenta.id)
        sql_md="""SELECT account_id, code, periodo_fecha, saldo_inicial,debe, haber,saldo_final from v_balanza where periodo =12 and anio='%s' and account_id in (%s) order by code desc;"""
        self.env.cr.execute(sql_md % (fecha.year,str(cuentas_open)[1:-1]))
        rows_sql = self.env.cr.dictfetchall()
        for i in rows_sql:
            if(i['saldo_final']>=0):
                line = [0,False,{
                        'analytic_account_id': False,
                        'account_id': i['account_id'],
                        'currency_id': False,
                        'credit': abs(i['saldo_final']),
                        'date_maturity': self.fecha,
                        'debit': 0,
                        'amount_currency': 0,
                        'partner_id': False,
                        'name': 'Poliza de cierre'
                    }]
            else:
                line =[0,False, {
                        'analytic_account_id': False,
                        'account_id': i['account_id'],
                        'currency_id': False,
                        'credit': 0,
                        'date_maturity': self.fecha,
                        'debit': abs(i['saldo_final']),
                        'amount_currency': 0,
                        'partner_id': False,
                        'name': 'Poliza de cierre'
                    }]
            line_ids.append(line)
        ref="""P.D. POLIZA DE CIERRE %s""" % (fecha.year)
        cargo=0
        abono=0
        for e in line_ids:
            cargo+=e[2]['debit']
            abono+=e[2]['credit']
        diferencia=cargo-abono
        if(diferencia>=0):
            line_saldo =[0,False, {
                    'analytic_account_id': False,
                    'account_id': self.cuenta.id,
                    'currency_id': False,
                    'debit': 0,
                    'date_maturity': self.fecha,
                    'credit': abs(diferencia),
                    'amount_currency': 0,
                    'partner_id': False,
                    'name': 'Poliza de cierre'
                }]
        else:
            line_saldo = [0,False,{
                    'analytic_account_id': False,
                    'account_id': self.cuenta.id,
                    'currency_id': False,
                    'debit': abs(diferencia),
                    'date_maturity': self.fecha,
                    'credit': 0,
                    'amount_currency': 0,
                    'partner_id': False,
                    'name': 'Poliza de cierre'
                }]
        line_ids.append(line_saldo)
        poliza = account_move.create({
            'journal_id': int(101),
            'date': self.fecha,
            'ref': ref,
            'narration':False,
            'line_ids':line_ids,
            'compra_id':''
        })
        poliza.post()
        sql_put = "UPDATE account_move SET state='cierre' WHERE id=%s" % (poliza.id)
        self.env.cr.execute(sql_put)

        action = self.env.ref('presupuestos.action_cierre_ano_move')
        res = self.env.ref('presupuestos.action_cierre_ano_move_form', False)
        if (poliza):
            result = action.read()[0]
            result['context'] = {}
            result['domain'] = "[('id','=', %s)]" % (poliza.id)
        else:
            result = action.read()[0]
            result['context'] = {}
            result['domain'] = "[('id','=', '')]"
        return result

    
