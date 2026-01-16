#This is not fully automated! (yet?)
docker compose up
#Dostep do bazy z hosta:
psql -U postgres -p 5439 -h localhost -d osm

#Z kontenera drugiego:
psql -U postgres -p 5432 -h postgis -d osm

#Wykonanie obliczeń:
docker exec -it osm-street-gradients-pl-geotools-1 bash
#Wewnątrz:
bbox="50.02667 50.08243 19.89064 19.96891"
./download_nmt.sh $bbox
python download_nmpt.py $bbox
./download_ways.sh $bbox
./compute_gradients.sh