# API: algoritmos temporales

Esta página cubre los módulos `journeys`, `connectivity`, `flows`, `expansion`,
`dissemination`, `design` y `classic`.

## `temporal_graph.journeys`

Un `Journey` es una secuencia no vacía de pasos `(origen, destino, instante)`.
Sus propiedades son `source`, `target`, `departure`, `arrival`, `duration`
(`arrival - departure + 1`), `hops`, `nodes` y `labels`.

| Función | Resultado |
| --- | --- |
| `arcs_by_instant(graph)` | Lista ordenada `(t, [(u, v), ...])` de arcos transitables; duplica aristas no dirigidas en ambos sentidos. |
| `traversal_labels(graph)` | Diccionario `(u, v) -> [t, ...]` de instantes transitables ordenados. |
| `foremost_search(graph, ready, strict=True)` | Búsqueda multiorigen. `ready` asigna instante disponible a cada origen; devuelve `(arrival, parent)`. |
| `earliest_arrival(graph, source, start=None, strict=True)` | Instante de llegada más temprana para cada nodo alcanzable; el origen también aparece. |
| `foremost_journey(graph, source, target, start=None, strict=True)` | Journey que llega antes al destino, o `None`. |
| `reachable(graph, source, start=None, strict=True)` | Conjunto de nodos temporalmente alcanzables. |
| `reachability(graph, start=None, strict=True)` | Diccionario `origen -> conjunto alcanzable`. |
| `is_temporally_connected(graph, start=None, strict=True)` | `True` si todos alcanzan a todos. |
| `temporal_distance(graph, source, target, start=None, strict=True)` | Distancia foremost `arrival - start`, o `None` si no hay journey. |
| `latest_departure(graph, target, deadline=None, strict=True)` | Para cada origen, último instante desde el que aún puede llegar a `target` antes del límite. |
| `fastest_journey(graph, source, target, start=None, strict=True)` | Journey de duración mínima; en empate, el de llegada más temprana. |
| `shortest_journey(graph, source, target, start=None, strict=True)` | Journey con menos saltos; en empate, llegada más temprana. |
| `enumerate_journeys(graph, source, target, start=None, strict=True)` | Iterador de todos los journeys de nodos no repetidos; exponencial. |

Las funciones que reciben origen y destino distintos lanzan `ValueError` si no
son nodos declarados o si ambos son el mismo nodo. `foremost_search` permite
distintos instantes iniciales por origen y es la base de los algoritmos
foremost. Las aristas dirigidas sólo se cruzan en la dirección declarada.

## `temporal_graph.connectivity`

Las propiedades instantáneas ignoran dirección: tratan cada snapshot como
grafo no dirigido. La vida útil es el rango entre el primer y último instante
que contienen al menos una arista; un instante intermedio sin snapshot no tiene
aristas.

| Función | Resultado |
| --- | --- |
| `lifetime(graph)` | `(λ_min, λ_max)` o `None` si no existen aristas. |
| `is_continuously_connected(graph)` | Cada snapshot de la vida útil es conexo. |
| `is_interval_connected(graph, window)` | En toda ventana de `window` instantes, las aristas presentes durante toda la ventana conectan todos los nodos. `window >= 1`. |
| `vertex_connectivity_at(graph, t)` | Conectividad por vértices κ del snapshot; `0` si no es conexo. |
| `is_f_connected(graph, f)` | κ es al menos `f` en cada snapshot de la vida útil. `f >= 1`. |
| `connectivity_time(graph)` | Menor tamaño de ventana cuya **unión** es conexa para toda ventana, o `None`. |
| `temporal_diameter(graph)` | Menor `d` que permite llegar desde todo nodo-tiempo a todos los nodos dentro de `d`, o `None`. |
| `future_set_sizes(graph, node, start)` | Curva `[(t, cantidad_alcanzada), ...]` desde un nodo-tiempo. |
| `outgoing_influence_time(graph)` | Menor `k` que hace crecer cada conjunto futuro al menos un nodo cada `k` instantes, o `None`. |

Para un grafo de un nodo, las métricas devuelven los valores triviales definidos
por la biblioteca (`True`, `0` o `1` según la métrica).

## `temporal_graph.flows`

Implementa variantes temporales de Menger con journeys estrictos.

| Función | Resultado |
| --- | --- |
| `max_out_disjoint_journeys(graph, source, target)` | Máxima cantidad de journeys que no salen del mismo nodo en el mismo instante. |
| `min_departure_separator(graph, source, target)` | Conjunto mínimo de pares `(nodo, t)` cuya eliminación corta todos los journeys. Su cardinal coincide con la función anterior. |
| `max_edge_disjoint_journeys(graph, source, target)` | Máxima cantidad de journeys sin aristas compartidas. Requiere que cada arista tenga una sola etiqueta. |
| `min_edge_separator(graph, source, target)` | Conjunto mínimo de aristas que corta todos los journeys; también requiere etiquetas únicas. |
| `max_node_disjoint_journeys(graph, source, target, limit=100_000)` | Lista máxima de journeys con nodos internos disjuntos. Búsqueda exhaustiva. |

La variante por nodos es NP-hard; genera journeys y falla con `ValueError` si
supera `limit`. Las variantes por arista fallan si una misma arista lógica está
presente en más de un instante. Un grafo sin etiquetas devuelve cero o un
conjunto vacío según corresponda.

## `temporal_graph.expansion`

```python
static_expansion(graph, waiting=True) -> StaticExpansion
```

Desenrolla el grafo en un DAG temporal. `StaticExpansion` contiene:

| Campo o propiedad | Significado |
| --- | --- |
| `first_level`, `last_level` | Niveles extremos del desenrollado. |
| `time_nodes` | Copias `(nodo, nivel)` de cada nodo en cada nivel. |
| `vertical_arcs` | Arcos de espera `(u, i-1) -> (u, i)`. |
| `diagonal_arcs` | Cruces de aristas: `(u, t-1) -> (v, t)`. Una arista no dirigida agrega ambos sentidos. |
| `arcs` | Concatenación de arcos verticales y diagonales. |

`waiting=False` omite los arcos verticales, para modelos donde la información
no se puede conservar entre instantes.

## `temporal_graph.dissemination`

| Función o tipo | Resultado |
| --- | --- |
| `flooding_times(graph, sources, start=None)` | Primera ronda en que cada nodo aprende un mensaje originado en cualquiera de `sources`; los no informados no aparecen. |
| `k_token_dissemination(graph, tokens, policy="round_robin", start=None, rounds=None, seed=None)` | Simula difusión de tokens y devuelve `DisseminationResult`. |
| `harmonic_potential(k)` | Número armónico `H_k`; requiere `k >= 1`. |

`DisseminationResult` tiene `completion` (instante de conocimiento total o
`None`), `knowledge` (diccionario de conjuntos inmutables por nodo) y
`progress` (pares `(ronda, pares nodo-token conocidos)`).

En `k_token_dissemination`, cada nodo transmite un único token que conocía al
inicio de la ronda, sin observar la topología de esa ronda. `policy` puede ser:

- `"round_robin"`: recorre los tokens conocidos ordenados por `repr`;
- `"random"`: elige uniformemente; `seed` hace reproducible la simulación;
- una función `policy(node, known, round) -> token | None`.

Si se omite `rounds`, el proceso llega al último timestep registrado. Las
aristas dirigidas sólo permiten transmisión desde su origen a su destino.

## `temporal_graph.design`

Los arcos estáticos se expresan como pares `(u, v)`. Los etiquetados devuelven
un `TemporalGraph` con aristas dirigidas.

| Función | Resultado |
| --- | --- |
| `temporality(graph)` | Máximo número de etiquetas sobre una arista. |
| `temporal_cost(graph)` | Número total de etiquetas, igual a `graph.label_count`. |
| `topological_order(nodes, arcs)` | Orden topológico de Kahn; falla si el digrafo tiene ciclos. |
| `dag_labeling(nodes, arcs)` | Etiqueta cada arco de un DAG con el índice topológico de su origen; temporality 1 y todos los caminos preservados. |
| `directed_ring_labeling(n)` | Etiqueta el anillo dirigido con dos etiquetas por arco, óptimas para preservar todos los caminos simples. `n >= 2`. |
| `reachability_labeling(nodes, arcs, root=None)` | Etiquetado de a lo sumo dos etiquetas por arco que preserva alcanzabilidad en un digrafo fuertemente conexo. |
| `simple_paths(nodes, arcs)` | Iterador de caminos dirigidos simples no vacíos; exponencial. |
| `has_journey_along(graph, path)` | Determina si una secuencia de nodos puede cruzarse con etiquetas crecientes. |
| `preserves_all_paths(graph, arcs)` | Verifica que todo camino simple del digrafo tiene un journey. |
| `preserves_reachability(graph, arcs)` | Verifica que toda alcanzabilidad estática también sea temporal. |

Todos los arcos deben usar nodos declarados y no pueden ser bucles.
`reachability_labeling` falla si el grafo no es fuertemente conexo o `root` no
pertenece a `nodes`.

## `temporal_graph.classic`

Estos algoritmos son exactos y exponenciales; están orientados a instancias
pequeñas y todos usan journeys estrictos.

| Función o tipo | Resultado |
| --- | --- |
| `max_temporal_matching(graph)` | Lista máxima de triples `(u, v, t)` sin extremos ni instantes compartidos. |
| `temporal_exploration(graph, start_node, start=None, max_nodes=20)` | `Exploration` de menor tiempo que visita todos los nodos, permitiendo espera y revisitas; `None` si no existe. |
| `temporal_tsp(graph, start_node, start=None, max_nodes=12)` | `Tour` hamiltoniano temporal de menor peso que vuelve al origen; `None` si no existe. |

`Exploration.finish` indica el instante en que se visita el último nodo y
`Exploration.walk` contiene los pasos. `Tour.cost` es la suma de los pesos de
las aristas cruzadas y `Tour.steps` contiene el ciclo temporal. Exploration
lanza `ValueError` si hay más de `max_nodes`; TSP hace lo mismo, y además exige
al menos tres nodos.
