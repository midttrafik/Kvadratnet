/**
* Vis befolkningskvadratnet med antal afgange indenfor forskellige distancer per. kørselsdagtype
* Tilpas navne og kolonner efter behov.
* 'afgange_døgn' eller 'afgange_time' kan bruges til at farvelægge kvadraterne.
* Filtre for kørselsdagtype og distance skal være påkrævet ellers tegnes befolkningskvadratnettet 9 gange oven på hinanden.
* Tager 5-10 minutter at beregne da tabellerne er store.
**/

CREATE MATERIALIZED VIEW IF NOT EXISTS grunddata.mvw_befolkning_2024_allnearbystops
TABLESPACE pg_default
AS
 -- find alle ITCS per stander for K24, på døgn niveau, uden flextur, skolebustur og dubleringstur
 -- meget stor tabel da rækkerne er alle gyldige (stander, ITCS)
 WITH stander_itcs AS MATERIALIZED (
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
	 RIGHT JOIN grunddata.dagsinddelinger d 
      ON date_part('isodow'::text, vd.date) = d.ugedagnr::double precision 
	  AND date_part('week'::text, vd.date) = d.uge::double precision 
	  AND date_part('hour'::text, v.dep::interval + t.arr::time without time zone) >= d.starttime::double precision 
      AND date_part('hour'::text, v.dep::interval + t.arr::time without time zone) <= (d.sluttime - 1)::double precision
	 WHERE drift.importid_get_kpl(v.importid)::text = 'K24'::text 
	  AND d.tidsinterval::text = 'Døgn'::text 
	  AND vjt.trafikart <> 'Flexbus'::text 
	  AND vjt.trafikart <> 'Skolebus'::text 
	  AND vjt.trafikart <> 'Dublering'::text
 	), 
	
	-- Lav kolonner 250, 500 og 1000 om til rækker med attribute 'distance' og 'stander_list'
	unionized AS MATERIALIZED (
	 SELECT befolkning_2024_allnearbystops.id,
		250 AS distance,
		befolkning_2024_allnearbystops.stops_250 AS stander_list
	   FROM grunddata.befolkning_2024_allnearbystops
	UNION ALL
	 SELECT befolkning_2024_allnearbystops.id,
		500 AS distance,
		befolkning_2024_allnearbystops.stops_500 AS stander_list
	   FROM grunddata.befolkning_2024_allnearbystops
	UNION ALL
	 SELECT befolkning_2024_allnearbystops.id,
		1000 AS distance,
		befolkning_2024_allnearbystops.stops_1000 AS stander_list
	   FROM grunddata.befolkning_2024_allnearbystops
	), 
	
	-- cross join med kørselsdagtype så hvert kvadrat har 9 rækker, hver kombination af (Hverdag, Lørdag, Søndag) og (250, 500, 1000)
	crossed AS MATERIALIZED (
	 SELECT unionized.id,
		unionized.distance,
		unionized.stander_list,
		d.ugedag
	   FROM unionized
		 CROSS JOIN ( VALUES ('Hverdag'::text), ('Lørdag'::text), ('Søndag'::text)) d(ugedag)
	), 

	-- standerlisten for hvert kvadrat splittes til en række per stander
	-- ex. (kvadrat1, 1;2;3) bliver til (kvadrat1, 1), (kvadrat1, 2), (kvadrat1, 3)
	unnested AS MATERIALIZED (
	 SELECT crossed.id,
		crossed.distance,
		crossed.ugedag,
		NULLIF(unnest(regexp_split_to_array(crossed.stander_list::text, ';'::text)), ''::text) AS standernummer
	   FROM crossed
	)
	
 -- join kvadrater med (kvadrat id, stander id) og (stander id, ITCS)
 -- og tæl antal unikke ITCS per kvadrat, distance og kørselsdagtype
 SELECT row_number() OVER () AS gid,
    b.id,
    b.antal_tal,
    b.antal_txt,
    b.the_geom, -- befolkningskvadratnet polygon geometri
    u.distance, -- distance: 250, 500 eller 1000
    u.ugedag, -- kørselsdagtype: Hverdag, Lørdag eller Søndag
    COUNT(DISTINCT si.itcs) AS "afgange_døgn", -- antal unikke ITCS per døgn
    FLOOR(count(DISTINCT si.itcs)::numeric / 24.0) AS afgange_time,
    COUNT(DISTINCT si.standernummer) AS standere, -- antal standere
    SUM(CASE WHEN si.trafikart = ANY (ARRAY['Bus'::text, 'Bybus'::text, 'Natbus'::text, 'X-bus'::text]) THEN 1 ELSE 0 END) AS bus, -- antal bus afgange
    SUM(CASE WHEN si.trafikart = ANY (ARRAY['Letbane'::text, 'Lokalbane'::text]) THEN 1 ELSE 0 END) AS letbane_lokalbane -- antal letbane/lokaltog afgange
 FROM grunddata.befolkning_2024 b
 LEFT JOIN unnested u ON b.id = u.id
 LEFT JOIN stander_itcs si ON u.ugedag = si.ugedag::text AND u.standernummer = si.standernummer
 GROUP BY b.id, b.antal_tal, b.antal_txt, b.the_geom, u.distance, u.ugedag
 ORDER BY b.id, u.distance, u.ugedag
WITH DATA;

COMMENT ON MATERIALIZED VIEW grunddata.mvw_befolkning_2024_allnearbystops
    IS 'Bruges til laget: befolkning_2024';