#This is not fully automated! (yet?)
docker compose up -d
#Dostep do bazy z hosta:
psql -U postgres -p 5439 -h localhost -d osm

#Z kontenera drugiego:
psql -U postgres -p 5432 -h postgis -d osm

#Wykonanie obliczeń:
docker exec -it 10-osm-street-gradients-pl-geotools-1 bash
#Wewnątrz:
docker exec 10-osm-street-gradients-pl-geotools-1 bash data/main_geotools.sh