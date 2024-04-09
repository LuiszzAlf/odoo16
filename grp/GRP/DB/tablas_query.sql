-- public.tjacdmx_balanza_comprobacion definition

-- Drop table

-- DROP TABLE public.tjacdmx_balanza_comprobacion;

CREATE TABLE public.tjacdmx_balanza_comprobacion (
	account_id int4 NOT NULL,
	periodo date NOT NULL,
	saldo_inicial numeric NULL DEFAULT 0,
	debe numeric NULL DEFAULT 0,
	haber numeric NULL DEFAULT 0,
	saldo_final numeric NULL DEFAULT 0,
	CONSTRAINT indx_account UNIQUE (account_id, periodo)
);

