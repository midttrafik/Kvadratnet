/**
* Vis de korteste veje fra resultatet.
* Viser kun korteste veje som findes (viser ikke tomme geometrier).
* Tilpas navne og kolonner efter behov.
* 'dist_total' kan bruges til at farvelægge vejene.
**/

CREATE MATERIALIZED VIEW IF NOT EXISTS cvr.mvw_cvr_midtjylland_shortestpath_line
TABLESPACE pg_default
AS
 SELECT a.*
   FROM ( SELECT row_number() OVER (ORDER BY b.gid) AS gid,
            d.the_geom, -- korteste vej linestring geometri
            b.fid,
            b.p_nummer,
            b."cvr nummer",
            b."cvr relati",
            b.virksomhed,
            b.hovedbranc,
            b.kommune,
            b."Årsbeskæ",
            b.kvartalsbe,
            b."månedsbes",
            b.kvt_info,
            b.md_info,
            b.aar_info,
            b.info,
            b.antal,
            d.dist_total,
            d.dist_path, -- evt fjern
            d.dist_input, -- evt fjern
            d.dist_stop, -- evt fjern
            d.stop_name,
            d.stop_id,
            d.stop_osmid, -- evt fjern
            d.osmid, -- evt fjern
            CASE WHEN d.dist_total >= 200000::double precision THEN 1 ELSE 0 END AS ukendt
           FROM cvr.cvr_midtjylland b
             JOIN cvr.cvr_midtjylland_shortestpath d ON b.id = d.id) a
  WHERE a.dist_total < 200000::double precision
WITH DATA;

COMMENT ON MATERIALIZED VIEW cvr.mvw_cvr_midtjylland_shortestpath_line
    IS 'CVR Midtjylland med korteste sti fra virksomheden til nærmeste stop.';
