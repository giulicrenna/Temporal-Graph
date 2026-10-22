# API: modelo y visualización

Esta página documenta `temporal_graph.graph`, `temporal_graph.render`,
`temporal_graph.figure` y `temporal_graph.animate`.

## `temporal_graph.graph`

### `Edge`

```python
Edge(u: str, v: str, directed: bool = False,
     weight: float = 1.0, color: str | None = None)
```

Arista declarada en un snapshot. `u` y `v` deben ser etiquetas de nodo distintas.
`weight` debe ser numérico y no negativo; `color` es una cadena CSS/hexadecimal
o `None`. En una arista dirigida, la dirección es `u -> v`.

| Método | Resultado |
| --- | --- |
| `key()` | Par canónico `(u, v)` que identifica la arista, sin dirección, peso ni color. |
| `canonical()` | Par de extremos ordenado lexicográficamente. |
| `other(node)` | El otro extremo; falla si `node` no pertenece a la arista. |
| `endpoints_in_order()` | `(u, v)` para aristas dirigidas; par canónico para no dirigidas. |
| `effective_color()` | El color declarado o `"#111111"` si no hay color. |

La igualdad y el hash de `Edge` usan `key()`: dos instancias con los mismos
extremos representan la misma arista lógica aunque sus atributos difieran.

### `TimeEdge`

```python
TimeEdge(u: str, v: str, t: int, directed: bool, weight: float)
```

Tupla con nombre que representa una disponibilidad `(arista, instante)` del
modelo λ. Para aristas no dirigidas, `u, v` se almacenan en orden canónico.
Se obtiene normalmente con `TemporalGraph.time_edges()`.

### `TemporalGraph`

```python
TemporalGraph(nodes: Sequence[str])
TemporalGraph.from_time_edges(nodes, time_edges, directed=False)
```

Contenedor mutable de snapshots ordenados. Requiere al menos un nodo, todos
etiquetados con cadenas únicas. `from_time_edges` recibe triples `(u, v, t)` y
construye aristas de atributos por defecto.

| Propiedad o método | Resultado y comportamiento |
| --- | --- |
| `nodes` | Copia de la lista de nodos, en el orden declarado. |
| `timesteps` | Lista ordenada de instantes con snapshot registrado, incluso si está vacío. |
| `add_snapshot(t, edges)` | Agrega o **reemplaza** el snapshot de `t`. Acepta únicamente `Edge`; elimina duplicados por identidad y conserva el primero. |
| `edges_at(t)` | Lista de `Edge` del snapshot; lanza `KeyError` si `t` no fue registrado. |
| `edge_at(t, key)` | Arista identificada por su par canónico; lanza `KeyError` si el instante o la arista no existen. |
| `snapshots()` | Lista de pares `(t, [Edge, ...])` ordenada. |
| `time_edges()` | Lista ordenada de `TimeEdge`, una por arista e instante. |
| `labels(u, v)` | Instantes en que la arista entre `u` y `v` está disponible. |
| `label_count` | Número total de pares arista-instante, `|λ|`. |
| `age` | `λ_max - λ_min + 1` sobre instantes con aristas; `0` si no hay aristas. |
| `change_events()` | Eventos `(t, "connect" | "disconnect", key)` entre snapshots **registrados** consecutivos. |
| `edge_intervals()` | Diccionario `key -> [(inicio, fin), ...]` con intervalos semiabiertos; fusiona sólo instantes consecutivos. |

## Renderizado de líneas de tiempo: `temporal_graph.render`

```python
render(graph: TemporalGraph, mode: str, path: str | PathLike | None = None)
```

Renderiza un grafo no vacío y devuelve una `Figure` si `path` es `None`; si se
indica una ruta, guarda el archivo y devuelve su ruta absoluta. `mode` admite:

| Modo | Representación |
| --- | --- |
| `"connections"` | Una columna por snapshot; dibuja todas las aristas activas. Las que persisten se atenúan. |
| `"decisions"` | Línea de vida de cada arista, más marcadores de conexión y desconexión. |

Ambos modos muestran dirección con flechas, colores por arista y un trazo
ondulado para pesos mayores que uno. Cada figura incluye su propia leyenda.
`render` lanza `ValueError` si el modo es desconocido o el grafo no tiene
snapshots.

Ejemplo:

```python
from temporal_graph import Edge, TemporalGraph, render

graph = TemporalGraph(["a", "b", "c"])
graph.add_snapshot(0, [Edge("a", "b")])
graph.add_snapshot(1, [Edge("a", "b", directed=True, weight=2, color="#d62728")])
render(graph, "decisions").savefig("output/timeline.svg")
```

## `Figure`

`Figure` es el resultado de `render` y de cada cuadro de una `Animation`.

| Propiedad o método | Resultado |
| --- | --- |
| `width` / `height` | Dimensiones SVG en unidades de usuario. |
| `to_svg()` | Documento SVG como `str`, incluida la declaración XML. |
| `to_png_bytes(scale=2.0)` | Rasteriza el SVG y devuelve bytes PNG. `scale` es píxeles por unidad SVG. |
| `savefig(path, format=None, scale=2.0)` | Guarda SVG o PNG y devuelve la ruta absoluta. El formato proviene de `format` o de `.svg` / `.png`. |

No se usan bibliotecas externas para SVG o PNG. En notebooks, `Figure` se
representa inline como SVG. `savefig` rechaza extensiones y formatos distintos
de `svg` y `png`.

## Animación: `temporal_graph.animate`

```python
animate(graph: TemporalGraph, frame_duration: int = 800,
        loop: int = 0,
        positions: Mapping[str, tuple[float, float]] | None = None) -> Animation
```

Genera una vista nodo-enlace, con un cuadro por snapshot registrado. Las
aristas nuevas se resaltan, las persistentes se dibujan normalmente y las
desconectadas aparecen como fantasmas grises discontinuos. El grosor codifica
el peso y una flecha codifica la dirección.

- `frame_duration` está en milisegundos y debe ser entero de al menos 20.
- `loop=0` repite el GIF indefinidamente; se admiten enteros de 0 a 65535.
- Si se omite `positions`, los nodos se disponen en un círculo.
- `positions` debe contener una coordenada `(x, y)` distinta para cada nodo.
  Las posiciones se escalan de forma uniforme para evitar superposiciones.

### `Animation`

| Propiedad o método | Resultado |
| --- | --- |
| `frames` | Copia de la lista de `Figure`, una por timestep. |
| `timesteps` | Lista de instantes de los cuadros. |
| `frame_duration` / `loop` | Configuración usada para codificar el GIF. |
| `len(animation)` | Cantidad de cuadros. |
| `to_gif_bytes(scale=1.5)` | GIF animado como bytes. |
| `save(path, scale=1.5)` | Escribe un archivo `.gif` y devuelve la ruta absoluta. |

`Animation.save` sólo admite la extensión `.gif`; para un cuadro fijo use
`animation.frames[i].savefig(...)`.

### `edge_width(weight)`

```python
edge_width(weight: float) -> float
```

Devuelve el ancho de trazo usado en animaciones: `1.5 + 1.5 * weight`, acotado
entre `1.5` y `12.0`.
