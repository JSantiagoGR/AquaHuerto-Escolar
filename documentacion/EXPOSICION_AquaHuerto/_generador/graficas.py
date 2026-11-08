"""Genera todas las graficas, planos y diagramas de la carpeta de exposicion (matplotlib)."""
import csv
import math
import os
import sqlite3
import datetime as dt

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon, Rectangle, Circle, FancyArrowPatch

from rutas import FIG, DB_LOCAL, RES, EPANET

VERDE = '#1B5E20'
VERDE2 = '#43A047'
AZUL = '#1565C0'
NARANJA = '#E65100'
ROJO = '#C62828'
GRIS = '#555555'
plt.rcParams.update({'font.family': 'Calibri', 'font.size': 11, 'axes.spines.top': False,
                     'axes.spines.right': False, 'axes.titleweight': 'bold', 'axes.titlesize': 13,
                     'savefig.dpi': 200, 'savefig.bbox': 'tight'})


def guardar(fig, nombre):
    p = os.path.join(FIG, nombre)
    fig.savefig(p)
    plt.close(fig)
    return p


# ---------------------------------------------------------------- calibraciones
def calibracion_ec5():
    mv = [360, 420, 630, 870]
    agua = [0, 105, 257, 490]
    s = [100 * a / (600 + a) for a in agua]
    m, b = 0.08146067, -23.932584
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    xs = [340, 900]
    ax[0].plot(xs, [m * x + b for x in xs], color=VERDE, lw=2, label='Recta: s = 0.0815·mV − 23.93')
    ax[0].scatter(mv, s, s=60, color=NARANJA, zorder=3, label='Muestras (600 mL de tierra)')
    for x, y, a in zip(mv, s, agua):
        ax[0].annotate(f'{a} mL agua', (x, y), textcoords='offset points', xytext=(6, -12), fontsize=9)
    ax[0].set_xlabel('Voltaje del EC-5 (mV)')
    ax[0].set_ylabel('s = V agua / (V tierra + V agua) (%)')
    ax[0].set_title('Calibración del sensor de humedad EC-5')
    ax[0].text(0.03, 0.80, 'R² = 0.945', transform=ax[0].transAxes, fontsize=12, color=VERDE, weight='bold')
    ax[0].legend(loc='lower right', fontsize=9)
    ax[0].grid(alpha=.3)
    mvs = list(range(360, 871, 10))
    th = []
    for x in mvs:
        sv = max(0, m * x + b) / 100
        th.append(100 * sv / (1 - sv))
    ax[1].plot(mvs, th, color=AZUL, lw=2)
    for lab, v, c in (('Punto de marchitez 16 %', 16, ROJO), ('Óptima frijol 39 %', 39, VERDE2),
                      ('Capacidad de campo 48 %', 48, AZUL)):
        ax[1].axhline(v, ls='--', color=c, lw=1)
        ax[1].text(365, v + 0.8, lab, color=c, fontsize=9)
    ax[1].axvspan(515, 600, color=VERDE2, alpha=.12)
    ax[1].text(520, 3, 'Lecturas en el\nsustrato (21-oct)', fontsize=9, color=VERDE)
    ax[1].set_xlabel('Voltaje del EC-5 (mV)')
    ax[1].set_ylabel('Humedad volumétrica θ (%VWC)')
    ax[1].set_title('Conversión usada en el firmware: θ = s / (1 − s)')
    ax[1].grid(alpha=.3)
    return guardar(fig, 'fig_calibracion_ec5.png')


def calibracion_ping():
    d = [12 + i for i in range(0, 106)]
    pct = [(117 - x) / (117 - 12) * 100 for x in d]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.plot(d, pct, color=AZUL, lw=2, label='Nivel % = (117 − d) / (117 − 12) · 100')
    pts = [(30.4, 82, '21-oct, tapa puesta: 82 %'), (110.7, 6, '14-oct, tinaco casi vacío: 6 %')]
    for x, y, t in pts:
        ax.scatter([x], [y], s=60, color=NARANJA, zorder=3)
        ax.annotate(t, (x, y), textcoords='offset points', xytext=(8, 6), fontsize=9)
    ax.axvline(12, ls=':', color=GRIS)
    ax.axvline(117, ls=':', color=GRIS)
    ax.text(13, 4, 'lleno\n12 cm', fontsize=9, color=GRIS)
    ax.text(105, 92, 'vacío\n117 cm', fontsize=9, color=GRIS)
    ax.set_xlabel('Distancia medida por el PING))) (cm)')
    ax.set_ylabel('Nivel del tinaco (%)')
    ax.set_title('Calibración del sensor de nivel (ultrasónico PING)))')
    sec = ax.secondary_yaxis('right', functions=(lambda p: p * 6.3 * 105 / 100, lambda l: l / (6.3 * 105) * 100))
    sec.set_ylabel('Volumen estimado (L, ≈ 6.3 L/cm)')
    ax.grid(alpha=.3)
    ax.legend(loc='upper center', fontsize=9)
    return guardar(fig, 'fig_calibracion_ping.png')


def calibracion_caudalimetro():
    litros = [1, 2, 3, 4, 5]
    pulsos = [481, 920, 1390, 1850, 2315]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.plot([0, 5.2], [0, 450 * 5.2], color=VERDE, lw=2, label='Factor de fábrica: 450 pulsos/L')
    ax.scatter(litros, pulsos, s=60, color=NARANJA, zorder=3, label='Pulsos registrados (Act. 2.3)')
    for x, y in zip(litros, pulsos):
        ax.annotate(str(y), (x, y), textcoords='offset points', xytext=(-14, 8), fontsize=9)
    ax.set_xlabel('Volumen pedido (L)')
    ax.set_ylabel('Pulsos del YF-S201')
    ax.set_title('Caudalímetro YF-S201: pulsos contra volumen')
    ax.text(0.2, 2000, 'Error calculado promedio 3.55 %\n(volumen calculado, sin recipiente graduado)',
            fontsize=9, color=GRIS)
    ax.grid(alpha=.3)
    ax.legend(loc='lower right', fontsize=9)
    return guardar(fig, 'fig_calibracion_caudalimetro.png')


# ---------------------------------------------------------------- pruebas fisicas
def riegos_reales():
    con = sqlite3.connect(DB_LOCAL)
    filas = con.execute("select ts_start, target_l, delivered_l, result, duration_s from irrigation_events "
                        "where simulated=0 and device='esp32_principal' and target_l is not null order by ts_start").fetchall()
    filas = [(dt.datetime.fromtimestamp(t).strftime('%d-oct %H:%M'), tl, dl, r, d) for t, tl, dl, r, d in filas]
    filas += [('21-oct 14:43', 2.0, 2.051, 'TARGET', 42.8), ('21-oct 14:44', 1.0, 0.622, 'STOP_CMD', 13.5)]
    fig, ax = plt.subplots(figsize=(11, 4.4))
    x = range(len(filas))
    col = {'TARGET': VERDE2, 'STOP_CMD': AZUL, 'NO_FLOW': ROJO}
    ax.bar([i - 0.2 for i in x], [f[1] for f in filas], 0.4, color='#BDBDBD', label='Litros pedidos')
    ax.bar([i + 0.2 for i in x], [f[2] for f in filas], 0.4, color=[col.get(f[3], GRIS) for f in filas],
           label='Litros medidos')
    for i, f in enumerate(filas):
        ax.text(i + 0.2, f[2] + 0.05, f[3].replace('_CMD', ''), ha='center', fontsize=7.5, rotation=90, va='bottom')
    ax.set_xticks(list(x))
    ax.set_xticklabels([f[0] for f in filas], rotation=45, ha='right', fontsize=8)
    ax.set_ylabel('Litros')
    ax.set_title('Riegos reales en el huerto (12 al 21 de octubre de 2026)')
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color='#BDBDBD', label='Pedido'), Patch(color=VERDE2, label='Medido: llegó a la meta'),
                       Patch(color=AZUL, label='Medido: detenido con STOP'),
                       Patch(color=ROJO, label='NO_FLOW: sin agua, corte de seguridad')], fontsize=8, loc='upper left')
    ax.set_ylim(0, 3.6)
    ax.grid(axis='y', alpha=.3)
    return guardar(fig, 'fig_riegos_reales.png'), filas


def caudal_por_fecha():
    datos = [('9-oct\n(banco)', 4.0), ('12-oct', 2.27), ('13-oct', 1.72), ('14-oct', 1.70),
             ('21-oct\n(mañana)', 1.91), ('21-oct\n(prueba final)', 3.02)]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar([d[0] for d in datos], [d[1] for d in datos], color=[AZUL] + [VERDE2] * 5)
    for i, d in enumerate(datos):
        ax.text(i, d[1] + 0.08, f'{d[1]:.2f}', ha='center')
    ax.axhline(4.5, ls='--', color=NARANJA)
    ax.text(5.4, 4.55, 'Diseño EPANET: 4.5 L/min', color=NARANJA, ha='right', fontsize=9)
    ax.set_ylabel('Caudal medido por el YF-S201 (L/min)')
    ax.set_title('Caudal real de la bomba en cada prueba')
    ax.set_ylim(0, 5.2)
    ax.grid(axis='y', alpha=.3)
    return guardar(fig, 'fig_caudal_por_fecha.png')


def serie_riego_2l():
    t, fl, pul, est = [], [], [], []
    with open(os.path.join(RES, 'riego_2L_20261013_1613.csv'), encoding='utf8') as f:
        for r in csv.DictReader(f):
            t.append(float(r['t_s']))
            fl.append(float(r['flujo_lpm'] or 0))
            pul.append(int(r['pulsos'] or 0))
            est.append(r['bomba'] == 'ON')
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(t, fl, color=AZUL, lw=2, label='Caudal (L/min)')
    ax.fill_between(t, 0, [3.2 if e else 0 for e in est], color=VERDE2, alpha=.12, step='mid', label='Bomba encendida')
    ax.set_xlabel('Tiempo (s)')
    ax.set_ylabel('Caudal (L/min)')
    a2 = ax.twinx()
    a2.plot(t, [p / 450 for p in pul], color=NARANJA, lw=2, label='Litros acumulados')
    a2.set_ylabel('Litros acumulados (pulsos / 450)')
    a2.spines['top'].set_visible(False)
    ax.set_title('Riego de 2 L en el huerto (13-oct-2026): caudal y volumen en el tiempo')
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = a2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc='upper left', fontsize=9)
    ax.grid(alpha=.3)
    return guardar(fig, 'fig_serie_riego_2L.png')


def humedad_tinaco():
    con = sqlite3.connect(DB_LOCAL)
    t0 = dt.datetime(2026, 10, 14, 10, 20).timestamp()
    t1 = dt.datetime(2026, 10, 14, 11, 12).timestamp()
    rows = con.execute("select ts, vwc, soil_status from readings where device='esp32_principal' and simulated=0 "
                       "and ts between ? and ? order by ts", (t0, t1)).fetchall()
    ev = con.execute("select ts_start, ts_end, delivered_l from irrigation_events where simulated=0 and "
                     "device='esp32_principal' and delivered_l>0.1 and ts_start between ? and ?", (t0, t1)).fetchall()
    fig, ax = plt.subplots(figsize=(10, 4.2))
    v = [(dt.datetime.fromtimestamp(r[0]), r[1]) for r in rows if r[1] is not None and r[2] == 'OK']
    ax.plot([a for a, _ in v], [b for _, b in v], '-o', ms=3, color=VERDE, label='Humedad del suelo (EC-5)')
    for a, b, l in ev:
        ax.axvspan(dt.datetime.fromtimestamp(a), dt.datetime.fromtimestamp(b or a + 60), color=AZUL, alpha=.25)
        ax.text(dt.datetime.fromtimestamp(a), 57, 'riego\n%.1f L' % l, color=AZUL, fontsize=9)
    ax.set_ylabel('Humedad volumétrica (%VWC)')
    ax.set_ylim(0, 65)
    ax.set_title('Respuesta del sensor de humedad a dos riegos reales (14-oct-2026, 10:20 a 11:12)')
    import matplotlib.dates as md
    ax.xaxis.set_major_formatter(md.DateFormatter('%H:%M'))
    ax.grid(alpha=.3)
    ax.legend(loc='upper left', fontsize=9)
    ax.text(0.01, 0.02, 'Ese día se terminó de cablear el EC-5; las lecturas previas a 10:25 son con el sensor recién conectado.',
            transform=ax.transAxes, fontsize=8, color=GRIS)
    return guardar(fig, 'fig_datos_reales_huerto.png')


def resumen_pruebas():
    datos = [('Pruebas de lógica en PC', 48, 48), ('Autodiagnóstico en la placa', 51, 51),
             ('Integración (simulador)', 30, 30), ('ESP32 real por red', 15, 15), ('Recuperación', 3, 3),
             ('Prueba de campo Pi + ESP32', 28, 28), ('Prueba final con agua', 14, 15)]
    fig, ax = plt.subplots(figsize=(9, 4))
    y = range(len(datos))
    ax.barh(list(y), [d[2] for d in datos], color='#E0E0E0')
    ax.barh(list(y), [d[1] for d in datos], color=VERDE2)
    for i, d in enumerate(datos):
        ax.text(d[2] + 0.5, i, f'{d[1]}/{d[2]}', va='center', weight='bold')
    ax.set_yticks(list(y))
    ax.set_yticklabels([d[0] for d in datos])
    ax.invert_yaxis()
    ax.set_xlabel('Pruebas aprobadas')
    ax.set_title('Resumen de pruebas automáticas y físicas')
    ax.set_xlim(0, 58)
    return guardar(fig, 'fig_resumen_pruebas.png')


# ---------------------------------------------------------------- EPANET
def epanet():
    asp, pres = [], []
    with open(os.path.join(EPANET, 'resultados_epanet.csv'), encoding='utf8') as f:
        for r in csv.DictReader(f):
            if r['tipo'] == 'nodo' and r['id'].startswith('A') and len(r['id']) == 3:
                asp.append(r['id'])
                pres.append(float(r['presion_bar_PRELIMINAR']))
    esc = []
    with open(os.path.join(EPANET, 'escenarios_sensibilidad.csv'), encoding='utf8') as f:
        for r in csv.DictReader(f):
            if r['escenario'].startswith('Q'):
                q = int(r['escenario'][1:]) * 9 / 60
                p = float(r['P_min_bar_PRELIM']) if r['P_min_bar_PRELIM'] else 0.0
                esc.append((r['escenario'], q, p, r['viable_hidraulicamente']))
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    ax[0].bar(asp, pres, color=AZUL)
    ax[0].set_ylim(2.10, 2.145)
    ax[0].set_ylabel('Presión (bar)')
    ax[0].set_title('Presión en los 9 aspersores (diseño A)')
    ax[0].text(0.02, 0.92, 'Uniformidad de presión 0.9998', transform=ax[0].transAxes, fontsize=9)
    ax[0].grid(axis='y', alpha=.3)
    cols = [VERDE2 if e[3] == 'SI' else ROJO for e in esc]
    ax[1].bar([f"{e[0][1:]} L/h\n({e[1]:.1f} L/min)" for e in esc], [max(e[2], 0) for e in esc], color=cols)
    for i, e in enumerate(esc):
        ax[1].text(i, max(e[2], 0) + 0.1, 'viable' if e[3] == 'SI' else 'NO viable', ha='center', fontsize=8)
    ax[1].set_ylabel('Presión mínima (bar)')
    ax[1].set_title('Sensibilidad: caudal por aspersor')
    ax[1].tick_params(axis='x', labelsize=8)
    ax[1].grid(axis='y', alpha=.3)
    return guardar(fig, 'fig_epanet_presiones.png')


# ---------------------------------------------------------------- ayudas de dibujo
def caja(ax, x, y, w, h, txt, fc='#E8F5E9', ec=VERDE, fs=9, bold=False, ls='-'):
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle='round,pad=0.02,rounding_size=0.08',
                                fc=fc, ec=ec, lw=1.4, ls=ls))
    ax.text(x, y, txt, ha='center', va='center', fontsize=fs, weight='bold' if bold else 'normal', wrap=True)


def rombo(ax, x, y, w, h, txt, fs=8.5):
    ax.add_patch(Polygon([(x, y + h / 2), (x + w / 2, y), (x, y - h / 2), (x - w / 2, y)], fc='#FFF8E1', ec=NARANJA, lw=1.4))
    ax.text(x, y, txt, ha='center', va='center', fontsize=fs)


def flecha(ax, a, b, txt=None, color=GRIS, ls='-', off=(0.05, 0.05), rad=0.0):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle='-|>', mutation_scale=12, color=color, lw=1.3, ls=ls,
                                 connectionstyle=f'arc3,rad={rad}'))
    if txt:
        ax.text((a[0] + b[0]) / 2 + off[0], (a[1] + b[1]) / 2 + off[1], txt, fontsize=8, color=color)


def lienzo(w, h, titulo):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.axis('off')
    ax.set_title(titulo, fontsize=14, weight='bold', color=VERDE)
    return fig, ax


# ---------------------------------------------------------------- diagramas de software
def arquitectura():
    fig, ax = lienzo(14, 7.5, 'Arquitectura del sistema AquaHuerto')
    caja(ax, 2.0, 5.6, 3.2, 2.6, 'SENSORES\nEC-5 (humedad del suelo)\nPING))) (nivel del tinaco)\nDHT22 (aire)\nYF-S201 (caudal)',
         fc='#E3F2FD', ec=AZUL)
    caja(ax, 2.0, 2.0, 3.2, 2.2, 'ACTUADORES\nRelé K1 → bomba 12 V\nRelé K2 → electroválvula NC', fc='#FFF3E0', ec=NARANJA)
    caja(ax, 6.2, 3.8, 3.0, 4.6, 'ESP32\nFirmware riego-2.0.0\n(C, ESP-IDF 6.0.2)\n\n• Lectura de sensores\n• Modos MANUAL /\n  AUTOMÁTICO / IA\n'
         '• Supervisor de seguridad\n• Modelo IA (RLS)\n• Guarda modo y\n  modelo en NVS', bold=False)
    caja(ax, 10.3, 5.9, 3.0, 1.5, 'Raspberry Pi (servidor)\nMosquitto 1884 (MQTT)\nNode-RED 1881', fc='#EDE7F6', ec='#5E35B1')
    caja(ax, 10.3, 3.8, 3.0, 1.3, 'Base de datos SQLite\n22 tablas · respaldo diario', fc='#EDE7F6', ec='#5E35B1')
    caja(ax, 12.6, 1.6, 2.4, 1.4, 'Dashboard 2.0\n10 páginas\n(red RouterHuerto1)', fc='#E8F5E9')
    caja(ax, 9.2, 1.6, 2.4, 1.4, 'Bot de Telegram\n/estado /ia /modo\n(sin regar)', fc='#E8F5E9')
    caja(ax, 6.2, 0.75, 3.6, 0.9, 'Open-Meteo (Internet): ET0, VPD, lluvia\nlo consultan el ESP32 (60 min) y el servidor (30 min)',
         fc='#F5F5F5', ec=GRIS, fs=8)
    flecha(ax, (3.6, 5.6), (4.7, 4.8), 'lecturas', AZUL)
    flecha(ax, (4.7, 2.8), (3.6, 2.2), 'órdenes', NARANJA)
    flecha(ax, (7.7, 5.0), (8.8, 5.8), None, '#5E35B1')
    flecha(ax, (8.8, 5.4), (7.7, 4.6), None, '#5E35B1')
    ax.text(8.05, 6.35, 'telemetría, estado,\neventos (MQTT)', fontsize=8, color='#5E35B1', ha='center')
    ax.text(8.25, 4.0, 'comandos\ncon ACK', fontsize=8, color='#5E35B1', ha='center')
    flecha(ax, (10.3, 5.15), (10.3, 4.45), None, '#5E35B1')
    flecha(ax, (11.2, 3.15), (12.3, 2.3), None, VERDE)
    flecha(ax, (9.8, 3.15), (9.4, 2.3), None, VERDE)
    flecha(ax, (6.2, 1.2), (6.2, 1.5), None, GRIS)
    ax.text(0.3, -0.15, 'Sin Internet el ESP32 sigue regando con sus reglas locales; sin MQTT guarda 24 h de datos y los envía al reconectar.',
            fontsize=9, color=GRIS)
    return guardar(fig, 'fig_arquitectura.png')


def flujo_automatico():
    fig, ax = lienzo(12, 13, 'Diagrama de flujo: decisión de riego en modo AUTOMÁTICO')
    pasos = [
        ('Leer humedad del suelo (cada 5 min)', 'c', None),
        ('¿Salidas habilitadas\ny sensor válido?', 'r', 'No'),
        ('¿Humedad sobre la\nreserva o máxima?', 'r', 'Sí'),
        ('¿Por debajo de la\nhumedad crítica?', 'r', 'EMERG'),
        ('¿Debajo de objetivo − 2 pp\nen 2 lecturas seguidas?', 'r', 'No'),
        ('¿Máximo diario alcanzado o\nriego hace < 60 min?', 'r', 'Sí'),
        ('¿Hora válida, fuera de 11–16 h\ny en ventana 06–09 / 18–20?', 'r', 'No'),
        ('¿Temperatura ≤ 35 °C?', 'r', 'No (pospone)'),
        ('Riego por dosis: 1.5 L → esperar 15 min → medir\n(hasta 5 dosis o llegar al objetivo)', 'c', None),
    ]
    sigue = {1: 'Sí', 2: 'No', 3: 'No', 4: 'Sí', 5: 'No', 6: 'Sí', 7: 'Sí'}
    X, BUS = 4.5, 8.4
    y = 12.2
    pos = []
    for t, k, _ in pasos:
        if k == 'c':
            caja(ax, X, y, 5.2, 0.8, t, fs=9.5)
        else:
            rombo(ax, X, y, 5.0, 1.1, t)
        pos.append(y)
        y -= 1.38
    for n, (a, b) in enumerate(zip(pos[:-1], pos[1:])):
        flecha(ax, (X, a - 0.5), (X, b + 0.55), None)
        if n in sigue:
            ax.text(X + 0.12, (a + b) / 2 - 0.1, sigue[n], fontsize=8.5, color=VERDE, weight='bold')
    ytop = None
    for i, (t, k, sal) in enumerate(pasos):
        if sal and sal != 'EMERG':
            ax.plot([X + 2.5, BUS], [pos[i], pos[i]], color=ROJO, lw=1.3)
            ax.text(X + 2.65, pos[i] + 0.08, sal, fontsize=8.5, color=ROJO, weight='bold')
            ytop = ytop or pos[i]
    ax.plot([BUS, BUS], [ytop, 1.6], color=ROJO, lw=1.3)
    flecha(ax, (BUS, 1.6), (BUS + 0.6, 1.6), None, ROJO)
    caja(ax, 10.3, 1.6, 2.6, 1.3, 'NO REGAR\n(registra la causa\ny sigue monitoreando)', fc='#FFEBEE', ec=ROJO)
    ie = 3
    ax.plot([X - 2.5, 0.9], [pos[ie], pos[ie]], color=NARANJA, lw=1.3)
    ax.text(X - 2.9, pos[ie] + 0.08, 'Sí', fontsize=8.5, color=NARANJA, weight='bold')
    flecha(ax, (0.9, pos[ie]), (0.9, pos[ie] - 0.9), None, NARANJA)
    caja(ax, 1.1, pos[ie] - 1.5, 2.0, 1.1, 'EMERGENCIA\n1.5 L a cualquier\nhora (máx. 1\ncada 240 min)', fc='#FFF3E0', ec=NARANJA, fs=8)
    ax.text(0.3, 0.3, 'El tinaco bajo no bloquea: solo avisa. La protección contra bombeo en seco es NO_FLOW (45 s sin pulsos).',
            fontsize=9, color=GRIS)
    return guardar(fig, 'fig_flujo_automatico.png')


def flujo_riego_seguro():
    fig, ax = lienzo(12, 7.2, 'Secuencia segura de un riego (los tres modos)')
    xs = [1.4, 3.6, 5.8, 8.0, 10.3]
    t = ['Orden de riego\n(L pedidos)', 'Abrir\nelectroválvula', 'Esperar 1.5 s', 'Encender bomba', 'Contar pulsos\n(PCNT, 450 p/L)']
    for x, s in zip(xs, t):
        caja(ax, x, 5.8, 1.9, 1.0, s)
    for a, b in zip(xs[:-1], xs[1:]):
        flecha(ax, (a + 0.95, 5.8), (b - 0.95, 5.8))
    rombo(ax, 10.3, 3.9, 2.6, 1.3, '¿Llegó a los\nlitros pedidos?')
    flecha(ax, (10.3, 5.3), (10.3, 4.55))
    caja(ax, 6.6, 3.9, 3.2, 1.0, 'Apagar bomba → esperar 1.5 s\n→ cerrar electroválvula')
    flecha(ax, (9.0, 3.9), (8.2, 3.9), 'Sí', VERDE, off=(-0.2, 0.1))
    caja(ax, 2.4, 3.9, 2.8, 1.0, 'Registrar evento\n(TARGET) y aprender IA', fc='#E3F2FD', ec=AZUL)
    flecha(ax, (5.0, 3.9), (3.8, 3.9))
    caja(ax, 6.6, 1.4, 9.8, 1.6,
         'CORTES DE SEGURIDAD (cualquier momento):  STOP del usuario  ·  NO_FLOW: 45 s sin pulsos  ·  FLOW_HIGH > 8 L/min\n'
         'Bomba más de 180 s (configurable) y tope fijo de 5.5 min  ·  control sin responder 3 s  ·  máximo 7.5 L por riego y 30 L por día\n'
         '→ apaga bomba, cierra válvula, registra FALLA y avisa en el dashboard',
         fc='#FFEBEE', ec=ROJO, fs=9)
    flecha(ax, (10.3, 3.25), (10.3, 2.25), 'No, pero hay\nuna falla', ROJO, off=(0.1, 0))
    return guardar(fig, 'fig_flujo_riego_seguro.png')


def estados():
    fig, ax = lienzo(12, 7, 'Máquina de estados del firmware')
    P = {'INIT': (1.3, 3.5), 'IDLE': (4.3, 3.5), 'MONITORING': (7.3, 5.6), 'AUTO_WATERING': (10.6, 5.6),
         'INFILTRATION_WAIT': (10.6, 3.3), 'MANUAL_WATERING': (7.3, 1.2), 'FAULT': (1.3, 1.2)}
    for k, (x, y) in P.items():
        caja(ax, x, y, 2.2, 0.7, k, fc='#FFEBEE' if k == 'FAULT' else '#E8F5E9', ec=ROJO if k == 'FAULT' else VERDE,
             fs=9, bold=True)

    def f(a, b, t, tp, c=GRIS, ha='center'):
        flecha(ax, a, b, None, c)
        ax.text(tp[0], tp[1], t, fontsize=8.5, color=c, ha=ha)
    f((2.45, 3.5), (3.15, 3.5), 'arranque\nsin regar', (2.8, 3.65))
    f((5.0, 3.9), (6.4, 5.2), 'AUTOMÁTICO / IA', (5.2, 4.7), ha='right')
    f((8.45, 5.6), (9.45, 5.6), 'hace falta\nregar', (8.95, 5.75))
    f((10.6, 5.2), (10.6, 3.7), 'dosis 1.5 L', (10.7, 4.4), ha='left')
    f((9.5, 3.55), (8.0, 5.2), '15 min, medir', (8.55, 3.9), ha='right')
    f((4.8, 3.1), (6.3, 1.6), 'START en MANUAL', (5.1, 2.0), ha='right')
    f((6.7, 1.6), (5.3, 3.1), 'meta o STOP', (6.3, 2.5), ha='left')
    f((6.15, 1.2), (2.45, 1.2), 'NO_FLOW / límite / falla', (4.3, 0.75), c=ROJO)
    f((1.6, 1.6), (3.6, 3.1), 'LIMPIAR FALLA', (2.0, 2.4), c=ROJO, ha='right')
    ax.text(0.3, 6.3, 'STOP siempre tiene prioridad. Tras un reinicio se restaura el modo guardado y nunca se riega al arrancar.',
            fontsize=9, color=GRIS)
    return guardar(fig, 'fig_maquina_estados.png')


def flujo_comando():
    fig, ax = lienzo(13, 6, 'Recorrido de un comando: del botón al ESP32 y de vuelta')
    xs = [1.3, 3.8, 6.4, 9.0, 11.6]
    t = ['Botón en el\ndashboard o /modo\nen Telegram', 'Confirmación\n("¿Seguro?")', 'Servidor: lista\nblanca, id y hora,\nMQTT QoS 1',
         'ESP32 revisa:\nJSON, duplicado,\nretenido, > 60 s', 'Ejecuta y responde\nACK con id']
    for x, s in zip(xs, t):
        caja(ax, x, 3.9, 2.2, 1.4, s)
    for a, b in zip(xs[:-1], xs[1:]):
        flecha(ax, (a + 1.1, 3.9), (b - 1.1, 3.9))
    caja(ax, 6.4, 1.3, 7.4, 1.0, 'La página muestra "CONFIRMADO por el dispositivo".  Sin ACK en 12 s → TIMEOUT y no cambia nada.',
         fc='#E3F2FD', ec=AZUL)
    flecha(ax, (11.6, 3.2), (10.1, 1.8), None, AZUL)
    caja(ax, 9.0, 5.5, 2.6, 0.7, 'Rechaza: DUPLICATE / RETAINED / STALE', fc='#FFEBEE', ec=ROJO, fs=8)
    flecha(ax, (9.0, 4.6), (9.0, 5.15), None, ROJO)
    return guardar(fig, 'fig_flujo_comando.png')


def flujo_ia():
    fig, ax = lienzo(13, 7.5, 'Modo IA: cómo aprende y cómo decide')
    caja(ax, 2.3, 6.0, 3.8, 1.3, 'Modelo A (respuesta al riego)\nΔθ por litro según humedad,\ntemperatura, HR y horas sin riego',
         fc='#E3F2FD', ec=AZUL)
    caja(ax, 2.3, 3.9, 3.8, 1.3, 'Modelo B (secado)\npérdida pp/h según humedad,\nKc·VPD, Kc·ET0 y hora del día',
         fc='#E3F2FD', ec=AZUL)
    caja(ax, 2.3, 1.6, 3.8, 1.5, 'Aprendizaje en línea (RLS)\nolvido 0.995 / 0.999\natípicos > 4σ descartados\nCUSUM detecta cambios',
         fc='#EDE7F6', ec='#5E35B1')
    caja(ax, 7.0, 6.0, 3.4, 1.2, 'APRENDIZAJE\n< 6 riegos o < 48 h de secado\n→ usa la lógica AUTOMÁTICA', fc='#FFF8E1', ec=NARANJA)
    caja(ax, 7.0, 3.9, 3.4, 1.2, 'VALIDACIÓN\nerror fuera de tolerancia\n(A ≤ 2 pp, B ≤ 0.4 pp/h)', fc='#FFF8E1', ec=NARANJA)
    caja(ax, 7.0, 1.6, 3.4, 1.2, 'PREDICTIVO_ACTIVO\ndatos suficientes y\nerrores dentro de tolerancia', fc='#E8F5E9')
    flecha(ax, (7.0, 5.4), (7.0, 4.5))
    flecha(ax, (7.0, 3.3), (7.0, 2.2))
    caja(ax, 11.3, 3.9, 3.0, 4.6, 'PLAN\n\n1. Simula hora por hora\nhasta el siguiente horario\n\n2. Si la humedad se\nmantiene: no riega\n\n'
         '3. Si no: litros = (meta −\nactual) / ganancia\n\n4. Pospone si la lluvia\nprevista cubre el déficit', fc='#E8F5E9')
    flecha(ax, (8.7, 1.6), (9.8, 2.5), None, VERDE)
    flecha(ax, (4.2, 6.0), (5.3, 6.0), None)
    flecha(ax, (4.2, 3.9), (5.3, 3.9), None)
    flecha(ax, (2.3, 2.35), (2.3, 3.25), None, '#5E35B1')
    return guardar(fig, 'fig_flujo_ia.png')


# ---------------------------------------------------------------- hidraulico
def diagrama_hidraulico():
    fig, ax = lienzo(15, 7.6, 'Diagrama hidráulico de AquaHuerto (diseño EPANET v3, escenario A)')
    # tinaco
    ax.add_patch(Rectangle((0.5, 2.2), 2.0, 3.6, fc='#263238', ec='k'))
    ax.add_patch(Rectangle((0.6, 2.3), 1.8, 2.9, fc='#90CAF9', ec='none', alpha=.8))
    ax.text(1.5, 4.3, 'TINACO\n≈ 650 L útiles\nØ 0.90 m', ha='center', color='white', fontsize=9, weight='bold')
    ax.add_patch(Rectangle((1.2, 5.8), 0.6, 0.3, fc='#E3F2FD', ec=AZUL))
    ax.text(1.5, 6.3, 'PING))) (nivel)', ha='center', fontsize=8, color=AZUL)
    y = 2.5
    ax.plot([2.5, 10.0], [y, y], color=AZUL, lw=4, solid_capstyle='round', zorder=1)
    comps = [(3.1, 'Válvula de\nesfera (azul)', '#1E88E5'), (4.0, 'Check', GRIS), (4.9, 'T existente', GRIS),
             (6.0, 'BOMBA\n12 V · 6 A\n6 L/min máx.', NARANJA), (7.4, 'CAUDALÍMETRO\nYF-S201\n450 p/L', VERDE2),
             (8.8, 'ELECTROVÁLVULA\nNC 12 V\n(KING SHENG)', ROJO)]
    for x, t, c in comps:
        if 'BOMBA' in t:
            ax.add_patch(Circle((x, y), 0.42, fc=c, ec='k', zorder=3))
            ax.add_patch(Polygon([(x - 0.15, y - 0.2), (x - 0.15, y + 0.2), (x + 0.22, y)], fc='white', zorder=4))
        elif 'ELECTRO' in t:
            ax.add_patch(Polygon([(x - 0.35, y - 0.25), (x - 0.35, y + 0.25), (x + 0.35, y - 0.25), (x + 0.35, y + 0.25)],
                                 fc=c, ec='k', zorder=3))
            ax.add_patch(Rectangle((x - 0.15, y + 0.25), 0.3, 0.3, fc='white', ec='k', zorder=3))
            ax.text(x, y + 0.4, 'M', ha='center', va='center', fontsize=7, zorder=4)
        elif 'CAUDAL' in t:
            ax.add_patch(Circle((x, y), 0.3, fc=c, ec='k', zorder=3))
            ax.text(x, y, 'FT', ha='center', va='center', fontsize=7, color='white', zorder=4)
        else:
            ax.add_patch(Polygon([(x - 0.22, y - 0.18), (x - 0.22, y + 0.18), (x + 0.22, y - 0.18), (x + 0.22, y + 0.18)],
                                 fc=c, ec='k', zorder=3))
        ax.text(x, y - 0.95, t, ha='center', fontsize=8)
    # subida
    ax.plot([10.0, 10.0], [y, 6.3], color=AZUL, lw=4, zorder=1)
    ax.text(9.6, 4.4, 'Subida vertical\nhasta z = 1.52 m\n(Tuboplus ½")', ha='right', fontsize=8)
    ax.plot([10.0, 13.6], [6.3, 6.3], color=AZUL, lw=4)
    ax.add_patch(Rectangle((10.75, 6.1), 0.4, 0.4, fc='white', ec='k', zorder=3))
    ax.text(10.95, 6.75, 'Cruz', ha='center', fontsize=8)
    # cajon visto en planta (derecha)
    ax.add_patch(Rectangle((11.4, 1.0), 3.2, 3.2, fc='#8D6E63', ec='#4E342E', lw=2, alpha=.35))
    ax.text(13.0, 0.65, 'Cajón 1.00 × 1.00 m (vista en planta)', ha='center', fontsize=8)
    for i, yy in enumerate([1.55, 2.6, 3.65]):
        ax.plot([11.4, 14.6], [yy, yy], color='k', lw=2)
        for xx in (11.95, 13.0, 14.05):
            ax.add_patch(Circle((xx, yy), 0.12, fc=AZUL, ec='k', zorder=3))
    ax.plot([11.2, 11.2, 11.4], [6.3, 2.6, 2.6], color='k', lw=2, ls='--')
    ax.text(11.6, 4.5, '3 mangueras negras\n× 3 microaspersores\n= 9 aspersores\n(0.17 / 0.50 / 0.83 m)', fontsize=8)
    ax.text(0.5, 7.0, 'Flujo: tinaco → esfera → check → T → bomba → caudalímetro → electroválvula → subida → cruz → 3 líneas.',
            fontsize=9)
    ax.text(0.5, 0.3, 'EPANET: 9 × 30 L/h = 4.5 L/min, ≈ 2.14 bar en aspersores (curva de bomba provisional). '
                      'Caudal real medido: 1.7–3.0 L/min.', fontsize=9, color=GRIS)
    return guardar(fig, 'fig_diagrama_hidraulico.png')


# ---------------------------------------------------------------- electrico
def diagrama_electrico():
    fig, ax = lienzo(16, 10, 'Diagrama eléctrico y electrónico de AquaHuerto')
    def bloque(x, y, w, h, t, fc, ec):
        ax.add_patch(Rectangle((x, y), w, h, fc=fc, ec=ec, lw=1.6))
        ax.text(x + w / 2, y + h / 2, t, ha='center', va='center', fontsize=9, weight='bold')

    def linea(pts, c, lw=2, ls='-'):
        ax.plot([p[0] for p in pts], [p[1] for p in pts], color=c, lw=lw, ls=ls, solid_capstyle='round')

    bloque(0.4, 7.6, 2.4, 1.6, 'PANEL SOLAR\nFirstech FE-50WP\n50 W · Vmp 17.4 V', '#E3F2FD', AZUL)
    bloque(3.6, 7.6, 2.4, 1.6, 'CONTROLADOR\nde carga PWM\n(LCD, 2 USB)', '#ECEFF1', GRIS)
    bloque(6.8, 7.6, 2.4, 1.6, 'BATERÍA SLA\nMighty Max ML9-12\n12 V · 9 Ah', '#FFF8E1', NARANJA)
    linea([(2.8, 8.6), (3.6, 8.6)], ROJO)
    linea([(2.8, 8.2), (3.6, 8.2)], 'k')
    linea([(6.0, 8.6), (6.8, 8.6)], ROJO)
    linea([(6.0, 8.2), (6.8, 8.2)], 'k')
    # bus 12 V
    linea([(9.2, 8.6), (15.3, 8.6)], ROJO, 3)
    linea([(9.2, 8.2), (15.3, 8.2)], 'k', 3)
    ax.text(12.3, 8.85, 'BUS +12 V', color=ROJO, fontsize=9, weight='bold')
    ax.text(12.3, 7.85, 'BUS GND (común)', color='k', fontsize=9, weight='bold')
    ax.add_patch(Rectangle((9.5, 8.45), 0.6, 0.3, fc='white', ec=ROJO, ls='--'))
    ax.text(9.8, 8.95, 'Fusible\n(recomendado)', ha='center', fontsize=8, color=ROJO)
    # ESP32
    bloque(5.4, 2.2, 3.6, 4.2, '', '#E8F5E9', VERDE)
    ax.text(7.2, 6.05, 'ESP32 (D0WD-V3)\nen placa de expansión', ha='center', fontsize=9, weight='bold')
    pines = [('GPIO26 → IN1 (bomba)', 5.4), ('GPIO27 → IN2 (válvula)', 5.0), ('GPIO19 ← YF-S201 (PCNT)', 4.5),
             ('GPIO18 ↔ PING))) SIG', 4.1), ('GPIO4 ↔ DHT22', 3.7), ('GPIO25 → excitación EC-5', 3.3),
             ('GPIO34 ← señal EC-5 (ADC)', 2.9), ('VIN (jack 6.5–16 V) ← 12 V', 2.5)]
    for t, yy in pines:
        ax.text(5.55, yy, t, fontsize=8)
    linea([(13.9, 8.2), (13.9, 1.5)], 'k', 1.2)
    linea([(9.0, 2.5), (10.5, 2.5), (10.5, 8.6)], ROJO, 1.2)
    ax.add_patch(Rectangle((10.25, 3.3), 0.5, 0.35, fc='white', ec=ROJO, ls='--'))
    ax.text(10.85, 3.4, 'Capacitor 470–1000 µF\nen VIN (recomendado)', fontsize=8, color=ROJO)
    # reles
    bloque(10.9, 4.6, 2.2, 1.5, 'MÓDULO 2 RELÉS\nSRD-05VDC-SL-C\nactivo en BAJO', '#FFF3E0', NARANJA)
    linea([(9.0, 5.4), (10.9, 5.6)], AZUL, 1.2)
    linea([(9.0, 5.0), (10.9, 5.0)], AZUL, 1.2)
    bloque(14.2, 5.4, 1.6, 1.0, 'BOMBA\n12 V · 6 A', '#FFE0B2', NARANJA)
    bloque(14.2, 3.9, 1.6, 1.0, 'ELECTRO-\nVÁLVULA\nNC 12 V', '#FFCDD2', ROJO)
    linea([(13.1, 5.7), (14.2, 5.9)], ROJO, 1.6)
    linea([(13.1, 5.0), (13.6, 4.4), (14.2, 4.4)], ROJO, 1.6)
    linea([(12.0, 8.6), (12.0, 6.1)], ROJO, 1.4)
    ax.text(12.05, 7.0, 'COM K1/K2', fontsize=8, color=ROJO)
    linea([(15.0, 5.4), (15.0, 4.9)], 'k', 1)
    linea([(15.8, 4.4), (15.95, 4.4), (15.95, 8.2), (15.3, 8.2)], 'k', 1)
    ax.text(14.2, 6.6, 'Diodos 1N4007 en paralelo\n(recomendado)', fontsize=8, color=ROJO)
    ax.text(10.9, 4.15, 'Nota: el SRD soporta 3 A inductivos;\nse recomienda relé automotriz 30/40 A\ncon fusible de 10 A para la bomba.',
            fontsize=7.5, color=ROJO)
    # sensores
    bloque(0.4, 4.9, 3.6, 1.2, 'YF-S201 (caudal)\nrojo 5 V · negro GND · amarillo señal', '#E3F2FD', AZUL)
    bloque(0.4, 3.4, 3.6, 1.2, 'PING))) #28015 (nivel)\n5V · GND · SIG (divisor 1 kΩ / 2 kΩ)', '#E3F2FD', AZUL)
    bloque(0.4, 1.9, 3.6, 1.2, 'DHT22 (temperatura y HR)\n3.3 V · GND · datos', '#E3F2FD', AZUL)
    bloque(0.4, 0.4, 3.6, 1.2, 'EC-5 (humedad del suelo)\nblanco → 25 · rojo → 34 · sin forro → GND', '#E3F2FD', AZUL)
    for yy, py in ((5.5, 4.5), (4.0, 4.1), (2.5, 3.7), (1.0, 3.1)):
        linea([(4.0, yy), (5.4, py)], AZUL, 1.2)
    ax.text(0.4, 9.6, 'Líneas rojas = +12 V · negras = tierra común · azules = señales. Lo punteado en rojo son protecciones recomendadas '
                      '(pendientes de instalar).', fontsize=9, color=GRIS)
    return guardar(fig, 'fig_diagrama_electrico.png')


# ---------------------------------------------------------------- planos
def cota(ax, a, b, txt, off=0.0, vertical=False, fs=8):
    if vertical:
        ax.annotate('', a, b, arrowprops=dict(arrowstyle='<->', lw=0.8))
        ax.text(a[0] + off, (a[1] + b[1]) / 2, txt, rotation=90, va='center', ha='center', fontsize=fs)
    else:
        ax.annotate('', a, b, arrowprops=dict(arrowstyle='<->', lw=0.8))
        ax.text((a[0] + b[0]) / 2, a[1] + off, txt, ha='center', fontsize=fs)


def marco(ax, titulo, escala, lamina):
    ax.text(1.0, -0.04, f'AquaHuerto · Equipo 2\n{titulo}\nAcotaciones en mm · {escala} · Lámina {lamina}',
            transform=ax.transAxes, ha='right', va='top', fontsize=8,
            bbox=dict(boxstyle='square', fc='white', ec='k'))


def plano_cajon():
    fig, ax = plt.subplots(1, 2, figsize=(14, 6.5))
    a = ax[0]
    a.add_patch(Rectangle((0, 0), 1000, 1000, fc='#D7CCC8', ec='#4E342E', lw=2))
    for y in (170, 500, 830):
        a.plot([0, 1000], [y, y], color='k', lw=2)
        for x in (170, 500, 830):
            a.add_patch(Circle((x, y), 22, fc=AZUL, ec='k', zorder=3))
    a.add_patch(Rectangle((470, 470), 60, 60, fc='white', ec='k', zorder=4))
    a.add_patch(Rectangle((640, 300), 30, 90, fc=VERDE2, ec='k', zorder=4))
    a.text(690, 330, 'EC-5', fontsize=8)
    cota(a, (0, -70), (1000, -70), '1000', off=-45)
    cota(a, (-70, 0), (-70, 1000), '1000', off=-45, vertical=True)
    cota(a, (0, 1060), (170, 1060), '170', off=15)
    cota(a, (170, 1060), (500, 1060), '330', off=15)
    cota(a, (500, 1060), (830, 1060), '330', off=15)
    a.set_xlim(-180, 1120)
    a.set_ylim(-180, 1180)
    a.set_aspect('equal')
    a.axis('off')
    a.set_title('Vista en planta: cajón y 9 microaspersores')
    b = ax[1]
    b.add_patch(Rectangle((0, 120), 1000, 400, fc='none', ec='#4E342E', lw=2))
    b.add_patch(Rectangle((0, 120), 1000, 375, fc='#A1887F', ec='none', alpha=.6))
    b.add_patch(Rectangle((0, 0), 1000, 120, fc='#B0BEC5', ec='k'))
    b.plot([0, 1000], [1520 - 1000 + 120 + 380, 1520 - 1000 + 120 + 380], color='k', lw=2)
    b.text(20, 1050, 'Líneas de aspersores a z = 1520 mm sobre el piso', fontsize=8)
    cota(b, (1080, 120), (1080, 495), '375 sustrato', off=40, vertical=True)
    cota(b, (1180, 120), (1180, 520), '400 cajón', off=40, vertical=True)
    cota(b, (1280, 0), (1280, 120), '120 base', off=40, vertical=True)
    cota(b, (0, -60), (1000, -60), '1000', off=-45)
    b.text(500, 300, 'Sustrato: 74 % peat moss · 19 % tierra negra · 7 % perlita\n'
                     'Capacidad de campo ≈ 48 %VWC · marchitez ≈ 16 %VWC\n1 punto de %VWC = 3.75 L', ha='center', fontsize=8)
    b.set_xlim(-100, 1400)
    b.set_ylim(-150, 1150)
    b.set_aspect('equal')
    b.axis('off')
    b.set_title('Corte lateral: cajón sobre la base')
    marco(b, 'Cajón de cultivo y riego', 'Esc. aprox. 1:10', '1 de 4')
    fig.suptitle('Plano 1. Cajón de cultivo 1.00 × 1.00 m', fontsize=14, weight='bold', color=VERDE)
    return guardar(fig, 'plano_1_cajon.png')


def plano_base_huerto():
    fig, ax = plt.subplots(figsize=(8.5, 7))
    ax.add_patch(Rectangle((0, 0), 1200, 1200, fc='none', ec='k', lw=2))
    ax.add_patch(Rectangle((40, 40), 1120, 1120, fc='none', ec='k', lw=1, ls='--'))
    for x in (300, 600, 900):
        ax.add_patch(Rectangle((x - 20, 40), 40, 1120, fc='#CFD8DC', ec='k'))
    for x, y in ((0, 0), (1160, 0), (0, 1160), (1160, 1160), (0, 580), (1160, 580)):
        ax.add_patch(Rectangle((x, y), 40, 40, fc='#455A64', ec='k'))
    cota(ax, (0, -80), (1200, -80), '1200', off=-50)
    cota(ax, (-80, 0), (-80, 1200), '1200', off=-50, vertical=True)
    ax.text(600, 600, 'PTR 40 × 40 × 3 mm\n6 patas (cuadros oscuros)\n3 travesaños intermedios\n'
                      'Carga de diseño 1500 kg\nEsfuerzo ≈ 94 MPa · deflexión ≈ 3.1 mm\n8.60 m de PTR', ha='center', va='center',
            fontsize=9, bbox=dict(fc='white', ec=GRIS))
    ax.set_xlim(-200, 1350)
    ax.set_ylim(-200, 1300)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title('Plano 2. Base metálica del huerto (vista superior)', fontsize=13, weight='bold', color=VERDE)
    marco(ax, 'Base del huerto', 'Esc. aprox. 1:12', '2 de 4')
    return guardar(fig, 'plano_2_base_huerto.png')


def plano_base_tinaco():
    fig, ax = plt.subplots(figsize=(8.5, 7))
    ax.add_patch(Rectangle((0, 0), 1200, 1200, fc='#ECEFF1', ec='k', lw=2))
    for x, y in ((0, 0), (1150, 0), (0, 1150), (1150, 1150), (575, 575)):
        ax.add_patch(Rectangle((x, y), 50, 50, fc='#455A64', ec='k'))
    for (x1, y1, x2, y2) in ((25, 25, 600, 600), (1175, 25, 600, 600), (25, 1175, 600, 600), (1175, 1175, 600, 600)):
        ax.plot([x1, x2], [y1, y2], color=GRIS, lw=1.5, ls='--')
    ax.add_patch(Circle((600, 600), 450, fc='none', ec=AZUL, lw=2))
    ax.text(600, 1080, 'Tinaco Ø ≈ 900 mm (medido)', ha='center', color=AZUL, fontsize=9)
    cota(ax, (0, -80), (1200, -80), '1200', off=-50)
    cota(ax, (-80, 0), (-80, 1200), '1200', off=-50, vertical=True)
    ax.text(600, 330, 'PTR 50 × 50 × 3 mm · 5 patas · 8 diagonales\nPlaca superior 4 mm · carga de diseño 850 kg\n'
                      'Travesaño ≈ 32 MPa / 0.8 mm · larguero ≈ 75 MPa / 2.3 mm', ha='center', fontsize=8.5,
            bbox=dict(fc='white', ec=GRIS))
    ax.set_xlim(-200, 1350)
    ax.set_ylim(-200, 1300)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title('Plano 3. Base metálica del tinaco (vista superior)', fontsize=13, weight='bold', color=VERDE)
    marco(ax, 'Base del tinaco', 'Esc. aprox. 1:12', '3 de 4')
    return guardar(fig, 'plano_3_base_tinaco.png')


def plano_soporte_panel():
    fig, ax = plt.subplots(figsize=(9, 6))
    L = 680
    ang = math.radians(30)
    x2, y2 = L * math.cos(ang), L * math.sin(ang)
    ax.plot([0, x2], [0, y2], color='k', lw=6)
    ax.add_patch(Polygon([(0, 0), (x2, y2), (x2 + 25 * math.sin(ang), y2 - 25 * math.cos(ang)),
                          (25 * math.sin(ang), -25 * math.cos(ang))], fc='#1565C0', ec='k'))
    ax.plot([x2, x2], [0, y2], color='#455A64', lw=4)
    ax.plot([0, x2 + 60], [0, 0], color='#455A64', lw=4)
    ax.plot([x2 * 0.5, x2 * 0.5], [0, y2 * 0.5], color='#455A64', lw=3)
    a = Polygon([(80, 0), (80 * math.cos(ang / 2) + 10, 40)], closed=False, fill=False)
    ax.annotate('30°', (130, 25), fontsize=11, weight='bold')
    cota(ax, (0, -60), (x2, -60), f'{x2:.0f}', off=-40)
    cota(ax, (x2 + 90, 0), (x2 + 90, y2), f'{y2:.0f}', off=35, vertical=True)
    ax.text(x2 / 2 - 120, y2 / 2 + 80, 'Panel 680 × 620 × 25 mm', rotation=30, fontsize=9, color=AZUL)
    ax.text(50, -170, 'PTR 25 × 25 × 2 mm · 4 puntos de anclaje · orientado al sur\n'
                      'Viento de diseño 1.5 kPa → 0.632 kN · esfuerzo ≈ 20.6 MPa · deflexión ≈ 0.40 mm', fontsize=8.5)
    ax.set_xlim(-100, 800)
    ax.set_ylim(-230, 450)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title('Plano 4. Soporte del panel solar (vista lateral)', fontsize=13, weight='bold', color=VERDE)
    marco(ax, 'Soporte del panel', 'Esc. aprox. 1:8', '4 de 4')
    return guardar(fig, 'plano_4_soporte_panel.png')


def todo():
    salida = {}
    for f in (calibracion_ec5, calibracion_ping, calibracion_caudalimetro, caudal_por_fecha, serie_riego_2l, humedad_tinaco,
              resumen_pruebas, epanet, arquitectura, flujo_automatico, flujo_riego_seguro, estados, flujo_comando, flujo_ia,
              diagrama_hidraulico, diagrama_electrico, plano_cajon, plano_base_huerto, plano_base_tinaco, plano_soporte_panel):
        salida[f.__name__] = f()
    p, filas = riegos_reales()
    salida['riegos_reales'] = p
    salida['_filas_riegos'] = filas
    return salida


if __name__ == '__main__':
    os.makedirs(FIG, exist_ok=True)
    r = todo()
    for k, v in r.items():
        if not k.startswith('_'):
            print(k, v)
