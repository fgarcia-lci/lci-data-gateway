# TO_DO: auth-server ligero (client credentials, IEC 62443)

Objetivo: tener un servicio de emision de tokens para acceso sistema-a-sistema (client credentials) y que `gateway-api` solo valide. Separar responsabilidades, facilitar rotacion y cumplir principios IEC 62443 (auth centralizada, minimo privilegio, trazabilidad).

## Resumen de lo acordado
- Modelo de acceso: tokens por aplicacion (no por usuario), OAuth2 client credentials.
- Tokens JWT firmados (RS256/ES256), cortos (5–15 min), con claims `iss`, `aud`, `exp`, `client_id`, `scope/roles`.
- Auth-server expone `/token` (emite) y `/jwks.json` (publica claves). Lleva inventario de clients con scopes.
- Gateway valida (firma via JWKS, `aud`, `exp`, `scope`) y aplica RBAC por scopes.
- Secrets/keys fuera de repo; rotacion y revocacion posibles sin tocar el gateway.

## Tareas para auth-server
1) Estructura y dependencias:
   - Stack ligero (Node/Express o similar).
   - Libreria JWT (ej. `jose` o `jsonwebtoken`), generacion de JWKs (par RSA/EC).
   - Config por env: `ISSUER`, `AUDIENCE`, `TOKEN_TTL`, `PRIVATE_KEY` o ruta a key, lista de clients.
2) Modelo de clients:
   - Al inicio, lista en JSON/ENV: `client_id`, `client_secret` (hash preferible), `scopes` permitidos, `status` (activo/revocado).
   - Futuro: mover a DB o vault.
3) Endpoint `/token` (grant type client_credentials):
   - Valida `client_id`/`client_secret` (o header Basic).
   - Verifica que el client esté activo y que solicite solo scopes permitidos.
   - Emite JWT con `sub`/`client_id`, `scope`, `aud`, `iss`, `iat`, `exp` (TTL corto).
4) Endpoint `/jwks.json`:
   - Publica la clave publica actual (y opcionalmente las anteriores para rotacion).
5) Rotacion y revocacion:
   - Soportar multiple `kid` para rotar llaves sin downtime.
   - Permitir desactivar un `client_id` o revocar (lista de revocados cargada desde config).
6) Seguridad:
   - TLS en despliegue (terminacion en reverse proxy/ingress).
   - No correr como root en el contenedor; imagen base slim.
   - Logs con `client_id`, scope solicitado, resultado (sin exponer secretos).

## Tareas para gateway-api
1) Middleware JWT:
   - Validar firma via `JWKS_URI`, validar `aud` y `iss`.
   - Requerir scopes configurables (`REQUIRED_SCOPES_DEVICES`, `REQUIRED_SCOPES_HISTORY`, etc.).
   - Rechazar tokens expirados o sin scopes.
2) Config por entorno:
   - `JWKS_URI`, `JWT_AUD`, `JWT_ISS`, `REQUIRED_SCOPES_*`.
   - `MONGO_URI`, `MYSQL_*` ya deberían venir por env (no hardcoded).
3) CORS y exposicion:
   - Restringir `origin` en CORS.
   - Mantener TLS en front/proxy.
4) Rate limiting y logging:
   - Limitar por `client_id`/IP.
   - Logs de acceso con `client_id`, endpoint, status (para trazabilidad IEC 62443).

## Flujo final (produccion)
1) Registrar aplicacion en auth-server -> obtiene `client_id`/`client_secret` y scopes.
2) La app llama a `/token` con grant client_credentials -> recibe JWT corto.
3) La app llama a `gateway-api` con `Authorization: Bearer <token>`.
4) `gateway-api` valida via JWKS + `aud`/`scope` y responde.
5) Rotacion de llaves y revocacion gestionadas en auth-server sin cambios en gateway.

## Notas IEC 62443
- Identificacion y autenticacion centralizadas; tokens cortos; minimo privilegio (scopes).
- Segregacion de redes y TLS obligatorio.
- Auditoria y trazabilidad por `client_id`.
- Secrets y llaves gestionadas fuera del repositorio (vault/secrets), rotables.
