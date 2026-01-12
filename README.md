# LCI Data Gateway

Entorno para simular un OT Gateway con datos en tiempo real (MongoDB), historicos (MySQL) y un simulador de tags/estados.

## Como levantar el entorno
```bash
docker-compose up --build
```

## Servicios incluidos
- **MySQL**: base de datos tipo Historian
- **MongoDB**: cache de datos actuales, agregados, estados
- **Simulator**: genera lecturas periodicas y cambios de estado
- **Microservicios Spring Boot**: vacios, listos para desarrollo

### Configurar devices y tags
- Edita `mongodb/devices.json` para agregar devices/tags y sus parametros de simulacion.
- Reinicia con `docker-compose down && docker-compose up --build` para aplicar el JSON.

## Migrar a entorno real
1. **Deten el simulador**:
   ```bash
   docker-compose stop simulator
   ```
2. **Cambia `application.yml` en `historian-api`**:
   ```yaml
   spring.datasource.url=jdbc:sqlserver://<host>:1433;databaseName=<db>
   ```
3. **Modifica conexion a MongoDB si usas otro host**:
   Ajusta `MONGO_URI` en `.env` o `docker-compose.yml`.
4. **Reinicia microservicios necesarios**:
   ```bash
   docker-compose up -d historian-api realtime-api gateway-api auth-server
   ```

Listo para usar con tus datos reales.
