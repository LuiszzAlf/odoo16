-- public.v_balanza_2 source

CREATE OR REPLACE VIEW public.v_balanza_2
AS SELECT a.id,
    e.id AS padre_code_id,
    e.code AS padre_code,
    concat(e.code, ' ', e.name) AS cuentas_padre,
    concat(a.code, ' ', a.name) AS cuentas,
    a.code,
    b.periodo AS periodo_fecha,
    date_part('month'::text, b.periodo)::integer AS periodo,
    date_part('year'::text, b.periodo)::character varying AS anio,
    abs(d.saldo_inicial) AS saldo_inicial,
    COALESCE(c.debe, 0::numeric) AS debe,
    COALESCE(c.haber, 0::numeric) AS haber,
    d.saldo_inicial + COALESCE(c.debe, 0::numeric) - COALESCE(c.haber, 0::numeric) AS saldo
   FROM account_account a
     LEFT JOIN account_account e ON e.id = a.account_padre
     CROSS JOIN ( SELECT date(generate_series(min(date_trunc('month'::text, a_1.date::timestamp with time zone)), max(a_1.date)::timestamp with time zone, '1 mon'::interval)) AS periodo
           FROM account_move_line a_1
             JOIN account_move b_1 ON b_1.id = a_1.move_id) b
     LEFT JOIN ( SELECT a_1.account_id,
            date(date_trunc('month'::text, a_1.date::timestamp with time zone)) AS periodo,
            round(sum(a_1.debit), 2) AS debe,
            round(sum(a_1.credit), 2) AS haber
           FROM account_move_line a_1
             JOIN account_move b_1 ON b_1.id = a_1.move_id
          WHERE b_1.state::text = 'posted'::text
          GROUP BY a_1.account_id, (date(date_trunc('month'::text, a_1.date::timestamp with time zone)))) c ON c.account_id = a.id AND c.periodo = b.periodo
     LEFT JOIN ( SELECT a_1.id AS account_id,
            b_1.periodo,
            sum(COALESCE(c_1.saldo_inicial, 0::numeric)) OVER (PARTITION BY a_1.id ORDER BY b_1.periodo) AS saldo_inicial
           FROM account_account a_1
             CROSS JOIN ( SELECT date(generate_series(min(date_trunc('month'::text, a_2.date::timestamp with time zone)), max(a_2.date)::timestamp with time zone, '1 mon'::interval)) AS periodo
                   FROM account_move_line a_2
                     JOIN account_move b_2 ON b_2.id = a_2.move_id) b_1
             LEFT JOIN ( SELECT a_2.account_id,
                    date(date_trunc('month'::text, a_2.date + '1 mon'::interval)) AS periodo,
                    round(sum(a_2.balance), 2) AS saldo_inicial
                   FROM account_move_line a_2
                     JOIN account_move b_2 ON b_2.id = a_2.move_id
                  WHERE b_2.state::text = 'posted'::text
                  GROUP BY a_2.account_id, (date(date_trunc('month'::text, a_2.date + '1 mon'::interval)))) c_1 ON c_1.account_id = a_1.id AND c_1.periodo = b_1.periodo
          ORDER BY a_1.id, b_1.periodo) d ON d.account_id = a.id AND d.periodo = b.periodo
  ORDER BY a.id, ("substring"(a.code::text, 5, 1)), ("substring"(a.code::text, 3, 1));