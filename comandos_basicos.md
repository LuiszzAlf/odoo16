build dockerfile:  docker build -t odoo10 -f Dockerfile .
entras con root : docker exec -u root -t -i container_id /bin/bash
docker exec -it <container-id> psql -U <username> -d postgres -c "DROP DATABASE <dbname>;"   ----elimina base de datos en contenedor postgresql
docker exec -it db12ee psql -U odoo -d postgres -c "DROP DATABASE agro_qas;"
docker exec -it <container-id> psql -U <username> -d postgres -c "CREATE DATABASE <dbname>;"
docker exec -u root -t -i odoo_10 /etc/init.d/odoo restart
docker exec -u root -t -i odoo10 /bin/bash

