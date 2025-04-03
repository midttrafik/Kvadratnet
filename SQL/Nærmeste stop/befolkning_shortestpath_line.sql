/**
* Vis de korteste veje fra resultatet.
* Viser kun korteste veje som findes (viser ikke tomme geometrier).
* Tilpas navne og kolonner efter behov.
* 'dist_total' kan bruges til at farvelægge vejene.
**/

CREATE MATERIALIZED VIEW IF NOT EXISTS grunddata.mvw_befolkning_2024_shortestpath_line
TABLESPACE pg_default
AS
 SELECT a.*
   FROM ( 
	   SELECT row_number() OVER (ORDER BY b.gid) AS gid,
            d.the_geom, -- korteste vej linestring geometri
            b.antal_tal,
            b.antal_txt,
            d.dist_total,
            d.dist_path, -- evt fjern
            d.dist_input, -- evt fjern
            d.dist_stop, -- evt fjern
            d.stop_name,
            d.stop_id,
            d.stop_osmid, -- evt fjern
            d.osmid, -- evt fjern
            CASE WHEN d.dist_total >= 200000::double precision THEN 1 ELSE 0 END AS ukendt
           FROM grunddata.befolkning_2024 b
             JOIN grunddata.befolkning_2024_shortestpath d ON b.id = d.id) a
  WHERE a.dist_total < 200000::double precision
WITH DATA;

COMMENT ON MATERIALIZED VIEW grunddata.mvw_befolkning_2024_shortestpath_line
    IS 'Bruges til laget: Befolkning 2024 distance';