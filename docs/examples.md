# Ejemplos generales

Todos los comandos de esta página se ejecutan desde la raíz del repositorio.
Los resultados se escriben bajo `output/`.

## Aristas, dirección y reconexión

```bash
python examples/example.py
```

El ejemplo base crea cuatro nodos, parte de una cadena `a-b-c-d` y cambia sus
aristas durante cuatro instantes. Demuestra aristas dirigidas, pesos, colores y
la regla de reconexión explícita: una arista que desaparece no se mantiene
implícitamente en el siguiente snapshot.

Genera:

- `output/example_connections.svg` y `output/example_connections.png`.
- `output/example_decisions.svg` y `output/example_decisions.png`.

## Red social temporal

```bash
python examples/social_network.py
```

Seis personas forman, fortalecen y disuelven amistades durante cinco semanas.
El color codifica el tipo de relación —amistad cercana, amistad o
conocimiento— y el peso expresa su intensidad.

Genera `output/social_network_connections.*` y
`output/social_network_decisions.*`.

## Flujo de trabajo dirigido

```bash
python examples/process_flow.py
```

El pipeline `intake -> review -> build -> test -> deploy` evoluciona durante
cuatro snapshots. Las aristas dirigidas indican entregas de trabajo; los pesos
representan volumen y los colores diferencian flujo principal, retrabajo y
automatización. Antes de renderizar, el script verifica con
`analysis.is_temporally_acyclic` que cada snapshot no tenga ciclos dirigidos.

Genera `output/process_flow_connections.*` y
`output/process_flow_decisions.*`.

## Color y peso como datos

```bash
python examples/custom_colors.py
```

Un balanceador de carga dirige tráfico hacia tres servidores. El estado de cada
servidor cambia entre saludable, degradado y fallando; el color de su arista lo
representa. El peso de la misma arista indica tráfico y un valor `None` la saca
de rotación para ese instante.

Genera `output/custom_colors_connections.*` y
`output/custom_colors_decisions.*`.

## Árbol binario animado

```bash
python examples/binary_tree.py
```

El programa construye y desmonta un árbol binario completo de profundidad 5
(63 nodos). Agrega seis aristas por instante en orden por niveles y luego poda
las hojas en orden inverso. Las aristas son dirigidas de padre a hijo y se
colorean por profundidad. Una disposición jerárquica explícita mantiene el
árbol legible durante la animación.

Resultados:

- `output/binary_tree.gif`: evolución completa.
- `output/binary_tree_full.png` y `.svg`: snapshot con el árbol completo.
- `output/binary_tree_decisions.png` y `.svg`: cambios de todas las aristas.

## Animaciones de grafos existentes

```bash
python examples/animation.py
```

Reutiliza los constructores de la red social y del pipeline para producir
`output/social_network.gif` y `output/process_flow.gif`. Además guarda el
último cuadro del pipeline en `output/process_flow_last_frame.png`.

## Análisis y exportación

```bash
python examples/analysis_and_export.py
```

Construye un grafo desde listas de aristas con `utils.from_edge_list` y luego
imprime:

- la evolución temporal del grado de `b`;
- los componentes conexos de cada instante;
- la persistencia de cada arista;
- las aristas agregadas y removidas entre `t=1` y `t=2`;
- un subgrafo inducido por `a` y `b`.

También exporta el mismo grafo como `output/network.json`,
`output/network.csv` y `output/network.gexf`. El archivo GEXF puede abrirse en
Gephi. Finalmente deserializa el JSON y comprueba que la conversión conserva el
grafo.

## Algoritmos temporales

```bash
python examples/temporal_algorithms.py
```

Este recorrido aplica los módulos algorítmicos a instancias de las notas
teóricas. Imprime resultados de:

- journeys: llegada más temprana, foremost, fastest, shortest, salida más
  tardía y enumeración de journeys;
- Menger temporal: journeys disjuntos por nodo, salida y arista, junto con un
  separador mínimo de salidas;
- métricas de conectividad para estrella móvil, *matchings* alternados y el
  grafo de Soifer;
- etiquetados temporales que preservan caminos y alcanzabilidad;
- disponibilidad periódica y sistemas de congruencias;
- fórmulas para grafos temporales aleatorios;
- exploración temporal exacta de una estrella rotante.

Como salida visual crea `output/moving_star.gif`.

## Cadena de Markov como grafo temporal

```bash
python examples/markov_chain.py
```

Una cadena no reversible modela la navegación de una persona entre las páginas
de una tienda. El ejemplo tiene dos interpretaciones temporales:

1. **Trayectoria simulada.** Cada transición `x(t-1) -> x(t)` se convierte en
   una arista dirigida en el instante `t`. La llegada foremost desde `home`
   coincide con el primer tiempo de visita de cada estado. El promedio de 1000
   caminatas se compara con los tiempos esperados obtenidos al resolver el
   sistema `h = 1 + P h`.
2. **Flujo de probabilidad.** El flujo neto entre cada par de estados genera
   aristas dirigidas ponderadas. Al acercarse a la distribución estacionaria,
   los flujos que se cancelan desaparecen y persiste la corriente del ciclo de
   compra.

El programa escribe `output/markov_trajectory_connections.png` y `.svg`,
`output/markov_flow.gif` y `output/markov_flow_stationary.png`.
