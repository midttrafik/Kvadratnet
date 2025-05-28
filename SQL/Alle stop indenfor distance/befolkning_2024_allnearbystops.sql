DROP MATERIALIZED VIEW IF EXISTS grunddata.mvw_befolkning_2024_allnearbystops;

CREATE MATERIALIZED VIEW IF NOT EXISTS grunddata.mvw_befolkning_2024_allnearbystops
TABLESPACE pg_default
AS
	WITH aktuelle_standere AS MATERIALIZED (
		SELECT n.no::text AS standernummer,
			   split_part(ns.navn, '[', 1) AS standernavn,
			   ns.stoptype AS standertype
		FROM drift.node n
		JOIN (
			SELECT nodegid,
				   stopnummer,
				   navn,
				   'Flextur' AS stoptype
			FROM grunddata.get_flexturknudepunkter(drift.importid_kpl('K24')) get_flexturknudepunkter(nodegid, stopnummer, navn, stoptype, geom)
			UNION
			SELECT nodegid,
				   stopnummer,
				   navn,
				   'Plustur' AS stoptype
			FROM grunddata.get_plusturknudepunkter(drift.importid_kpl('K24')) get_plusturknudepunkter(nodegid, stopnummer, navn, stoptype, geom)
			UNION
			SELECT nodegid,
				   stopnummer,
				   navn,
				   CASE WHEN navn LIKE '%Letbane%' THEN 'Letbane' ELSE 'Tog' END AS stoptype
			FROM grunddata.get_stationer(drift.importid_kpl('K24')) get_stationer(nodegid, stopnummer, navn, stoptype, geom)
			UNION
			SELECT nodegid,
				   stopnummer,
				   navn,
				   'Bus' As stoptype
			FROM grunddata.get_busstop(drift.importid_kpl('K24')) get_busstop(nodegid, stopnummer, navn, stoptype, geom)
		) ns ON n.gid = ns.nodegid
		LEFT JOIN drift.stoppoint s ON n.no = s.no AND s.importid = n.importid
		WHERE ns.navn !~~ 'NEDLAGT%'::text AND n.importid = drift.importid_kpl('K24')
	), 

	-- lav række for hvert par af stander, itcs nr.
	stander_itcs AS MATERIALIZED (
		SELECT d.dag AS ugedag,
			   d.tidsinterval,
			   sp.no::text AS standernummer,
			   v.itcsno AS itcs,
			   vjt.trafikart
		FROM drift.vehjourney v
		JOIN drift.line line ON v.linegid = line.gid
		JOIN grunddata.vw_vehjourneygid_with_tsys vjt ON v.gid = vjt.gid
		JOIN drift.vehjourneysection vjs ON v.gid = vjs.vehjourneygid
		JOIN drift.vw_dates vd ON vd.validdaysgid = vjs.validdaysgid
		JOIN drift.timeprofileitem t ON v.timeprofilegid = t.timeprofilegid
		JOIN drift.linerouteitem l ON t.linerouteitemindexgid = l.gid
		JOIN drift.stoppoint sp ON l.stoppointgid = sp.gid
		RIGHT JOIN grunddata.dagsinddelinger d ON date_part('isodow'::text, vd.date) = d.ugedagnr::double precision AND date_part('week'::text, vd.date) = d.uge::double precision AND date_part('hour'::text, v.dep::interval + t.arr::time without time zone) >= d.starttime::double precision AND date_part('hour'::text, v.dep::interval + t.arr::time without time zone) <= (d.sluttime - 1)::double precision
		WHERE drift.importid_get_kpl(v.importid)::text = 'K24'::text 
		 AND d.tidsinterval::text = 'Døgn'::text 
		 AND vjt.trafikart <> 'Skolebus'::text 
		 AND vjt.trafikart <> 'Dublering'::text
	),

	-- Lav stop kolonner om til rækker
	unionized AS MATERIALIZED (
		SELECT id,
			   400 AS distance,
			   stops_400 AS stander_list
		FROM grunddata.befolkning_2024_allnearbystops
		UNION ALL
		SELECT id,
			   500 AS distance,
			   stops_500 AS stander_list
		FROM grunddata.befolkning_2024_allnearbystops
		UNION ALL
		SELECT id,
			   600 AS distance,
			   stops_600 AS stander_list
		FROM grunddata.befolkning_2024_allnearbystops
		UNION ALL
		SELECT id,
			   800 AS distance,
			   stops_800 AS stander_list
		FROM grunddata.befolkning_2024_allnearbystops
		UNION ALL
		SELECT id,
			   1000 AS distance,
			   stops_1000 AS stander_list
		FROM grunddata.befolkning_2024_allnearbystops
		UNION ALL
		SELECT id,
			   2000 AS distance,
			   stops_2000 AS stander_list
		FROM grunddata.befolkning_2024_allnearbystops
	), 

	-- cross join med alle typer ugedage og tidsintervaller således at også tidspunkter med 0 afgange er inkluderet
	crossed AS MATERIALIZED (
		SELECT unionized.id,
			   unionized.distance,
			   unionized.stander_list,
			   d.ugedag,
			   d.tidsinterval
		FROM unionized
		CROSS JOIN ( VALUES ('Hverdag', 'Døgn'), ('Lørdag', 'Døgn'), ('Søndag', 'Døgn')) d(ugedag, tidsinterval)
	),

	-- split semikolon separeret liste af standere til en række per stander
	unnested AS MATERIALIZED (
		SELECT DISTINCT crossed.id,
			   crossed.distance,
			   crossed.ugedag,
			   crossed.tidsinterval,
			   NULLIF(unnest(regexp_split_to_array(crossed.stander_list::text, ';'::text)), ''::text) AS standernummer
		FROM crossed
	)

	-- join standere på befolkningskvadratet
	-- join aktuelle standere på så vi ved hvilken type stander det er
	-- join itcs på standere
	-- tæl antal unikke itcs per kvadrat = antal unikke afgange indenfor x meter og find standertyperne 
	SELECT row_number() OVER () AS gid,
		   b.id,
		   b.antal_tal,
		   b.antal_txt,
		   b.the_geom,
		   u.distance,
		   u.ugedag,
		   u.tidsinterval,
		   COUNT(DISTINCT u.standernummer) AS "antal_standere",
		   COUNT(DISTINCT s.standertype) AS "antal_standertyper",
		   STRING_AGG(DISTINCT s.standertype::text, ', ') AS "standertyper",
		   COUNT(DISTINCT si.itcs) AS "afgange_døgn",
		   FLOOR(COUNT(DISTINCT si.itcs)::numeric / 24.0) AS "afgange_time",
		   COALESCE(BOOL_OR(s.standertype = 'Bus'), FALSE) AS "adgang_bus",
		   COALESCE(BOOL_OR(s.standertype = 'Tog'), FALSE) AS "adgang_tog",
		   COALESCE(BOOL_OR(s.standertype = 'Letbane'), FALSE) AS "adgang_letbane",
		   COALESCE(BOOL_OR(s.standertype = 'Flextur'), FALSE) AS "adgang_flextur",
		   COALESCE(BOOL_OR(s.standertype = 'Plustur'), FALSE) AS "adgang_plustur"
	FROM grunddata.befolkning_2024 b
	LEFT JOIN unnested u ON b.id = u.id
	LEFT JOIN aktuelle_standere s ON u.standernummer = s.standernummer
	LEFT JOIN stander_itcs si ON u.ugedag = si.ugedag::text AND u.tidsinterval = si.tidsinterval AND u.standernummer = si.standernummer
	GROUP BY b.id, b.antal_tal, b.antal_txt, b.the_geom, u.distance, u.ugedag, u.tidsinterval
	ORDER BY b.id, u.distance, u.ugedag, u.tidsinterval
WITH DATA;

ALTER TABLE IF EXISTS grunddata.mvw_befolkning_2024_allnearbystops
    OWNER TO midttrafik;

COMMENT ON MATERIALIZED VIEW grunddata.mvw_befolkning_2024_allnearbystops
    IS 'Viser antal afgange og typer af tilgængelig offentlig transport indenfor x meter for hvert befolkningskvadrat. Inkluderer afgange for bus, flexbus, letbane og lokalbane. Inkluderer ikke afgange for tog.';

CREATE INDEX idx_mvw_befolkning_2024_allnearbystops_the_geom
    ON grunddata.mvw_befolkning_2024_allnearbystops USING gist
    (the_geom)
    TABLESPACE pg_default;