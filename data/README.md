# Datos

Datos **simulados** para demostrar y probar el divisor de gastos. Se generan con:

```bash
python scripts/generar_datos.py
```

El script usa la semilla `2026`, así que cada ejecución produce exactamente los mismos archivos.

## Archivos

| Archivo | Contenido |
|---|---|
| `gastos.csv` | los gastos en CSV (separado por comas, UTF-8) |
| `gastos.json` | los **mismos** gastos en JSON: una lista de objetos, uno por gasto |
| `grupo.json` | nombre del grupo e integrantes con su alias de transferencia |

## Unidad de análisis

Cada fila es **un gasto**: lo pagó una persona, pertenece a un evento y se reparte en partes iguales entre los participantes.

## Variables

| Columna | Tipo | Descripción | Ejemplo |
|---|---|---|---|
| `gasto_id` | texto | identificador único: G + 3 dígitos | `G001` |
| `fecha` | texto | fecha del gasto, formato AAAA-MM-DD | `2026-07-27` |
| `evento` | texto | salida o viaje al que pertenece | `Viaje a Bariloche` |
| `categoria` | texto | una de: Alojamiento, Transporte, Supermercado, Comidas y bebidas, Actividades y entradas, Regalos, Otros | `Transporte` |
| `descripcion` | texto | en qué se gastó | `Pasajes de avión` |
| `pagador` | texto | quién pagó (debe ser integrante) | `Ana` |
| `monto` | número | importe en **pesos argentinos**, punto decimal, hasta 2 decimales | `23456.5` |
| `participantes` | lista | entre quiénes se divide. En CSV, nombres separados por `;`; en JSON, una lista | `Ana;Bruno` |

## Cómo se generan

Seis amigos (Ana, Bruno, Carla, Diego, Elena y Facundo) a lo largo de 2026 (enero a octubre), en 8 eventos. Cada evento tiene sus propios integrantes:

| Evento | Fechas | Quiénes |
|---|---|---|
| Vacaciones en Mar del Plata | 12 al 21 de enero | Ana, Bruno, Carla, Diego, Elena |
| Finde largo en Córdoba | 14 al 17 de febrero | Ana, Carla, Diego, Facundo |
| Asados del grupo | uno por mes, de enero a octubre | entre 4 y 6, al azar |
| Cumpleaños de Bruno | abril | todos (el regalo lo pagan todos menos Bruno) |
| Mundial 2026: partidos de Argentina | 7 juntadas, junio y julio | entre 4 y 6, al azar |
| Viaje a Bariloche | 27 de julio al 2 de agosto | Ana, Bruno, Carla, Diego, Elena |
| Cumpleaños de Elena | agosto | todos (el regalo lo pagan todos menos Elena) |
| Recital en Buenos Aires | 26 y 27 de septiembre | Bruno, Elena, Facundo |

- En los viajes hay un gasto de alojamiento y uno de traslado al principio, y varios gastos por día.
- Cada tipo de gasto (supermercado, cena, remis, etc.) tiene un rango de montos y una categoría fijos. El pagador y los participantes se eligen al azar entre los integrantes del evento.
- En total hay **306 gastos correctos**. Al final se agregan **12 filas con errores a propósito**: id duplicado, id mal escrito, fecha inexistente, fecha con otro formato, monto con coma, negativo o cero, persona fuera del grupo, sin participantes, participantes repetidos, categoría desconocida y evento vacío.

## Limitaciones

Los montos, las personas y las fechas de los partidos son inventados: los datos no representan gastos ni precios reales. No incluyen información personal.
