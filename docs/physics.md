# Ejemplos de física

Los ejemplos de `examples/physics/` convierten interacciones físicas en aristas
temporales y verifican que las conclusiones obtenidas con journeys coincidan con
predicciones teóricas. Ambos usan exclusivamente la biblioteca estándar y
escriben sus resultados en `output/physics/`.

## Cadena armónica: propagación del sonido

```bash
python examples/physics/harmonic_chain.py
```

Una cadena de masas `m` unidas por resortes de constante `k` y distancia `a`
comienza con su masa central desplazada. La simulación usa integración
velocity-Verlet. Un resorte `(n, n+1)` pasa a ser una arista temporal cuando
conserva al menos el 0.1 % de la energía inicial.

Por lo tanto, un journey desde el sitio central describe un camino causal para
la energía y su llegada foremost mide el arribo del frente de onda. El script
contrasta la simulación con la solución de Bessel y con la velocidad de sonido
`c = a sqrt(k / m)`.

Comprueba la conservación de energía, compara todas las aristas temporales de
la simulación contra la solución exacta, estima la velocidad del frente y repite
la medición para varias masas.

Genera:

- `output/physics/harmonic_chain_connections.png` y `.svg`.
- `output/physics/harmonic_chain.gif`.

## Gas de discos duros: colisiones y difusión causal

```bash
python examples/physics/hard_disk_gas.py
```

El sistema contiene 40 discos duros en una caja periódica. La dinámica es por
eventos: entre choques cada disco se mueve en línea recta y cada colisión crea
una arista temporal; los eventos se agrupan en instantes de 0.02 unidades de
tiempo.

El programa realiza tres comprobaciones:

- **Frecuencia de colisión:** compara el número de aristas por disco con la
  teoría de Enskog y con la aproximación diluida de Boltzmann.
- **Equilibración:** verifica que las velocidades converjan a la distribución
  Maxwell--Boltzmann bidimensional (Rayleigh).
- **Propagación causal:** calcula journeys foremost desde un disco y compara la
  cantidad alcanzada con un proceso SI bien mezclado. También reordena los
  compañeros de colisión en los mismos instantes para separar el efecto de la
  estructura espacial.

Genera `output/physics/hard_disk_cascade_connections.png` y `.svg`. La imagen
muestra el árbol de journeys foremost desde `p0`; el color refleja la cantidad
de saltos y los discos están ordenados por instante de llegada.

## Tiempos de ejecución orientativos

En una máquina de desarrollo típica, la cadena armónica tarda aproximadamente
cuatro segundos y el gas de discos duros alrededor de nueve segundos. Los
resultados numéricos incluyen simulación y validaciones, por lo que pueden
variar levemente entre versiones de Python y plataformas.
