
# LCI Data Gateway

Este entorno simula un OT Gateway con:

- Datos de tiempo real (MongoDB)
- Datos históricos (MySQL)
- Simulador de tags y estados
- Arquitectura modular y portable

## 🚀 Cómo levantar el entorno

```bash
docker-compose up --build
```

## 🧪 Servicios incluidos

- **MySQL**: Base de datos tipo Historian
- **MongoDB**: Cache de datos actuales, agregados, estados
- **Simulator**: Simula lecturas por minuto y estados
- **Microservicios Spring Boot**: Vacíos, listos para desarrollo

## 🔄 Migrar a entorno real

1. **Detén el simulador**:
   ```bash
   docker-compose stop simulator
   ```

2. **Cambia `application.yml` en `historian-api`**:
   ```yaml
   spring.datasource.url=jdbc:sqlserver://<host>:1433;databaseName=<db>
   ```

3. **Modifica conexión a MongoDB si se usará otro host**:
   Cambia `MONGO_URI` en `.env` o `docker-compose.yml`.

4. **Reinicia microservicios necesarios**:
   ```bash
   docker-compose up -d historian-api realtime-api gateway-api auth-server
   ```

Listo para usar con tus datos reales.
