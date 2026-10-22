# temporal-graph: documentación

`temporal-graph` modela grafos cuyos enlaces cambian a través del tiempo,
permite analizarlos y los representa como SVG, PNG o GIF animados. La
documentación incluye tanto la referencia completa de la API como guías basadas
en los programas ejecutables incluidos en `examples/`.

Un grafo temporal contiene un *snapshot* por instante. Una arista que no se
declara en un snapshot está desconectada en ese instante; para que vuelva a
aparecer debe declararse nuevamente. Las aristas pueden ser dirigidas y tener
peso y color.

## Contenido

### Referencia de API

| Página | Módulos y capacidades |
| --- | --- |
| [Modelo y visualización](api-core.md) | `Edge`, `TimeEdge`, `TemporalGraph`, renderizado SVG/PNG, `Figure`, animaciones GIF y `Animation`. |
| [Algoritmos](api-algorithms.md) | Journeys, conectividad, Menger temporal, expansión estática, difusión, diseño temporal y problemas clásicos exactos. |
| [Datos, modelos y utilidades](api-data.md) | Análisis, importación/exportación, transformaciones, generadores, disponibilidad periódica y modelos aleatorios. |

### Guías y material complementario

- [Ejemplos generales](examples.md)
- [Ejemplos de física](physics.md)
- [Notas teóricas: *Grafos temporales: una introducción desde la perspectiva algorítmica*](grafos_temporales.pdf)

## Requisitos e instalación

El paquete requiere Python 3.9 o posterior y no tiene dependencias de ejecución.
Desde la raíz del repositorio se puede instalar en modo editable con:

```bash
pip install -e ".[dev]"
```

Los ejemplos se ejecutan también desde la raíz. Cada uno crea `output/` si no
existe y deja allí sus figuras, animaciones o archivos de intercambio:

```bash
python examples/example.py
```

## Modelo temporal y convenciones

Los scripts son autocontenidos: construyen el grafo en una función
`build_graph()`, lo visualizan o analizan y escriben los resultados bajo
`output/`.

`Edge(origen, destino, directed=True)` representa una arista dirigida. El
argumento `weight` controla el peso visual: valores mayores que `1.0` se
dibujan como una línea de vida más enfática. `color` acepta colores CSS o
hexadecimales.

`render(grafo, modo)` genera una figura de línea de tiempo:

| Modo | Descripción |
| --- | --- |
| `connections` | Muestra el snapshot completo en cada instante. |
| `decisions` | Muestra apariciones, persistencias y desconexiones de aristas. |

Una figura se guarda con `figure.savefig(ruta)` en SVG o PNG. Para la vista
nodo-enlace se usa `animate(grafo)` y `Animation.save(ruta)` para crear un GIF.

### Instantes, snapshots y aristas

- Un timestep es un **instante** o etiqueta temporal. Un snapshot en `t`
  contiene exactamente las aristas disponibles en `t`.
- Un instante que no tiene snapshot registrado se interpreta sin aristas para
  journeys y métricas globales.
- `TemporalGraph.add_snapshot(t, edges)` reemplaza un snapshot existente en
  `t`; conserva los snapshots ordenados por instante.
- La identidad de una arista es el par no ordenado de extremos: dirección,
  color y peso no forman parte de ella. Por tanto, `u -> v` y `v -> u` no
  pueden coexistir en un mismo snapshot.
- Duplicados en un snapshot se eliminan y prevalece la primera declaración.
- No se permiten bucles ni nodos que no hayan sido declarados al construir el
  grafo.

### Journeys estrictos y no estrictos

Las funciones de `journeys` usan `strict=True` por defecto: los instantes de
las aristas cruzadas deben crecer estrictamente (`t1 < t2 < ...`). Con
`strict=False`, pueden encadenarse contactos del mismo instante
(`t1 <= t2 <= ...`). Cuando se omite `start`, el origen está disponible antes
del primer instante registrado para journeys estrictos, y en el primer instante
para los no estrictos.

### Importación principal

Los elementos centrales están disponibles directamente desde el paquete:

```python
from temporal_graph import Edge, TemporalGraph, TimeEdge, Journey
from temporal_graph import render, animate
from temporal_graph import analysis, connectivity, journeys
```

Los módulos `classic`, `design`, `dissemination`, `expansion`, `exporters`,
`flows`, `generators`, `periodic`, `random_models` y `utils` también se
exportan desde `temporal_graph`.
