# eco

Pingear muchas cosas a la vez y que se entienda de una mirada.

*[Read this in English](README.md)*

El nombre es lo que hace: manda un ICMP **echo** y escucha el eco.

`eco` es el hermano del `ping` de toda la vida, pero pensado para redes y no
para un solo equipo. Le das una dirección o un `/24` entero y él elige el modo
solo — una tabla viva que se redibuja en el sitio, o un barrido paralelo de la
red. Saca las MAC de la tabla ARP y te deja ponerle nombres a los equipos que
después se reconocen solos.

Un archivo, Python 3 con pura librería estándar, cero dependencias.

## Instalar

```bash
curl -o ~/.local/bin/eco https://raw.githubusercontent.com/MasterStreet423/eco/main/eco
chmod +x ~/.local/bin/eco
```

Necesita Python 3.9+, `iproute2` (`ip`) e `iputils` (`ping`). Por ahora solo
Linux: la MAC sale de `ip neigh`.

## Dos modos, elegidos solos

**Flujo** (≤ 12 destinos) — una fila por destino que se redibuja sola con el
último ms, la pérdida, min/prom/máx y una chispa con el historial. Ctrl-C corta
y deja la tabla quieta en pantalla.

```
    destino        quién            seq     último     paq  perd  min/prom/máx        historial
  ─────────────────────────────────────────────────────────────────────────────────────────────
  ● 192.168.1.1    router             8     3.9 ms     8/8    0%  1.2/4.1/9.8        ▂▃▂▄▃▂▃▃
  ● 8.8.8.8                           8    22.4 ms     8/8    0%  19.9/22.1/31.2     ▄▄▅▄▄▄▄▄
  ○ 192.168.1.42   impresora-barra    8   perdido      5/8   37%  2.1/2.8/3.9        ▂▂✗▂✗▂✗▂
```

**Barrido** (> 12 destinos) — unos pocos paquetes a cada uno en paralelo y una
tabla numerada de quién contestó, con cuánto ms y con qué MAC.

```bash
eco 192.168.1.0/24          # la red completa
eco 192.168.1.1-20          # un rango
eco --todos 192.168.1.0/24  # incluye a los que no contestan
eco --dns 10.0.0.0/24       # además, DNS inverso
```

## Ponerle nombre a un equipo

El barrido numera cada fila, así que puedes bautizar una:

```bash
eco --nombrar 5 impresora-barra
```

Y si ya sabes a quién quieres bautizar, sáltate el barrido: dale la dirección
directo y `eco` busca la MAC solo, pingueando al equipo si la tabla ARP está
fría. Un punto adelante completa con tu propia red:

```bash
eco --nombrar .65 impresora-barra          # -> 192.168.1.65
eco --nombrar 192.168.1.65 impresora-barra
eco --nombrar torre servidor-casa
```

Los nombres se guardan **por MAC**, así que aguantan que el DHCP le cambie la IP
al equipo. Los que no tienen MAC visible (todo lo que esté al otro lado de un
router) caen a guardarse por IP. El archivo es `~/.config/lan/conocidos.conf`,
compartido con la herramienta `lan`; se cambia con `ECO_CONF`.

> Un número pelado siempre es fila del barrido, nunca una dirección. Para la `.5`
> de tu propia red, escribe `.5`.

## Dos idiomas

La salida sigue tu locale, y cada opción larga tiene su gemela en el otro
idioma, así que estos dos son el mismo comando:

```bash
eco --todos --barrido 192.168.1.0/24
eco --all   --sweep   192.168.1.0/24
```

| Español | Inglés | |
|---|---|---|
| `--cuenta` | `--count` | paquetes por destino |
| `--intervalo` | `--interval` | segundos entre paquetes |
| `--espera` | `--wait`, `--timeout` | timeout por paquete |
| `--paralelo` | `--parallel` | pings simultáneos en el barrido |
| `--barrido` | `--sweep`, `--scan` | forzar la tabla |
| `--flujo` | `--stream`, `--live` | forzar la tabla viva |
| `--todos` | `--all` | incluir a los que no contestan |
| `--inverso` | `--dns`, `--reverse` | DNS inverso |
| `--nombrar` | `--name` | ponerle nombre a un equipo |
| `--relativo` | `--relative` | chispa con escala relativa |
| `--lineas` | `--lines`, `--log` | log vertical, para pipes |
| `--plano` | `--plain` | sin colores, tabulado |
| `--idioma` | `--lang` | forzar `es` o `en` |

Se fuerza con `--idioma en` o con `ECO_LANG=en`.

## Por qué la escala de la chispa es absoluta

Los bloques van contra cortes fijos en milisegundos (`▁`≈1, `▂`≈3, `▃`≈9, `▄`≈26,
`▅`≈70, `▆`≈190, `▇`≈500, `█`+), más o menos logarítmicos, porque la latencia se
mueve en órdenes de magnitud y no en pasos iguales.

Escalar cada fila entre su propio mín y máx — que es lo que hacen casi todas las
sparklines — convierte un vaivén de 0.4 a 0.5 ms en un pico dramático que no
significa nada, y encima deja dos filas imposibles de comparar entre sí. Con
escala fija, `▁` es siempre como un milisegundo y `█` es siempre un desastre. Con
`-r` vuelve el zoom relativo, si lo quieres.

## Advertencias

Que alguien no conteste ICMP no significa que esté muerto — Windows con
firewall, cámaras y celulares en ahorro de batería lo filtran. Para saber qué
hay de verdad en la red, la fuente honesta es ARP.

Las MAC solo existen para tu propia LAN; al otro lado de un router no hay nada
que leer. Un `~` después de una MAC significa que es aleatoria (Android, iOS y
Windows lo hacen por defecto), así que no sirve como identidad estable.

## Tests

```bash
uv run pytest
```

## Licencia

MIT
