# Guia rapida: agregar devices y propiedades via JSON

Todo se configura en **un unico fichero JSON**: `mongodb/devices.json`. El simulador lo lee al arrancar, sincroniza MongoDB y genera valores para MySQL/Mongo sin tocar codigo.

## Donde editar
- `mongodb/devices.json` -> define devices, tags, parametros de simulacion y `hist_tags` (tag original del historian si se renombra).
- `docker-compose.yml` ya monta ese fichero en MongoDB y en el simulador.

Tras editar el JSON, reinicia con:
```bash
docker-compose down
docker-compose up --build
```

## Formato del fichero `mongodb/devices.json`
Cada elemento del array es un device:
```json
{
  "device_id": "S_NEW_01",
  "name": "Motor de prueba",
  "xeokit_id": 6001,
  "tags": ["Motor4_Temp", "Motor4_Speed", "Motor4_Vibration"],
  "hist_tags": ["Motor4.Temp", "Motor4.Speed", "Motor4.Vibration"],  // opcional, referencia al tag original
  "status": "RUNNING",
  "status_timestamp": "2025-07-16T08:00:00Z",
  "sim": {
    "Temp":  { "base": 70,  "variation": 12,  "min": 30,  "max": 120,  "unit": "C",   "precision": 1 },
    "Speed": { "base": 1750,"variation": 180, "min": 500, "max": 3500, "unit": "RPM","precision": 0 },
    "Vibration": { "base": 0.5, "variation": 0.2, "min": 0, "max": 5, "unit": "mm/s", "precision": 2 }
  }
}
```
Claves importantes:
- `device_id`: unico.
- `tags`: lista de tags que generara el device. El tipo se deduce del ultimo segmento despues de normalizar (se reemplazan `.` por `_`). Ej: `Motor4_Temp` -> tipo `Temp`; `G_BC_27.SDDevCtl.St.PV` se normaliza a `G_BC_27_SDDevCtl_St_PV` y el tipo es `PV`.
- `hist_tags`: opcional; guarda el nombre original del historian para referencia.
- `sim`: tabla por tipo de tag. Si falta un tipo, usa los defaults internos.
- Parametros por tipo:
  - `base`: valor base.
  - `variation`: amplitud de la variacion sinusoidal.
  - `min` / `max`: limites (opcional).
  - `unit`: unidad corta (se guarda en MySQL y Mongo).
  - `precision`: decimales al redondear.

## Agregar un device nuevo (solo JSON)
1) Abre `mongodb/devices.json` y anade el nuevo objeto con sus `tags` (sin puntos o con puntos; el simulador los normaliza) y su bloque `sim`.
2) Asegura que `device_id` y `xeokit_id` sean unicos y que los `tags` sean descriptivos.
3) (Opcional) Pon `hist_tags` si quieres mantener el nombre original del historian.
4) Reinicia con `docker-compose down && docker-compose up --build`.

El simulador:
- Subira automaticamente el device a MongoDB si no existe.
- Empezara a generar datos historicos (MySQL) y valores actuales (Mongo).

## Agregar nuevas propiedades/tags a un device
1) En `tags` agrega el nuevo tag, siguiendo la convencion `{Equipo}_{Propiedad}` o el tag original con puntos (se normaliza internamente).
2) En `sim`, agrega la entrada para ese tipo (`Current`, `Pressure`, `PV`, etc.) con sus parametros.
3) Reinicia los servicios.

Defaults actuales si no defines `sim` para un tipo:
- `Temp`: base 70, variation 15, min 30, max 120, unit C, precision 1.
- `Speed`: base 1800, variation 200, min 500, max 3500, unit RPM, precision 0.
- `PV`: base 50, variation 20, min 0, max 100, unit %, precision 1.
- `Power`: base 10, variation 3, min 0, max 1000, unit kW, precision 1.
Otros tipos sin config tendran variacion minima y unidad `unit`.

## Ejemplos rapidos de tipos
- `Vibration`: base 0.5, variation 0.2, min 0, max 5, unit mm/s, precision 2.
- `Pressure`: base 100, variation 10, min 50, max 150, unit bar, precision 1.
- `Current`: base 10, variation 3, min 0, max 50, unit A, precision 1.
- `Flow`: base 800, variation 120, min 0, max 1500, unit L/min, precision 0.
- `PV`: base 50, variation 20, min 0, max 100, unit %, precision 1 (valor de proceso tipo consigna/medida).
- `Power`: base segun potencia en kW del equipo, variation ~10%, min 0, max base*1.2, unit kW.

## Checklist
- [ ] Nuevo device y tags agregados en `mongodb/devices.json` (con `hist_tags` si los renombraste).
- [ ] Cada tipo de tag tiene configuracion en `sim` o usa defaults.
- [ ] `device_id` y `xeokit_id` sin duplicados.
- [ ] Reiniciado `docker-compose` para aplicar el JSON.

## Troubleshooting
- **No aparecen datos del nuevo device**: revisa ortografia de `device_id` y `tags` en el JSON (puntos se normalizan a `_`), y mira `docker-compose logs -f simulator`.
- **Tags nuevos no salen en la API**: comprueba `db.current_values.find()` en Mongo y reinicia `gateway-api` si persiste.
- **Valores raros**: ajusta `base`, `variation`, `min/max` o `precision` para el tipo en `sim`.
