/**
* Vis befolkningskvadratnet med attributterne 'dist_total', 'stop_name' og 'stop_id' fra resultatet.
* ukendt=1 hvis der ikke findes et nærmeste stop, ellers ukendt=0.
* Tilpas navne og kolonner efter behov.
* 'dist_total' kan bruges til at farvelægge kvadraterne.
**/

CREATE MATERIALIZED VIEW IF NOT EXISTS grunddata.mvw_befolkning_2024_shortestpath
TABLESPACE pg_default
AS
 SELECT row_number() OVER (ORDER BY b.gid) AS gid,
    b.the_geom, -- befolkningskvadratnet polygon geometri
    b.antal_tal,
    b.antal_txt,
    ROUND(d.dist_total, 2) AS dist_total,
    ROUND(d.dist_path, 2) AS dist_path, -- evt fjern
    ROUND(d.dist_input, 2) AS dist_input, -- evt fjern
    ROUND(d.dist_stop, 2) AS dist_stop, -- evt fjern
    d.stop_name,
    d.stop_id,
    d.stop_osmid, -- evt fjern
    d.osmid, -- evt fjern
    CASE WHEN d.dist_total >= 200000::double precision THEN 1 ELSE 0 END AS ukendt
   FROM grunddata.befolkning_2024 b
     JOIN grunddata.befolkning_2024_shortestpath d ON b.id = d.id
WITH DATA;

COMMENT ON MATERIALIZED VIEW grunddata.mvw_befolkning_2024_shortestpath
    IS 'Befolkningsdata 2024 med nærmeste stop';