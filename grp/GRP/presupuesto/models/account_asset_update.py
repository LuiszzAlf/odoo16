# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tools import float_compare, float_is_zero
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.tools.translate import _
from odoo import models, fields, api
import calendar
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import dateutil.relativedelta
from calendar import monthrange

from odoo.exceptions import ValidationError, UserError
import logging
_logger = logging.getLogger(__name__)


class account_asset_update(models.Model):
    _inherit = 'account.asset.asset'
    # AGREGA CAMPOS A LOS ACTIVOS PARA EL MODULO DE RESGUARDOS  START
    date_sale_activo = fields.Date(string=u'Fecha de compra')
    emple_asig = fields.Char(string='Resguardante')
    marca = fields.Char(string="Marca")
    no_serie = fields.Char(string="Numero de serie")
    modelo = fields.Char(string='Modelo')
    estado_fisico = fields.Char(string='Estado Fisico')
    piso = fields.Selection(
        [('1', '1'), 
         ('2', '2'), 
         ('3', '3'), 
         ('4', '4'),
         ('5', '5'), 
         ('6', '6'), 
         ('7', '7'), 
         ('8', '8'),
         ('9', '9'), 
         ('10', '10'), 
         ('11', '11'), 
         ('12', '12'), 
         ('13', 'PB'), 
         ('14', 'E1'), 
         ('15', 'E2'), 
         ('16', 'Almacén General')],string='Piso', required=True)
    edificio = fields.Selection([('Insurgentes', 'Insurgentes'), (
        'Coyoacan', 'Coyoacan'), ('Nebraska', 'Nebraska')], string='Edificio')
    id_empleado_linea = fields.Integer(string='Empleado')
    status = fields.Char(string='Status', default='open')
    comment_activo = fields.Text(string='Comentario')
    placa = fields.Char(string='Placas')
    no_motor = fields.Char(string='No. del motor')
    category_asset = fields.Text(
        compute='_getCategoryAsset', string='Categoria de activo')
    code_bar = fields.Char(string='Codigo de barras')
    no_factura = fields.Char(string='No. Factura')
    clase = fields.Char(string='Clase')
    partida = fields.Many2one('presupuesto.partida_presupuestal',
                              track_visibility='onchange', string='Posición presupuestaria', required=True)
    movimientos_reguardo = fields.One2many(
        'tjacdmx.movimientos_resguardante', 'activo', string='Movimientos', track_visibility='onchange')

    def genera_movimientos(self):
        query = """select
                        tlrl.id_activo,
                        tlrl.tipo_mov,
                        tlrl.create_date,
                        tlrl.resguardo_id,
                        tlr.id_empleado
                    from
                        tjacdmx_log_resguardo_lineas tlrl
                    join tjacdmx_log_resguardos tlr on
                        tlr.id = tlrl.resguardo_id;"""
        self.env.cr.execute(query)
        movs = self.env.cr.dictfetchall()
        for i in movs:
            mov_activo = self.env['tjacdmx.movimientos_resguardante']
            if (i['tipo_mov'] == 'Asignacion'):
                tipo = 'asignacion'
            elif (i['tipo_mov'] == 'Liberado'):
                tipo = 'desasignacion'
            mov_activo.create({
                'resguardante': i['id_empleado'],
                'activo': i['id_activo'],
                'tipo': tipo,
                'fecha': i['create_date'],
            })

    @api.depends('total_depreciado')
    def _compute_total(self):
        sql_origen = """with saldo_anterior as ((
                        select
                            aadl.asset_id id_activo,
                                    coalesce(sum(aadl.amount), 0) valor_anterior2018
                        from
                            account_asset_depreciation_line aadl
                        where
                            extract(year
                        from
                            DATE (aadl.depreciation_date)) <= '2018'
                        group by
                            1))
                        select
                            coalesce((sum(aadl.amount) + coalesce((
                                        select valor_anterior2018
                                        from saldo_anterior
                                        where id_activo = %s), 0)), 0) total_depreciado,
                                        coalesce(aaa.value-(sum(aadl.amount) + coalesce((
                                        select valor_anterior2018
                                        from saldo_anterior
                                        where id_activo = %s), 0)), 0) residual
                        from
                            account_asset_asset aaa
                            join account_asset_depreciation_line aadl on aaa.id = aadl.asset_id
                        where aadl.move_id > 0
                            and aaa.id=%s
                            and state = 'open'
                        group by aaa.value;
                        """
        self.env.cr.execute(sql_origen % (self.id, self.id, self.id))
        totales_depreciacion = self.env.cr.dictfetchall()
        if (totales_depreciacion):
            for each in totales_depreciacion:
                if (each):
                    self.total_depreciado = each['total_depreciado']
                    self.residual = each['residual']
        else:
            self.total_depreciado = self.value
            self.residual = 0

            # raise ValidationError('%s' % each )

    total_depreciado = fields.Float(digits=(
        15, 2), compute='_compute_total', default=0, string='Total depreciado', store=True)
    residual = fields.Float(
        digits=(15, 2), compute='_compute_total', default=0, string='Residual')

    def sinc_compute_total(self):
        sql_origen = """with saldo_anterior as ((
                        select
                            aadl.asset_id id_activo,
                                    coalesce(sum(aadl.amount), 0) valor_anterior2018
                        from
                            account_asset_depreciation_line aadl
                        where
                            extract(year
                        from
                            DATE (aadl.depreciation_date)) <= '2018'
                        group by
                            1))
                        select
                            coalesce((sum(aadl.amount) + coalesce((
                                        select valor_anterior2018
                                        from saldo_anterior
                                        where id_activo = %s), 0)), 0) total_depreciado,
                                        coalesce(aaa.value-(sum(aadl.amount) + coalesce((
                                        select valor_anterior2018
                                        from saldo_anterior
                                        where id_activo = %s), 0)), 0) residual
                        from
                            account_asset_asset aaa
                            join account_asset_depreciation_line aadl on aaa.id = aadl.asset_id
                        where aadl.move_id > 0
                            and aaa.id=%s
                            and state = 'open'
                        group by aaa.value;
                        """
        self.env.cr.execute(sql_origen % (self.id, self.id, self.id))
        totales_depreciacion = self.env.cr.dictfetchall()
        total_depreciado = 0
        residual = 0
        if (totales_depreciacion):
            for each in totales_depreciacion:
                if (each):
                    total_depreciado = each['total_depreciado']
                    residual = each['residual']
        else:
            total_depreciado = self.value
            residual = 0
        self.write({'total_depreciado': total_depreciado, 'residual': residual})

    def open_resguardo(self):
        action = self.env.ref('resguardos.action_resguardos')
        search_resguardo = self.env['tjacdmx.resguardos'].search(
            [('id', '=', self.id_empleado_linea)], limit=1)
        if (search_resguardo):
            result = action.read()[0]
            result['context'] = {}
            result['domain'] = "[('id','=', %s)]" % (search_resguardo.id)
        else:

            pass
        return result

    def wizard_codebar(self):
        if (self.code_bar):
            return {
                'name': _("Genera codigo de barras del activo"),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'wizard.codebar',
                'target': 'new',
                'type': 'ir.actions.act_window',
                'context': {'codebar_num': self.code_bar, 'activo': self.name, 'no_inventario': self.code}
            }

    def actu_code_bar(self):
        activos = self.env['account.asset.asset'].search([])
        for i in activos:
            query = """select 
                        concat(
                            substring(split_part(code::TEXT,' ', 2) from 1 for 4),
                            substring(split_part(code::TEXT,' ', 2) from 8 for 3),
                            split_part(code::TEXT,'-', 2)
                        ) as code
                    from account_asset_asset
                    where id=%s;""" % (i.id)
            self.env.cr.execute(query)
            code = self.env.cr.dictfetchall()
            code_barra = ''
            if (code):
                code_barra = code[0]['code']
            tjacdmx_update_asset_code = "UPDATE account_asset_asset SET code_bar='%s' WHERE id=%s" % (
                code_barra, i.id)
            self.env.cr.execute(tjacdmx_update_asset_code)

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        if not recs:
            recs = self.search(['|',
                                ('no_serie', operator, name),
                                ('name', operator, name),
                                ] + args, limit=limit)
            if (not recs.name_get()):
                recs = self.search(['|',
                                    ('code', operator, name),
                                    ('code_bar', operator, name),
                                    ] + args, limit=limit)
        return recs.name_get()

    def _getCategoryAsset(self):
        id_asset = int(self.category_id)
        category = self.env['account.asset.category'].search(
            [('id', '=', id_asset)]).name
        self.category_asset = category

    def _compute_board_amount(self, sequence, residual_amount, amount_to_depr, undone_dotation_number, posted_depreciation_line_ids, total_days, depreciation_date):
        amount = 0
        if sequence == undone_dotation_number:
            amount = residual_amount
        else:
            if self.method == 'linear':
                amount = amount_to_depr / \
                    (undone_dotation_number - len(posted_depreciation_line_ids))
                if self.prorata:
                    amount = amount_to_depr / self.method_number
            elif self.method == 'degressive':
                amount = residual_amount * self.method_progress_factor
        return round(float('%.8f' % (amount)), 5)

    def _compute_board_undone_dotation_nb(self, depreciation_date, total_days):
        undone_dotation_number = self.method_number
        if self.method_time == 'end':
            end_date = datetime.strptime(self.method_end, DF).date()
            undone_dotation_number = 0
            while depreciation_date <= end_date:
                depreciation_date = date(depreciation_date.year, depreciation_date.month,
                                         depreciation_date.day) + relativedelta(months=+self.method_period)
                undone_dotation_number += 1
        if self.prorata:
            undone_dotation_number += 1
        return undone_dotation_number

    def compute_depreciation_board(self):
        self.ensure_one()

        posted_depreciation_line_ids = self.depreciation_line_ids.filtered(
            lambda x: x.move_check).sorted(key=lambda l: l.depreciation_date)
        unposted_depreciation_line_ids = self.depreciation_line_ids.filtered(
            lambda x: not x.move_check)

        # Remove old unposted depreciation lines. We cannot use unlink() with One2many field
        commands = [(2, line_id.id, False)
                    for line_id in unposted_depreciation_line_ids]

        if self.value_residual != 0.0:
            amount_to_depr = residual_amount = self.value_residual
            if self.prorata:
                # if we already have some previous validated entries, starting date is last entry + method perio
                if posted_depreciation_line_ids and posted_depreciation_line_ids[-1].depreciation_date:
                    last_depreciation_date = datetime.strptime(
                        posted_depreciation_line_ids[-1].depreciation_date, DF).date()
                    depreciation_date = last_depreciation_date + \
                        relativedelta(months=+self.method_period)
                else:
                    depreciation_date = datetime.strptime(
                        self._get_last_depreciation_date()[self.id], DF).date()

            else:
                # depreciation_date = 1st of January of purchase year if annual valuation, 1st of
                # purchase month in other cases
                if self.method_period >= 12:
                    if self.company_id.fiscalyear_last_month:
                        asset_date = date(year=int(self.date[:4]),
                                          month=self.company_id.fiscalyear_last_month,
                                          day=self.company_id.fiscalyear_last_day) + \
                            relativedelta(days=1) + \
                            relativedelta(
                                year=int(self.date[:4]))  # e.g. 2018-12-31 +1 -> 2019
                    else:
                        asset_date = datetime.strptime(
                            self.date[:4] + '-01-01', DF).date()
                else:
                    asset_date = datetime.strptime(
                        self.date[:7] + '-01', DF).date()
                # if we already have some previous validated entries, starting date isn't 1st January but last entry + method period
                if posted_depreciation_line_ids and posted_depreciation_line_ids[-1].depreciation_date:
                    last_depreciation_date = datetime.strptime(
                        posted_depreciation_line_ids[-1].depreciation_date, DF).date()
                    depreciation_date = last_depreciation_date + \
                        relativedelta(months=+self.method_period)
                else:
                    depreciation_date = asset_date

            fecha = datetime.strptime(self.date, '%Y-%m-%d')
            depreciation_date = depreciation_date + \
                dateutil.relativedelta.relativedelta(months=1)

            day = depreciation_date.day
            month = depreciation_date.month
            year = depreciation_date.year
            total_days = (year % 4) and 365 or 366

            undone_dotation_number = self._compute_board_undone_dotation_nb(
                depreciation_date, total_days)

            for x in range(len(posted_depreciation_line_ids), undone_dotation_number):
                sequence = x + 1
                amount = self._compute_board_amount(
                    sequence, residual_amount, amount_to_depr, undone_dotation_number, posted_depreciation_line_ids, total_days, depreciation_date)

                if float_is_zero(amount, precision_rounding=self.currency_id.rounding):
                    continue

                residual_amount = round(
                    float('%.8f' % (residual_amount - amount)), 5)
                depreciated_value = round(
                    float('%.8f' % (self.value - (self.salvage_value + residual_amount))), 5)

                if residual_amount < 0:
                    residual_amount = 0.0

                vals = {
                    'amount': amount,
                    'asset_id': self.id,
                    'sequence': sequence,
                    'name': (self.code or '') + '/' + str(sequence),
                    'remaining_value': residual_amount,
                    'depreciated_value': depreciated_value,
                    'depreciation_date': depreciation_date,
                    'category_asset': self.category_asset
                }
                commands.append((0, False, vals))
                # Considering Depr. Period as months
                depreciation_date = date(
                    year, month, day) + relativedelta(months=+self.method_period)
                day = depreciation_date.day
                month = depreciation_date.month
                year = depreciation_date.year

        self.write({'depreciation_line_ids': commands})

        return True


class depreciaciones(models.Model):
    _inherit = 'account.asset.depreciation.line'

    category_asset = fields.Text(
        compute='_getCategoryAsset', string='Categoria de activo', store=True, default="Otro")

    def _getCategoryAsset(self):
        id_asset = int(self.asset_id.category_id)
        category = self.env['account.asset.category'].search(
            [('id', '=', id_asset)]).name
        self.category_asset = category

    @api.model
    def compute_generated_entries_range(self, date_min, date_max, asset_type=None, post_move=True):
        created_moves = self.env['account.move']
        depreciation_date = datetime.strptime(
            date_max, '%Y-%m-%d') or fields.Date.context_today(self)

        last = depreciation_date.replace(day=calendar.monthrange(
            depreciation_date.year, depreciation_date.month)[1])

        if last.weekday() < 5:
            depreciation_date = last

        else:
            depreciation_date = last-timedelta(days=1 + last.weekday() - 5)

        query = """
            SELECT
                b.category_id,
                c.name categoria,
                c.account_depreciation_id,
                c.account_depreciation_expense_id,
                c.journal_id,
                c.account_analytic_id,
                c.type,
                sum(a.amount) amount
            FROM
                account_asset_depreciation_line a
                LEFT JOIN account_asset_asset b ON a.asset_id = b.id
                LEFT JOIN account_asset_category c ON b.category_id = c.id
            WHERE
                b.state = 'open'
                AND a.move_check = FALSE
                AND a.move_id is NULL
                AND c.group_entries = TRUE
                AND a.depreciation_date >= '%s'
                AND a.depreciation_date <= '%s'
            GROUP BY 1,2,3,4,5,6,7
        """ % (date_min, date_max)

        self.env.cr.execute(query)
        response = self.env.cr.dictfetchall()

        for x in response:
            name = x['categoria'] + _(' (grouped)')
            amount = float('%.8f' % (x['amount']))

            move_line_1 = {
                'name': name,
                'account_id': x['account_depreciation_id'],
                'debit': 0.0,
                'credit': x['amount'],
                'journal_id': x['journal_id'],
                'analytic_account_id': x['account_analytic_id'] if x['type'] == 'sale' else False,
            }
            move_line_2 = {
                'name': name,
                'account_id': x['account_depreciation_expense_id'],
                'credit': 0.0,
                'debit': amount,
                'journal_id': x['journal_id'],
                'analytic_account_id': x['account_analytic_id'] if x['type'] == 'purchase' else False,
            }
            move_vals = {
                'ref': x['categoria'],
                'date': depreciation_date or False,
                'journal_id': x['journal_id'],
                'line_ids': [(0, 0, move_line_1), (0, 0, move_line_2)],
            }
            move = self.env['account.move'].create(move_vals)

            if move:
                lines_depreciation = self.env['account.asset.depreciation.line'].search([
                    ('depreciation_date', '<=',
                     date_max), ('depreciation_date', '>=', date_min),
                    ('move_check', '=', False), ('move_id', '=', False)])

                for y in lines_depreciation:
                    _logger.debug(
                        "!!!!!!!!!!!!!!!!!1---------------- %s" % x['categoria'])
                    query = "UPDATE account_asset_depreciation_line SET move_check = TRUE, move_posted_check = TRUE, move_id = %s WHERE id = %s and category_asset = '%s' and depreciation_date >= '%s' and depreciation_date <= '%s'" % (
                        move.id, y.id, x['categoria'], date_min, date_max)
                    self.env.cr.execute(query)

            created_moves |= move

        return [x.id for x in created_moves]

    # AGREGA CAMPOS A LOS ACTIVOS PARA EL MODULO DE RESGUARDOS  END


class DepreciationLine(models.Model):
    _inherit = 'account.asset.depreciation.line'

    @api.model
    def create(self, values):
        res = super(depreciaciones, self).create(values)
        # id_asset = str('sss')
        # raise ValidationError("%s" % (id_asset))
        return res


class movimientos_resguardante(models.Model):
    _name = 'tjacdmx.movimientos_resguardante'
    resguardante = fields.Many2one(
        'tjacdmx.resguardantes', string='Resguardante')
    activo = fields.Many2one('account.asset.asset', string='Nombre de activo')
    tipo = fields.Selection([('asignacion', 'Asignacion'), ('reasignacion', 'Reasignacion'), (
        'desasignacion', 'Desasignacion')], string='Tipo', default='asignacion')
    fecha = fields.Datetime(string='Scheduled Date', default=datetime.today())


class repair_asset(models.Model):
    _name = 'tjacdmx.repair_asset'
    _rec_name = 'name'

    asset_id = fields.Integer(string="asset_id")
    name = fields.Char(string="name")
    sequence = fields.Char(string="sequence")
    move_check = fields.Char(string="move_check")
    depreciation_date = fields.Char(string="depreciation_date")
    amount = fields.Float(string="amount")
    move_posted_check = fields.Char(string="move_posted_check")
    remaining_value = fields.Char(string="remaining_value")
    move_id = fields.Integer(string="move_id")
    depreciated_value = fields.Char(string="depreciated_value")
    category_asset = fields.Char(string="category_asset")
    state_asiento = fields.Boolean(string='Asiento', default=True)
    state_activo = fields.Boolean(string='Activo', default=True)
    state_final = fields.Boolean(string='Activo', default=False)
