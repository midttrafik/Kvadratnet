/**
* Vis de korteste veje fra resultatet.
* Viser kun korteste veje som findes (viser ikke tomme geometrier).
* Tilpas navne og kolonner efter behov.
* 'dist_total' kan bruges til at farvelægge vejene.
**/

CREATE MATERIALIZED VIEW IF NOT EXISTS uddannelsesinstitutioner.mvw_uddannelsesinstitutioner_elevtal_20232024_shortestpath_line
TABLESPACE pg_default
AS
 SELECT a.*
   FROM ( SELECT row_number() OVER (ORDER BY b.gid) AS gid,
            b.id,
            d.the_geom, -- korteste vej linestring geometri
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
            ROUND(d.dist_total, 2) AS dist_total,
            ROUND(d.dist_path, 2) AS dist_path, -- evt fjern
            ROUND(d.dist_input, 2) AS dist_input, -- evt fjern
            ROUND(d.dist_stop, 2) AS dist_stop, -- evt fjern
            d.stop_name,
            d.stop_id,
            d.stop_osmid, -- evt fjern
            d.osmid, -- evt fjern
		    CASE WHEN d.dist_total >= 200000::double precision THEN 1 ELSE 0 END AS ukendt
           FROM uddannelsesinstitutioner.uddannelsesinstitutioner_elevtal_2023_2024_25832 b
             JOIN uddannelsesinstitutioner.uddannelsesinstitutioner_elevtal_2023_2024_25832_shortestpath d ON b.id = d.id) a
  WHERE a.dist_total < 200000::double precision
WITH DATA;

COMMENT ON MATERIALIZED VIEW uddannelsesinstitutioner.mvw_uddannelsesinstitutioner_elevtal_20232024_shortestpath_line
    IS 'Uddannelsesinstitutioner elevtal (2023/2024) med stien til nærmeste stoppested på vejnettet.';