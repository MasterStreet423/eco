"""Tests de lo que se rompe de verdad: el parseo de la salida de `ping`, la
expansión de destinos, la escala de la chispa, el guardado de apodos y que los
dos idiomas no se desincronicen. Nada de red real ni de dibujado de tablas."""

import importlib.util, os, re, sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
FUENTE = RAIZ / "eco"


def cargar():
    """El ejecutable no termina en .py, así que se importa a mano."""
    spec = importlib.util.spec_from_loader("eco", SourceFileLoader("eco", str(FUENTE)))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


m = cargar()


# ── i18n ──────────────────────────────────────────────────────────────────────
# Estos dos son los que se pagan solos: al agregar un texto es facilísimo
# traducirlo en un idioma y olvidar el otro, y el error aparecería recién en
# runtime, delante del usuario.

def test_los_dos_idiomas_tienen_las_mismas_claves():
    es, en = set(m.TEXTOS["es"]), set(m.TEXTOS["en"])
    assert es == en, f"solo en es: {es - en} · solo en en: {en - es}"


def test_toda_clave_pedida_por_el_codigo_existe():
    fuente = FUENTE.read_text()
    pedidas = set(re.findall(r'\bt\(\s*["\']([a-z_0-9]+)["\']', fuente))
    assert pedidas, "el regex no encontró ninguna llamada a t(), revísalo"
    for idioma in ("es", "en"):
        faltan = pedidas - set(m.TEXTOS[idioma])
        assert not faltan, f"faltan en {idioma}: {faltan}"


def test_los_textos_con_placeholder_coinciden_entre_idiomas():
    """Si el español dice {n} y el inglés {total}, el format() revienta."""
    for clave, es in m.TEXTOS["es"].items():
        campos = lambda s: set(re.findall(r"\{(\w+)", s))
        assert campos(es) == campos(m.TEXTOS["en"][clave]), clave


@pytest.mark.parametrize("entorno,esperado", [
    ({"LANG": "es_CL.UTF-8"}, "es"),
    ({"LANG": "en_US.UTF-8"}, "en"),
    ({"LANG": "C"}, "en"),
    ({}, "en"),
    ({"ECO_LANG": "es", "LANG": "en_US.UTF-8"}, "es"),   # la env manda sobre el locale
])
def test_eleccion_de_idioma(monkeypatch, entorno, esperado):
    for v in ("ECO_LANG", "LC_ALL", "LC_MESSAGES", "LANG"):
        monkeypatch.delenv(v, raising=False)
    for k, v in entorno.items():
        monkeypatch.setenv(k, v)
    assert m.elegir_idioma() == esperado


def test_el_flag_manda_sobre_todo(monkeypatch):
    monkeypatch.setenv("LANG", "es_CL.UTF-8")
    assert m.elegir_idioma("en") == "en"
    assert m.elegir_idioma("es") == "es"
    assert m.elegir_idioma("klingon") == "en"   # idioma raro: inglés, no adivinar


# ── flags bilingües ───────────────────────────────────────────────────────────
@pytest.mark.parametrize("es,en", [
    ("--todos", "--all"), ("--barrido", "--sweep"), ("--flujo", "--stream"),
    ("--dns", "--inverso"), ("--relativo", "--relative"),
    ("--lineas", "--lines"), ("--plano", "--plain"),
])
def test_las_opciones_largas_son_gemelas(es, en):
    ap = m.construir_parser()
    a, b = ap.parse_args([es, "x"]), ap.parse_args([en, "x"])
    assert vars(a) == vars(b)


def test_nombrar_toma_destino_y_apodo():
    ap = m.construir_parser()
    assert ap.parse_args(["--nombrar", ".65", "impresora"]).nombrar == [".65", "impresora"]
    assert ap.parse_args(["--name", ".65", "printer"]).nombrar == [".65", "printer"]


def test_nombrar_no_necesita_destinos():
    """`eco --nombrar .65 x` no pinga nada, así que no debe exigir un destino."""
    a = m.construir_parser().parse_args(["--nombrar", ".65", "impresora"])
    assert a.destinos == [] and a.nombrar


def test_un_apodo_con_espacios_va_entre_comillas():
    a = m.construir_parser().parse_args(["--nombrar", ".65", "impresora de barra"])
    assert a.nombrar[1] == "impresora de barra"


def test_nombres_ya_no_existe_como_flag():
    """--nombrar y --nombres juntos se confundían al leer; el DNS es --dns."""
    with pytest.raises(SystemExit):
        m.construir_parser().parse_args(["--nombres", "x"])


def test_las_opciones_con_valor_son_gemelas():
    ap = m.construir_parser()
    assert ap.parse_args(["--cuenta", "5", "x"]).cuenta == 5
    assert ap.parse_args(["--count", "5", "x"]).cuenta == 5
    assert ap.parse_args(["--espera", "2", "x"]).espera == 2.0
    assert ap.parse_args(["--timeout", "2", "x"]).espera == 2.0
    assert ap.parse_args(["-t", "x"]).todos is True


# ── expansión de destinos ─────────────────────────────────────────────────────
def test_cidr():
    assert m.expandir("192.168.1.0/30") == ["192.168.1.1", "192.168.1.2"]
    assert len(m.expandir("192.168.1.0/24")) == 254


def test_cidr_de_un_host_no_pierde_la_ip():
    """Un /32 no tiene .hosts() usables; sin el caso especial devolvía vacío."""
    assert m.expandir("10.0.0.5/32") == ["10.0.0.5"]


def test_rango():
    assert m.expandir("192.168.1.10-13") == [f"192.168.1.{n}" for n in (10, 11, 12, 13)]


def test_el_rango_se_corta_en_255():
    assert m.expandir("192.168.1.250-999")[-1] == "192.168.1.255"


def test_llaves():
    assert m.expandir("10.0.0.{1,3}") == ["10.0.0.1", "10.0.0.3"]
    assert m.expandir("10.0.0.{1..3}") == ["10.0.0.1", "10.0.0.2", "10.0.0.3"]


def test_nombre_pelado_pasa_entero():
    assert m.expandir("torre") == ["torre"]
    assert m.expandir("host.ejemplo.com") == ["host.ejemplo.com"]


# ── parseo de la salida de ping ───────────────────────────────────────────────
# Es lo más frágil del programa: depende del formato de iputils y de que el
# locale forzado a C de verdad funcione.

def test_linea_ok():
    mm = m.RE_OK.search("64 bytes from 192.168.1.1: icmp_seq=3 ttl=64 time=1.42 ms")
    assert mm and mm.group(1) == "3" and float(mm.group(2)) == 1.42


def test_linea_ok_no_matchea_la_traducida():
    """Si alguien saca el LC_ALL=C esto falla, que es justo lo que queremos."""
    assert m.RE_OK.search("64 bytes desde 192.168.1.1: icmp_seq=3 ttl=64 tiempo=1.42 ms") is None


def test_sin_respuesta():
    mm = m.RE_NOOK.search("no answer yet for icmp_seq=7")
    assert mm and mm.group(1) == "7"


def test_inalcanzable():
    mm = m.RE_UNRE.search("From 10.0.0.1 icmp_seq=2 Destination Host Unreachable")
    assert mm and mm.group(1) == "2"


def test_estadisticas_finales():
    mm = m.RE_STAT.search("5 packets transmitted, 4 received, 20% packet loss, time 4005ms")
    assert mm and (mm.group(1), mm.group(2)) == ("5", "4")


def test_rtt_final():
    mm = m.RE_RTT.search("rtt min/avg/max/mdev = 1.234/2.345/3.456/0.789 ms")
    assert mm and float(mm.group(2)) == 2.345


# ── chispa ────────────────────────────────────────────────────────────────────
def test_la_escala_absoluta_no_infla_diferencias_chicas(monkeypatch):
    """El reclamo que originó la escala absoluta: 0.4 vs 0.5 ms no es un pico."""
    monkeypatch.setattr(m, "RELATIVO", False)
    monkeypatch.setattr(m, "PLANO", True)
    assert len(set(m.chispa([0.4, 0.5, 0.45]))) == 1


def test_la_escala_absoluta_si_muestra_diferencias_reales(monkeypatch):
    monkeypatch.setattr(m, "RELATIVO", False)
    monkeypatch.setattr(m, "PLANO", True)
    s = m.chispa([0.5, 900.0])
    assert s[0] == "▁" and s[1] == "█"


def test_la_relativa_si_estira(monkeypatch):
    monkeypatch.setattr(m, "RELATIVO", True)
    monkeypatch.setattr(m, "PLANO", True)
    assert len(set(m.chispa([0.4, 0.5]))) == 2


def test_el_perdido_va_como_cruz(monkeypatch):
    monkeypatch.setattr(m, "PLANO", True)
    assert m.chispa([1.0, None, 1.0])[1] == "✗"
    assert m.chispa([None, None]) == "✗✗"


# ── conocidos.conf ────────────────────────────────────────────────────────────
@pytest.fixture
def conf(tmp_path, monkeypatch):
    ruta = tmp_path / "conocidos.conf"
    monkeypatch.setattr(m, "CONOCIDOS", str(ruta))
    monkeypatch.setattr(m, "PLANO", True)
    return ruta


def test_leer_conocidos_ignora_comentarios_y_vacias(conf):
    conf.write_text("# comentario\n\nAA:BB:CC:DD:EE:FF | torre | pc | nota\n")
    assert m.leer_conocidos() == {"AA:BB:CC:DD:EE:FF": "torre"}


def test_leer_conocidos_sin_archivo_no_revienta(conf):
    assert m.leer_conocidos() == {}


def test_apodar_por_ip_guarda_por_mac(conf, monkeypatch):
    monkeypatch.setattr(m, "resolver", lambda o: ("192.168.1.65", None))
    monkeypatch.setattr(m, "ips_propias", lambda: set())
    monkeypatch.setattr(m, "mac_de", lambda ip: "AA:BB:CC:DD:EE:FF")
    assert m.apodar("192.168.1.65", "impresora") == 0
    assert m.leer_conocidos() == {"AA:BB:CC:DD:EE:FF": "impresora"}


def test_reapodar_reescribe_en_vez_de_duplicar(conf, monkeypatch):
    monkeypatch.setattr(m, "resolver", lambda o: ("192.168.1.65", None))
    monkeypatch.setattr(m, "ips_propias", lambda: set())
    monkeypatch.setattr(m, "mac_de", lambda ip: "AA:BB:CC:DD:EE:FF")
    m.apodar("192.168.1.65", "viejo")
    m.apodar("192.168.1.65", "nuevo")
    assert m.leer_conocidos() == {"AA:BB:CC:DD:EE:FF": "nuevo"}
    assert sum("AA:BB:CC" in l for l in conf.read_text().splitlines()) == 1


def test_sin_mac_cae_a_guardar_por_ip(conf, monkeypatch):
    monkeypatch.setattr(m, "resolver", lambda o: ("8.8.8.8", None))
    monkeypatch.setattr(m, "ips_propias", lambda: set())
    monkeypatch.setattr(m, "mac_de", lambda ip: None)
    assert m.apodar("8.8.8.8", "google") == 0
    assert m.leer_conocidos() == {"8.8.8.8": "google"}


def test_apodar_objetivo_irresoluble_falla_sin_escribir(conf, monkeypatch):
    monkeypatch.setattr(m, "resolver", lambda o: (None, "no pude"))
    assert m.apodar("no-existe", "x") == 1
    assert not conf.exists()


def test_apodar_fila_inexistente_falla(conf, tmp_path, monkeypatch):
    estado = tmp_path / "ultimo.json"
    estado.write_text('{"filas": [{"ip": "10.0.0.1", "mac": null}]}')
    monkeypatch.setattr(m, "ESTADO", str(estado))
    assert m.apodar("99", "x") == 1


def test_apodar_por_fila_usa_la_mac_de_esa_fila(conf, tmp_path, monkeypatch):
    estado = tmp_path / "ultimo.json"
    estado.write_text('{"filas": [{"ip": "10.0.0.1", "mac": "11:22:33:44:55:66"}]}')
    monkeypatch.setattr(m, "ESTADO", str(estado))
    assert m.apodar("1", "router") == 0
    assert m.leer_conocidos() == {"11:22:33:44:55:66": "router"}


# ── dónde vive el archivo de apodos ───────────────────────────────────────────
def test_usuario_nuevo_usa_su_propio_directorio(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert m._conf_por_defecto() == str(tmp_path / "eco" / "conocidos.conf")


def test_hereda_el_conf_que_el_usuario_ya_tenia(tmp_path, monkeypatch):
    """Pisar los nombres ya puestos sería peor que heredar el directorio."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    (tmp_path / "lan").mkdir()
    (tmp_path / "lan" / "conocidos.conf").write_text("")
    assert m._conf_por_defecto() == str(tmp_path / "lan" / "conocidos.conf")


def test_el_propio_le_gana_al_heredado(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    for d in ("lan", "eco"):
        (tmp_path / d).mkdir()
        (tmp_path / d / "conocidos.conf").write_text("")
    assert m._conf_por_defecto() == str(tmp_path / "eco" / "conocidos.conf")


# ── resolver ──────────────────────────────────────────────────────────────────
def test_el_punto_completa_con_la_red_propia(monkeypatch):
    monkeypatch.setattr(m, "prefijo_local", lambda: "192.168.1")
    assert m.resolver(".65") == ("192.168.1.65", None)


def test_una_ip_completa_pasa_tal_cual():
    assert m.resolver("10.0.0.7") == ("10.0.0.7", None)


def test_sin_red_propia_el_punto_da_error(monkeypatch):
    monkeypatch.setattr(m, "prefijo_local", lambda: None)
    ip, err = m.resolver(".65")
    assert ip is None and err


# ── MAC aleatoria ─────────────────────────────────────────────────────────────
@pytest.mark.parametrize("mac,es_random", [
    ("AA:BB:CC:DD:EE:FF", True), ("A2:BB:CC:DD:EE:FF", True),
    ("BC:FC:E7:AA:C7:38", False), ("00:11:22:33:44:55", False),
])
def test_deteccion_de_mac_aleatoria(mac, es_random):
    assert m.aleatoria(mac) is es_random


# ── tabla ARP ─────────────────────────────────────────────────────────────────
def test_arp_ignora_las_entradas_fallidas(monkeypatch):
    salida = ("192.168.1.1 dev enp3s0 lladdr bc:fc:e7:aa:c7:38 REACHABLE\n"
              "192.168.1.9 dev enp3s0  FAILED\n"
              "192.168.1.7 dev enp3s0 lladdr 11:22:33:44:55:66 STALE\n")
    class Fake:
        stdout = salida
    monkeypatch.setattr(m.subprocess, "run", lambda *a, **k: Fake())
    assert m.macs_arp() == {"192.168.1.1": "BC:FC:E7:AA:C7:38",
                            "192.168.1.7": "11:22:33:44:55:66"}
