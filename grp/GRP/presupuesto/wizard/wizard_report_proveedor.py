from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import ValidationError,UserError
from odoo.tools.translate import _
from num2words import num2words

PERIODO_SELECT = [(periodo, periodo) for periodo in range(1,13)]
EJERCICIO_SELECT = [ (year, year) for year in range(2019, 2031)]

class wizard_report_proveedor(models.TransientModel):
    _name='tjacdmx_report_proveedor'
    _description=u'Reporte de proveedor'
    
    @api.model
    def _select_anio(self):
        fecha = datetime.today()
        return  fecha.year
    
    @api.model
    def _select_periodo(self):
        fecha = datetime.today()
        return  int(fecha.month)

    proveedor = fields.Many2one('res.partner', required=True)
    fecha_inicio=fields.Date(string='Fecha inicio', default=datetime.today())
    fecha_fin=fields.Date(string='Fecha fin', default=datetime.today())
    result_pc_html=fields.Html(string='Resultados',compute='search_pc_button')    
    csv_urls = fields.Char(compute='search_pc_button')




    @api.multi
    def search_pc_button(self):
        sql="""SELECT  a.id,a.account_id,c.code,c.tipo,a.debit, a.credit, a."name", a.invoice_id, a.move_id, a.date, a.ref,b."number"  from account_move_line  a 
inner join account_invoice b  on  b.id=a.invoice_id 
inner join account_account c  on  c.id=a.account_id   where a.partner_id=%s and a."date" between  '%s' and '%s';""" % (self.proveedor.id,self.fecha_inicio,self.fecha_fin)
        self.env.cr.execute(sql)
        sql_row = self.env.cr.dictfetchall()
        html_items_mov=""
        if(sql_row):
            for i in sql_row:
                ref=i['ref']
                name=i['name']
                date=i['date']
                saldo_inicial='{0:,.2f}'.format(float(0))
                cargo='{0:,.2f}'.format(float(i['debit']))
                abono='{0:,.2f}'.format(float(i['credit']))
                sal=float(i['debit'])-float(i['credit'])
                if(i['tipo']=='deudora'):
                    saldo='{0:,.2f}'.format(float(sal))
                else:
                    saldo='{0:,.2f}'.format(float(sal*-1))

                html_items_mov2="""
                <tr><td><p>%s</p></td> 
                <td><p>%s</p></td>
                <td><p>%s</p></td> 
                <td><p>$%s</p></td> 
                <td><p>$%s</p></td> 
                <td><p>$%s</p></td> 
                <td><p>$%s</p></td> 
                </tr>
                """ % (ref,name,date,saldo_inicial,cargo,abono,saldo)
                html_items_mov+=html_items_mov2.encode('ascii', 'ignore')
        else:
            html_items_mov1="""
                <tr>
                    <th style="text-align:center; color: red; font-size: 9px;"  colspan="6"><p>Sin Movimientos</p></th>
                </tr>
                """
            html_items_mov+=html_items_mov1.encode('ascii', 'ignore')

        html_items_code="""<table style="border:solid 2px; border-color:#5f5e97" class="table">

                <thead class="thead-dark">
                    <tr>
                    <th style="text-align:center"  colspan="7">Movimientos</th>
                    </tr>
                    <tr>
                    <th scope="col">Diario</th>
                    <th scope="col">Nombre</th>
                    <th scope="col">Fecha</th>
                    <th scope="col">Saldo inicial</th>
                    <th scope="col">Debe</th>
                    <th scope="col">Haber</th>
                    <th scope="col">Saldo</th>
                    </tr>
                </thead>
                <tbody>
                   %s
                </tbody>
                    </table>""" %(html_items_mov)

        self.result_pc_html=html_items_code

