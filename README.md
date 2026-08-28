# eco

Ping a lot of things at once and understand it at a glance.

*[Léeme en español](README.es.md)*

The name is what it does: it sends an ICMP **echo** and listens for the echo
back.

`eco` is the sibling of a plain `ping`, aimed at networks rather than at a
single host. Give it one address or a whole `/24` and it picks the right mode on
its own — a live table that redraws in place, or a parallel sweep of the network.
It reads MAC addresses out of the ARP table, and lets you give hosts names that
stick.

Single file, Python 3 standard library only, no dependencies.

## Install

```bash
curl -o ~/.local/bin/eco https://raw.githubusercontent.com/MasterStreet423/eco/main/eco
chmod +x ~/.local/bin/eco
```

Requires Python 3.9+, `iproute2` (`ip`) and `iputils` (`ping`). Linux only for
now — the ARP lookup uses `ip neigh`.

## Two modes, picked automatically

**Stream** (≤ 12 hosts) — one row per host, redrawn in place with the last
latency, the loss, min/avg/max and a sparkline of the history. Ctrl-C stops and
leaves the table on screen.

```
    host           who              seq        last     pkt  loss  min/avg/max         history
  ─────────────────────────────────────────────────────────────────────────────────────────────
  ● 192.168.1.1    router             8     3.9 ms     8/8    0%  1.2/4.1/9.8        ▂▃▂▄▃▂▃▃
  ● 8.8.8.8                           8    22.4 ms     8/8    0%  19.9/22.1/31.2     ▄▄▅▄▄▄▄▄
  ○ 192.168.1.42   printer-bar        8   lost         5/8   37%  2.1/2.8/3.9        ▂▂✗▂✗▂✗▂
```

**Sweep** (> 12 hosts) — a few packets to each host in parallel, then a numbered
table of who answered, how fast, and with which MAC.

```bash
eco 192.168.1.0/24        # the whole network
eco 192.168.1.1-20        # a range
eco --all 192.168.1.0/24  # include the ones that never answer
eco --dns 10.0.0.0/24     # plus reverse DNS
```

## Naming hosts

A sweep numbers every row, so you can baptize one:

```bash
eco --name 5 printer-bar
```

If you already know who you want to name, skip the sweep — give it the address
directly and `eco` finds the MAC itself, pinging the host first if the ARP
table is cold. A leading dot fills in your own network:

```bash
eco --name .65 printer-bar          # -> 192.168.1.65
eco --name 192.168.1.65 printer-bar
eco --name tower home-server
```

Names are stored **by MAC**, so they survive a DHCP lease change. Hosts with no
visible MAC (anything across a router) fall back to being stored by IP. The file
is `~/.config/lan/conocidos.conf`, shared with the `lan` tool; override it with
`ECO_CONF`.

> A bare number is always a sweep row, never an address. For `.5` on your own
> network, write `.5`.

## Two languages

Output follows your locale, and every long option has a twin in the other
language, so both of these are the same command:

```bash
eco --todos --barrido 192.168.1.0/24
eco --all   --sweep   192.168.1.0/24
```

| Spanish | English | |
|---|---|---|
| `--cuenta` | `--count` | packets per host |
| `--intervalo` | `--interval` | seconds between packets |
| `--espera` | `--wait`, `--timeout` | per-packet timeout |
| `--paralelo` | `--parallel` | simultaneous pings in a sweep |
| `--barrido` | `--sweep`, `--scan` | force the table |
| `--flujo` | `--stream`, `--live` | force the live table |
| `--todos` | `--all` | include hosts that never answer |
| `--inverso` | `--dns`, `--reverse` | reverse DNS |
| `--nombrar` | `--name` | name a host |
| `--relativo` | `--relative` | sparkline with relative scale |
| `--lineas` | `--lines`, `--log` | vertical log, for pipes |
| `--plano` | `--plain` | no colors, tab-separated |
| `--idioma` | `--lang` | force `es` or `en` |

Force the language with `--lang en` or `ECO_LANG=en`.

## Why the sparkline scale is absolute

The blocks map to fixed millisecond cuts (`▁`≈1, `▂`≈3, `▃`≈9, `▄`≈26, `▅`≈70,
`▆`≈190, `▇`≈500, `█`+), roughly logarithmic, because latency moves in orders of
magnitude rather than in even steps.

Scaling each row to its own min/max instead — which is what most sparklines do —
turns a 0.4 → 0.5 ms wobble into a dramatic spike that means nothing, and makes
two rows impossible to compare against each other. With a fixed scale, `▁` is
always about a millisecond and `█` is always a disaster. `-r` brings the relative
zoom back if you want it.

## Caveats

Not answering ICMP does not mean a host is dead — Windows with a firewall,
cameras and phones on battery saver all filter it. For an inventory of what is
actually on the network, ARP is the honest source.

MAC addresses only exist for your own LAN; across a router there is nothing to
read. A `~` after a MAC means it is randomized (Android/iOS/Windows do this by
default), so it is not a stable identity.

## Tests

```bash
uv run pytest
```

## License

MIT
