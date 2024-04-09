# Dependencias
# Install base image
```bash
    docker-compose build
```
# Start base image
```bash
    docker-compose up
```
# Entrar al contenedor odoo10

```bash
docker exec -u root -t -i odoo10 /bin/bash
```
# Ejecutar en contenedor odoo10
```bash
apt update -y
```
```bash
apt install python-pandas locales -y
locale-gen es_MX.UTF-8
echo "LANG=es_MX.UTF-8" > /etc/default/locale
``` 

## Contributing
En caso de agregar mas librerias edite este archivo

## License
