# Divisor de gastos compartidos

**Autor:** Daniel Chacón
**Materia:** Programación Orientada a Datos, Licenciatura en Ciencia de Datos (UCA, Campus Rosario), 2026
**Trabajo:** TP2 individual

Aplicación de consola en Python que toma los gastos de un grupo (un viaje, una juntada, un departamento compartido), calcula cuánto puso y cuánto consumió cada persona, y devuelve **la lista de transferencias necesarias para quedar a mano**.

## 1. Problema, usuario y solución

**Problema.** Cuando un grupo comparte gastos, cada persona paga cosas distintas y no siempre para todos (un café para dos, un remis para tres, la cabaña para los cinco). Al final nadie sabe bien cuánto debe ni a quién. Hacerlo a mano en una planilla es lento, se cometen errores (gastos cargados dos veces, montos mal escritos, gente que no estaba) y suelen terminar haciéndose muchas transferencias cruzadas innecesarias.

**Usuario.** Cualquier persona que organiza los gastos de un grupo y quiere cerrar las cuentas de forma clara y verificable.

**Solución.** El programa:

1. lee los gastos desde un archivo **CSV o JSON**;
2. valida cada gasto y aparta los que tienen errores, **explicando el motivo**;
3. reparte cada gasto en partes iguales entre sus participantes;
4. calcula el saldo de cada persona (lo que pagó menos lo que consumió);
5. propone las transferencias para saldar las deudas (como máximo, una menos que la cantidad de personas);
6. comprueba que el resultado sea coherente y guarda todo en archivos CSV.

**Alcance de esta versión.** Los gastos se dividen **en partes iguales** y en **una sola moneda (pesos)**. Quedan fuera de esta versión los repartos por porcentaje o por montos distintos, las monedas múltiples y los pagos parciales ya realizados entre integrantes.

## 2. Funcionalidades y modo de uso

| Operación | Comando |
|---|---|
| Resumen completo con los datos de ejemplo (CSV) | `python src/main.py` |
| Usar el archivo JSON en lugar del CSV | `python src/main.py --datos data/gastos.json` |
| Cerrar cuentas solo de un período | `python src/main.py --desde 2026-07-11 --hasta 2026-07-12` |
| Ver el detalle de una persona | `python src/main.py --persona Bruno` |
| Usar otro grupo u otra carpeta de salida | `python src/main.py --grupo otro_grupo.json --salida resultados` |
| Ver la ayuda | `python src/main.py --help` |

Las opciones se pueden combinar (por ejemplo, `--persona` con `--desde` y `--hasta`). En macOS o Linux puede ser necesario escribir `python3` en lugar de `python`.

**Archivos que genera** (en `outputs/`, o en la carpeta indicada con `--salida`):

- `saldos.csv`: lo que pagó, consumió y el saldo de cada persona;
- `transferencias.csv`: quién le paga a quién, cuánto y a qué alias;
- `rechazados.csv`: gastos descartados con el motivo.

## 3. Datos

- **Origen:** datos **simulados** generados por `scripts/generar_datos.py`, con semilla fija (`2026`) para que sean reproducibles. Representan los gastos de un viaje de cinco amigos a Bariloche del 6 al 12 de julio de 2026. Las personas y los alias son inventados.
- **Licencia:** creados para este trabajo; se pueden usar libremente.
- **Unidad de análisis:** cada fila es **un gasto** pagado por una persona y compartido por uno o más integrantes del grupo.
- **Tamaño:** 62 filas (55 gastos correctos y 7 con errores puestos a propósito para probar la validación).
- **Variables:** `gasto_id`, `fecha`, `descripcion`, `pagador`, `monto` (en pesos) y `participantes`. El detalle está en [`data/README.md`](data/README.md).
- **Configuración del grupo:** `data/grupo.json` contiene el nombre del grupo y el alias de transferencia de cada integrante.

Para volver a generar los datos: `python scripts/generar_datos.py`.

## 4. Instalación y ejecución

Requisitos: **Python 3.10 o superior**. No usa bibliotecas externas, solo la biblioteca estándar (`csv`, `json`, `re`, `datetime`, `dataclasses`, `abc`, `argparse` y `unittest`).

```bash
git clone https://github.com/daniichaconn/tp2-chacon.git
cd tp2-chacon
python src/main.py
```

**Pruebas** (desde la carpeta raíz):

```bash
python -m unittest discover -s tests -v
```

## 5. Organización del código

```
tp2-chacon/
|-- README.md
|-- requirements.txt
|-- .gitignore
|-- src/
|   |-- main.py        # consola: lee argumentos, coordina el flujo y muestra resultados
|   |-- fuentes.py     # FuenteDatos (clase base) + FuenteCSV y FuenteJSON
|   |-- dominio.py     # clases Gasto y Grupo: reparto, saldos y transferencias
|   '-- pipeline.py    # validar -> limpiar -> filtrar -> calcular -> verificar -> guardar
|-- tests/             # pruebas con unittest
|-- data/              # datos de ejemplo (CSV, JSON, grupo) y su documentación
'-- scripts/
    '-- generar_datos.py
```

**Flujo de llamadas** (`pipeline.procesar`):

```
filas = fuente.cargar()                        # CSV o JSON -> misma representación
validar_esquema(filas)                         # ¿hay datos? ¿están todas las columnas?
validos, rechazados = limpiar_gastos(filas, grupo)
seleccionados = filtrar_periodo(validos, desde, hasta)
grupo.registrar(gasto)  (para cada gasto)
transferencias = grupo.transferencias()
verificar_resultado(grupo, transferencias)
guardar_resultados(resultado, carpeta)
```

**Decisiones de diseño:**

- **Abstracción de las fuentes.** `FuenteDatos` es una clase abstracta con el método `cargar()`. `FuenteCSV` y `FuenteJSON` lo implementan y devuelven lo mismo: una lista de diccionarios con valores de texto y `participantes` como lista. El resto del programa no sabe ni le importa de qué formato vino el dato (polimorfismo).
- **Clases del dominio.** `Gasto` (una `dataclass` inmutable) sabe repartirse entre sus participantes. `Grupo` guarda los integrantes y los gastos, y calcula los saldos y las transferencias.
- **Plata en centavos enteros.** Todos los importes se guardan como `int` en centavos, porque con `float` aparecen errores de redondeo (en Python, `0.1 + 0.2` da `0.30000000000000004`). Cuando un monto no se divide justo (por ejemplo, $10 entre 3), los centavos que sobran se asignan de a uno, en orden alfabético. Así **la suma de las partes es siempre igual al total**.
- **Funciones sin efectos secundarios.** La limpieza y los cálculos no escriben archivos ni modifican la entrada. Solo `cargar()` y `guardar_resultados()` tocan el disco, lo que permite probar los cálculos sin archivos.

## 6. Expresiones regulares

| Campo | Patrón | Qué valida |
|---|---|---|
| `gasto_id` | `G\d{3}` | una G seguida de 3 dígitos (G001) |
| `fecha` | `\d{4}-\d{2}-\d{2}` | formato AAAA-MM-DD |
| `monto` | `\d+(\.\d{1,2})?` | número positivo, con punto decimal y hasta 2 decimales |
| alias | `[a-z0-9.\-]{6,20}` | alias de transferencia: 6 a 20 minúsculas, números, puntos o guiones |

Se usa `re.fullmatch`, que exige que **todo** el texto cumpla el patrón. Una regex solo controla la *forma*: `2026-02-29` cumple el patrón de fecha pero no existe. Por eso, después de la regex, la fecha se convierte con `datetime.strptime`, que controla el calendario (y acepta `2024-02-29`, porque 2024 es bisiesto).

## 7. Ejemplo de resultado

`python src/main.py --desde 2026-07-11 --hasta 2026-07-12`

```
=== Viaje a Bariloche - julio 2026 ===
Filas leídas: 62 | válidas: 54 | rechazadas: 8 | en el período: 15
Total gastado en el período: $ 980.571,71

Persona               Pagó        Consumió           Saldo
Ana           $ 251.686,50    $ 200.843,13     $ 50.843,37
Bruno         $ 170.786,25    $ 188.851,52    -$ 18.065,27
Carla         $ 186.485,99    $ 229.941,12    -$ 43.455,13
Diego          $ 23.820,00    $ 167.912,99   -$ 144.092,99
Elena         $ 347.792,97    $ 193.022,95    $ 154.770,02
(saldo positivo: le deben plata | negativo: debe plata)

Transferencias para quedar a mano:
  Diego -> Elena: $ 144.092,99  (alias: elena.pagos)
  Carla -> Ana: $ 43.455,13  (alias: ana.viaja.mp)
  Bruno -> Elena: $ 10.677,03  (alias: elena.pagos)
  Bruno -> Ana: $ 7.388,24  (alias: ana.viaja.mp)
```

**Cómo se interpreta.** En esos dos días, Elena puso $ 154.770,02 más de lo que consumió, así que el grupo le debe esa plata. Diego consumió mucho más de lo que pagó y le transfiere a Elena. Con **4 transferencias** quedan los 5 a mano. Sin el programa, cada uno le pagaría a cada pagador por cada gasto, y serían muchas más.

## 8. Decisiones de limpieza

Una fila se **rechaza entera** si tiene al menos un problema. Se guarda en `rechazados.csv` con todos sus motivos:

| Problema | Ejemplo en los datos | Decisión |
|---|---|---|
| id con formato inválido | `G9` | rechazar |
| id repetido | `G011` cargado dos veces | rechazar **las dos** filas: no se sabe cuál es la buena |
| fecha inexistente | `2026-06-31` | rechazar |
| monto con formato inválido | `1.500,00`, `-2500` | rechazar (no se adivina qué quiso escribir) |
| persona fuera del grupo | pagador `Franco` | rechazar |
| gasto sin participantes | `Propina` sin nadie | rechazar |

El programa **se detiene con un mensaje claro** si el archivo no existe, si el JSON está mal formado o no es una lista de objetos, si faltan columnas, si no hay datos, si ningún gasto es válido o si el período pedido está invertido.

**Verificaciones del resultado** (`verificar_resultado`), que deben cumplirse siempre:

- la suma de todos los saldos es exactamente 0;
- lo consumido por todos suma el total gastado;
- aplicando las transferencias, todos quedan en 0;
- hay como máximo (cantidad de personas − 1) transferencias.

## 9. Pruebas

`tests/` contiene 40 pruebas con `unittest`:

- **casos normales:** reparto exacto, saldos y transferencias de un caso calculado a mano, gastos cruzados que se compensan;
- **entradas inválidas y límites:**
  - cada regla de rechazo;
  - el 29/02 en año bisiesto y no bisiesto;
  - montos negativos o con coma;
  - archivo inexistente, JSON roto, formato no soportado;
  - período invertido o sin gastos;
  - una persona inexistente;
- **propiedades:**
  - las partes de un gasto suman el total;
  - los saldos suman 0;
  - las transferencias dejan a todos en 0;
  - nunca hay más de n − 1 transferencias;
  - **CSV y JSON producen exactamente el mismo resultado**;
  - entrada = válidos + rechazados;
  - la limpieza no modifica los datos originales.

## 10. Limitaciones

- Reparto solo en partes iguales y en una sola moneda.
- El método de transferencias garantiza como máximo n − 1, pero **no siempre el mínimo absoluto**: si dentro del grupo hay subgrupos cuyas deudas se cancelan entre sí, podría existir una solución con menos transferencias. Encontrar siempre la mínima es un problema mucho más costoso de calcular, y para grupos chicos esta aproximación alcanza.
- La regex del alias controla el formato, no que el alias exista realmente.
- Los datos de ejemplo son simulados: sirven para demostrar y probar el programa, no describen gastos reales.

## Versión evaluada

La versión entregada se identifica con la etiqueta `v1.0` del repositorio.
