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

Cada fila es **un gasto**: lo pagó una persona y se reparte en partes iguales entre los participantes.

## Variables

| Columna | Tipo | Descripción | Ejemplo |
|---|---|---|---|
| `gasto_id` | texto | identificador único: G + 3 dígitos | `G001` |
| `fecha` | texto | fecha del gasto, formato AAAA-MM-DD | `2026-07-06` |
| `descripcion` | texto | en qué se gastó | `Supermercado` |
| `pagador` | texto | quién pagó (debe ser integrante) | `Ana` |
| `monto` | número | importe en **pesos argentinos**, punto decimal, hasta 2 decimales | `23456.5` |
| `participantes` | lista | entre quiénes se divide. En CSV, nombres separados por `;`; en JSON, una lista | `Ana;Bruno` |

## Cómo se generan

- 5 personas (Ana, Bruno, Carla, Diego y Elena) durante 7 días (6 al 12 de julio de 2026).
- Un gasto fijo de alojamiento pagado por Ana para todos, más 7 a 10 gastos por día.
- Cada gasto tiene un tipo (supermercado, nafta, cena, remis, etc.) con un rango de montos realista para ese tipo, un pagador al azar y participantes al azar.
- Al final se agregan **7 filas con errores a propósito** (id mal escrito, id duplicado, fecha inexistente, monto con coma, monto negativo, persona fuera del grupo y gasto sin participantes) para mostrar la validación.

## Limitaciones

Los montos y las personas son inventados: los datos no representan gastos reales ni precios reales de Bariloche. Los datos no incluyen información personal.
