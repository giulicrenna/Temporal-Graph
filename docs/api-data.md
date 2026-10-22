# API: datos, modelos y utilidades

Esta página cubre `analysis`, `exporters`, `utils`, `generators`, `periodic` y
`random_models`.

## `temporal_graph.analysis`

| Función | Resultado |
| --- | --- |
| `degree_timeline(graph, node)` | Diccionario `t -> grado` en cada snapshot registrado. Ignora dirección: una arista dirigida cuenta en ambos extremos. |
| `connected_components_at(graph, t)` | Lista de componentes como `set[str]`, ignorando dirección. Incluye aislados y conserva el orden del primer nodo declarado. |
| `edge_persistence(graph)` | Diccionario `key -> fracción de snapshots registrados` en que aparece cada arista. |
| `is_temporally_acyclic(graph)` | `True` si las aristas dirigidas de cada snapshot forman un DAG; ignora las no dirigidas. |

`degree_timeline` falla si el nodo no fue declarado. `connected_components_at`
usa `graph.edges_at(t)` y por ello falla si el snapshot no existe.

## `temporal_graph.exporters`

| Función | Resultado |
| --- | --- |
| `to_dict(graph)` | Diccionario compatible con JSON, con `nodes` y `snapshots`; cada arista conserva `u`, `v`, `directed`, `weight` y `color`. |
| `from_dict(data)` | Reconstruye un `TemporalGraph` desde el formato anterior. |
| `to_json(graph, indent=2)` | Serialización JSON como texto. |
| `from_json(text)` | Reconstruye el grafo desde JSON. |
| `to_csv(graph, path)` | Escribe una fila por arista-snapshot y devuelve la ruta absoluta. Columnas: `t,u,v,directed,weight,color`. |
| `to_gexf(graph, path)` | Escribe GEXF dinámico de tiempo entero para Gephi y devuelve la ruta absoluta. |

En GEXF, cada arista contiene un *spell* por intervalo continuo de presencia.
Si una arista es dirigida en algún snapshot, se exporta como dirigida; su peso
es el del primer snapshot donde aparece.

## `temporal_graph.utils`

| Función | Resultado |
| --- | --- |
| `from_edge_list(nodes, snapshots)` | Construye un grafo desde `{t: [(u, v), ...]}` con aristas no dirigidas y atributos por defecto. |
| `snapshot_diff(graph, t1, t2)` | `(added, removed)` al pasar de `t1` a `t2`; ambas listas están ordenadas por clave. |
| `filter_edges(graph, predicate)` | Nuevo grafo que conserva sólo aristas que satisfacen `predicate(edge)`. Conserva nodos y snapshots, incluso vacíos. |
| `subgraph(graph, nodes)` | Nuevo grafo inducido por los nodos solicitados; conserva orden y snapshots. |

`subgraph` falla si se solicita un nodo ausente o si el conjunto de nodos queda
vacío. `snapshot_diff` falla si alguno de los snapshots no fue registrado.

## `temporal_graph.generators`

Todas las familias son deterministas, usan instantes desde `1` y materializan
exactamente `rounds` snapshots.

| Función | Grafo generado y restricciones |
| --- | --- |
| `moving_star(n, rounds)` | Estrella cuyo centro recorre `u1` a `u(n-1)`; período `n-1`. Requiere `n >= 3`, `rounds >= 1`. |
| `alternating_matchings(n, rounds)` | Anillo dividido en dos matchings perfectos alternados; cada snapshot es disconexo. Requiere `n >= 4` par. |
| `soifer_graph(n, rounds)` | Coloración de Soifer de `K_n`: cada snapshot es un matching perfecto y cada arista reaparece cada `n-1` instantes. Requiere `n >= 4` par. |
| `rotating_center_star(n, rounds)` | Mitad centros `c*` rotan y mitad hojas `l*` permanecen hojas; período `n/2`. Requiere `n >= 4` par. |

## `temporal_graph.periodic`

Una disponibilidad lineal se representa como `Linear = (a, b)`: la arista está
disponible en `b, b+a, b+2a, ...`. `a=0` representa sólo el instante `b`. Los
dos valores deben ser no negativos.

| Función | Resultado |
| --- | --- |
| `solve_congruences(system)` | Resuelve pares `(residuo, módulo)`; devuelve `(t0, M)` con todas las soluciones `t0 + Mz`, o `None` si son incompatibles. Los módulos deben ser al menos 1. |
| `common_instants(functions, count=1)` | Primeros `count` instantes en que todas las disponibilidades coinciden. Devuelve `[]` si no hay solución, `count < 1` o la lista está vacía. |
| `edges_coincide(first, second)` | Si dos disponibilidades comparten al menos un instante. |
| `next_availability(function, after)` | Primer instante estrictamente posterior a `after`, o `None` para una disponibilidad única ya vencida. |
| `linear_availability_graph(nodes, functions, lifetime, directed=False)` | Materializa disponibilidades desde `0` hasta `lifetime` como `TemporalGraph`. |
| `linear_earliest_arrival(nodes, functions, source, start=-1, directed=False, lifetime=None)` | Llegadas foremost sin materializar el tiempo; usa Dijkstra y cuesta `O(m log n)`. |

En `linear_earliest_arrival`, `lifetime` limita los instantes utilizables; los
no alcanzables no se incluyen en el diccionario resultado. Si `directed=False`,
cada función puede cruzarse en ambos sentidos.

## `temporal_graph.random_models`

| Función | Resultado |
| --- | --- |
| `random_temporal_graph(n, r, seed=None)` | Clique no dirigido `v1..vn` donde cada arista recibe una única etiqueta uniforme entre `1` y `r`. `seed` lo hace reproducible. Requiere `n >= 2`, `r >= 1`. |
| `path_journey_probability(k, r)` | Probabilidad de que un camino fijo de `k` aristas sea journey: `C(r, k) / r^k`. Requiere `k >= 1`, `r >= 1`. |
| `expected_journey_count(n, k, r)` | Esperanza de journeys de longitud `k`: `(n)_(k+1) C(r, k) / r^k`. Requiere `1 <= k < n`. |
| `foremost_within_two_probability(n, r)` | Probabilidad exacta de llegada foremost entre dos nodos fijos antes o en el instante 2. Requiere `n >= 2`, `r >= 2`. |

## Resumen de validaciones frecuentes

La biblioteca usa `ValueError` para argumentos válidos por tipo pero inválidos
por dominio —por ejemplo nodos desconocidos, límites negativos, grafos vacíos
para renderizar o restricciones matemáticas incumplidas— y `TypeError` para
tipos incorrectos en el modelo base. Las rutas de salida crean automáticamente
sus directorios padre y los métodos de guardado devuelven rutas absolutas.
