-- public.v_balanza source

CREATE OR REPLACE VIEW public.v_balanza
AS SELECT a.id AS account_id,
    b.id AS padre_code_id,
    b.code AS padre_code,
    a.name AS nombre_c,
    concat(b.code, ' ', b.name) AS cuentas_padre,
    concat(a.code, ' ', a.name) AS cuentas,
    a.code,
    date(date_trunc('month'::text, c.periodo::timestamp with time zone) + '1 mon -1 days'::interval) AS periodo_fecha,
    date_part('month'::text, c.periodo)::integer AS periodo,
    date_part('year'::text, c.periodo)::character varying AS anio,
    c.saldo_inicial,
    c.debe,
    c.haber,
    c.saldo_final
   FROM account_account a
     LEFT JOIN account_account b ON b.id = a.account_padre
     LEFT JOIN tjacdmx_balanza_comprobacion c ON c.account_id = a.id
  WHERE a.code::text !~~ '8%'::text
UNION
 SELECT a.id AS account_id,
    b.id AS padre_code_id,
    b.code AS padre_code,
    a.name AS nombre_c,
    concat(b.code, ' ', b.name) AS cuentas_padre,
    concat(a.code, ' ', a.name) AS cuentas,
    a.code,
    date(date_trunc('month'::text, c.periodo::timestamp with time zone) + '1 mon -1 days'::interval) AS periodo_fecha,
    date_part('month'::text, c.periodo)::integer AS periodo,
    date_part('year'::text, c.periodo)::character varying AS anio,
    sum(c.saldo_inicial) OVER (PARTITION BY c.account_id ORDER BY c.periodo) AS saldo_inicial,
    sum(c.debe) OVER (PARTITION BY c.account_id ORDER BY c.periodo) AS debe,
    sum(c.haber) OVER (PARTITION BY c.account_id ORDER BY c.periodo) AS haber,
    sum(c.saldo_final) OVER (PARTITION BY c.account_id ORDER BY c.periodo) AS saldo_final
   FROM account_account a
     LEFT JOIN account_account b ON b.id = a.account_padre
     LEFT JOIN tjacdmx_balanza_comprobacion c ON c.account_id = a.id
  WHERE a.code::text ~~ '8%'::text;