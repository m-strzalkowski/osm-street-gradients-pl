#This is not fully automated! (yet?)
podman compose up -d
#Dostep do bazy z hosta:
psql -U postgres -p 5439 -h localhost -d osm

#Z kontenera drugiego:
psql -U postgres -p 5432 -h postgis -d osm

#Wykonanie obliczeń:
podman exec -it 10-osm-street-gradients-pl_geotools_1 bash
#Wewnątrz:
podman exec 10-osm-street-gradients-pl_geotools_1 bash data/main_geotools.sh
