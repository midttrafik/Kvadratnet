SELECT stopnummer, 
	   rejseplan_navn AS stopnavn,
	   geom AS geometry
FROM grunddata.mvw_aktuelle_stoppesteder
WHERE stoptype != 'Plustur knudepunkt'