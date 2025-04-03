/**
* Vis uddannelsesinstitutioner med attributterne 'dist_total', 'stop_name' og 'stop_id' fra resultatet.
* ukendt=1 hvis der ikke findes et nærmeste stop, ellers ukendt=0.
* Tilpas navne og kolonner efter behov.
* 'dist_total' kan bruges til at farvelægge punkter.
**/

CREATE MATERIALIZED VIEW IF NOT EXISTS uddannelsesinstitutioner.mvw_uddannelsesinstitutioner_elevtal_2023_2024_shortestpath
TABLESPACE pg_default
AS
 SELECT row_number() OVER (ORDER BY b.gid) AS gid,
    b.id,
    b.the_geom, -- uddannelsesinstitution punkt geometri
    b.elevtal_20,
    b.afdeling,
    b.afdelingsn,
    b.institutio,
    b.institut_1,
    b.inst_nr,
    b.inst_navn,
    b.inst_type_,
    b.geo_bredde,
    b.geo_laengd,
    b.styling,
    d.dist_total,
    d.dist_path, -- evt fjern
    d.dist_input, -- evt fjern
    d.dist_stop, -- evt fjern
    d.stop_name,
    d.stop_id,
    d.stop_osmid, -- evt fjern
    d.osmid, -- evt fjern
    CASE WHEN d.dist_total >= 200000::double precision THEN 1 ELSE 0 END AS ukendt
   FROM uddannelsesinstitutioner.uddannelsesinstitutioner_elevtal_2023_2024_25832 b
     JOIN uddannelsesinstitutioner.uddannelsesinstitutioner_elevtal_2023_2024_25832_shortestpath d ON b.id = d.id
WITH DATA;

COMMENT ON MATERIALIZED VIEW uddannelsesinstitutioner.mvw_uddannelsesinstitutioner_elevtal_2023_2024_shortestpath
    IS 'Uddannelsesinstitutioner elevtal (2023/2024) med distance til nærmeste stop.';