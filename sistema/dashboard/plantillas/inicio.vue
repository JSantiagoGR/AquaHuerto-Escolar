<template>
<div class="rg">
@@CABECERA@@
<div class="rg-sec" style="margin-top:0"><v-icon>mdi-tune-vertical</v-icon>Panel de control</div>
<div class="rg-grid2 mb-2">
  <div class="rg-box">
    <div class="rg-sec" style="margin-top:0"><v-icon>mdi-gauge</v-icon>Sensores</div>
    <div class="rg-gauges">
      <div class="rg-gauge"><div class="t">Humedad del suelo</div>
        <svg viewBox="0 0 120 72"><path d="M 10 62 A 50 50 0 0 1 110 62" fill="none" stroke="#e0e0e0" stroke-width="12"></path>
          <path v-if="vwc !== null" :d="arc(vwc / 60)" fill="none" stroke="#2e7d32" stroke-width="12"></path>
          <text x="60" y="56" text-anchor="middle" font-size="17" font-weight="700">{{ vwc !== null ? n(vwc) : '—' }}</text>
          <text x="10" y="71" text-anchor="middle" font-size="7">0</text><text x="110" y="71" text-anchor="middle" font-size="7">60</text></svg>
        <div class="s">%VWC · {{ (T.soil || {}).status || 'sin lectura' }}</div></div>
      <div class="rg-gauge"><div class="t">Voltaje EC-5</div>
        <svg viewBox="0 0 120 72"><path d="M 10 62 A 50 50 0 0 1 110 62" fill="none" stroke="#e0e0e0" stroke-width="12"></path>
          <path v-if="mv !== null" :d="arc(mv / 2000)" fill="none" :stroke="(T.soil || {}).valid ? '#0277bd' : '#9e9e9e'" stroke-width="12"></path>
          <text x="60" y="56" text-anchor="middle" font-size="17" font-weight="700">{{ mv !== null ? n(mv, 0) : '—' }}</text>
          <text x="10" y="71" text-anchor="middle" font-size="7">0</text><text x="110" y="71" text-anchor="middle" font-size="7">2000</text></svg>
        <div class="s">mV · {{ (T.soil || {}).valid ? 'lectura válida' : 'sin sensor: lectura no válida' }}</div></div>
    </div>
  </div>
  <div class="rg-box">
    <div class="rg-sec" style="margin-top:0"><v-icon>mdi-pump</v-icon>Actuadores</div>
    <div class="rg-lamp"><span class="dot" :class="{ on: ST.pump }"></span><b>Bomba</b> {{ ST.pump ? 'ENCENDIDA' : 'APAGADA' }}</div>
    <div class="rg-lamp"><span class="dot" :class="{ on: ST.valve }"></span><b>Electroválvula</b> {{ ST.valve ? 'ABIERTA' : 'CERRADA' }}</div>
    <div class="rg-lamp"><span class="dot" :class="{ on: powerOn }"></span><b>Salidas de potencia</b> {{ powerOn ? 'habilitadas' : (S.simulated ? 'simuladas (sin hardware)' : 'deshabilitadas') }}</div>
    <div class="rg-muted mt-2">Por seguridad no hay interruptor ON-OFF directo: la bomba solo enciende dentro de un riego con volumen máximo y se apaga con DETENER, al llegar al volumen o por tiempo límite.{{ !S.simulated && !powerOn ? ' Mientras las salidas estén deshabilitadas, el ESP32 rechazará los riegos (no hay etapa de potencia conectada).' : '' }}</div>
  </div>
  <div class="rg-box">
    <div class="rg-sec" style="margin-top:0"><v-icon>mdi-water-pump</v-icon>Sistema de riego</div>
    <div class="rg-row"><span>VOLUMEN OBJETIVO</span><b>{{ volMl }} mL</b></div>
    <v-slider v-model="volMl" :min="100" :max="maxMl" :step="50" color="primary" thumb-label hide-details></v-slider>
    <div v-if="lpp" class="rg-muted mb-1">≈ +{{ n(volMl / 1000 / lpp, 2) }} puntos de %VWC en toda la cama (1 punto ≈ {{ n(lpp, 2) }} L)</div>
    <v-btn block class="mb-2" color="success" prepend-icon="mdi-play" :disabled="busy || watering" @click="askStart">INICIAR RIEGO</v-btn>
    <v-btn block color="error" prepend-icon="mdi-stop" @click="cmd('STOP', {}, 'STOP')">DETENER BOMBA</v-btn>
    <div class="rg-row mt-2"><span>Volumen entregado</span><b>{{ n(deliveredMl, 0) }} mL</b></div>
    <div class="rg-gauge"><div class="t">Agua entregada</div>
      <svg viewBox="0 0 120 72"><path d="M 10 62 A 50 50 0 0 1 110 62" fill="none" stroke="#e0e0e0" stroke-width="12"></path>
        <path v-if="deliveredMl > 0" :d="arc(deliveredMl / gaugeMaxMl)" fill="none" stroke="#0288d1" stroke-width="12"></path>
        <text x="60" y="56" text-anchor="middle" font-size="17" font-weight="700">{{ n(deliveredMl, 0) }}</text>
        <text x="10" y="71" text-anchor="middle" font-size="7">0</text><text x="110" y="71" text-anchor="middle" font-size="7">{{ gaugeMaxMl }}</text></svg>
      <div class="s">mL · {{ watering ? 'riego en curso ' + (W.progress_pct || 0) + ' %' : (lastMl > 0 ? 'último riego' : 'sin riego en curso') }} (calculado por pulsos)</div></div>
    <div v-if="res" class="mt-1"><v-chip size="small" :color="resColor(res.status)">{{ res.status }}</v-chip> <span class="rg-muted">{{ res.label }}: {{ res.message }}</span></div>
  </div>
</div>
<div class="rg-box mb-2">
  <div class="rg-sec" style="margin-top:0"><v-icon>mdi-chart-line</v-icon>Historial de agua (litros del día) y humedad · últimas 24 h</div>
  <svg class="rg-svg" viewBox="0 0 600 190" preserveAspectRatio="none">
    <line x1="40" y1="10" x2="40" y2="170" stroke="#bbb"></line><line x1="40" y1="170" x2="590" y2="170" stroke="#bbb"></line>
    <text x="36" y="14" text-anchor="end" font-size="10">{{ n(waterMax, 1) }} L</text><text x="36" y="172" text-anchor="end" font-size="10">0</text>
    <path :d="chartPts('water')" fill="none" stroke="#0288d1" stroke-width="2"></path>
    <path :d="chartPts('vwc')" fill="none" stroke="#2e7d32" stroke-width="1.5" stroke-dasharray="4 2"></path>
    <text x="45" y="186" font-size="10">{{ hm(H.length ? H[0].ts : 0) }}</text><text x="585" y="186" text-anchor="end" font-size="10">{{ hm(H.length ? H[H.length - 1].ts : 0) }}</text>
  </svg>
  <div class="rg-row rg-muted"><span style="color:#0288d1">— agua hoy (L)</span><span style="color:#2e7d32">- - humedad %VWC (0–60)</span><span>{{ H.length }} lecturas{{ H.length && !H.some(h => h.vwc !== null) ? ' · humedad sin datos (no hay sensor)' : '' }}</span></div>
</div>

<div class="rg-sec"><v-icon>mdi-view-dashboard</v-icon>Resumen</div>
<div class="rg-grid">
  <div class="rg-kpi"><div class="lbl"><v-icon size="16">mdi-water-percent</v-icon>Humedad del suelo</div>
    <div class="val">{{ n(vwc) }} <small>%VWC</small></div>
    <div class="sub">{{ (T.soil || {}).status || 'sin lectura' }} · {{ (T.soil || {}).mv || 0 }} mV</div></div>
  <div class="rg-kpi"><div class="lbl"><v-icon size="16">mdi-target</v-icon>Humedad recomendada</div>
    <div class="val">{{ n(C.hum_target) }} <small>%VWC</small></div>
    <div class="sub">rango {{ n(C.hum_min) }}–{{ n(C.hum_reserve) }} · máx {{ n(C.hum_max) }}</div></div>
  <div class="rg-kpi"><div class="lbl"><v-icon size="16">mdi-thermometer</v-icon>Temperatura ambiente</div>
    <div class="val">{{ n((T.env || {}).temp_c) }} <small>°C</small></div><div class="sub">sensor local {{ (T.env || {}).status || '' }}</div></div>
  <div class="rg-kpi"><div class="lbl"><v-icon size="16">mdi-water-outline</v-icon>Humedad relativa</div>
    <div class="val">{{ n((T.env || {}).rh_pct, 0) }} <small>%HR</small></div><div class="sub">VPD {{ n((T.env || {}).vpd_kpa, 2) }} kPa (aire, no suelo)</div></div>
  <div class="rg-kpi"><div class="lbl"><v-icon size="16">mdi-storage-tank</v-icon>Nivel del tinaco</div>
    <div class="val">{{ (T.tank || {}).calibrated ? n((T.tank || {}).level_pct, 0) + ' %' : 'Sin calibrar' }}</div>
    <div class="sub">{{ (T.tank || {}).status || '' }} {{ (T.tank || {}).valid ? '· ' + n((T.tank || {}).distance_cm) + ' cm' : '' }}</div></div>
  <div class="rg-kpi"><div class="lbl"><v-icon size="16">mdi-cup-water</v-icon>Litros hoy</div>
    <div class="val">{{ n((T.flow || {}).today_l, 2) }} <small>L</small></div><div class="sub">calculados por pulsos ({{ n((T.flow || {}).pulses_per_liter, 0) }} p/L, provisional)</div></div>
  <div class="rg-kpi"><div class="lbl"><v-icon size="16">mdi-scale-balance</v-icon>Balance de agua de hoy</div>
    <div class="val">{{ bal.pierde === null ? '—' : '≈ ' + n(bal.pierde, 1) }} <small>L que pierde la planta</small></div>
    <div class="sub">ET0 {{ n(bal.et0, 1) }} mm × Kc {{ n(bal.kc, 2) }}{{ bal.puntos !== null ? ' ≈ ' + n(bal.puntos, 1) + ' puntos' : '' }} · regado hoy {{ n(bal.regado, 2) }} L · lluvia prevista {{ n(bal.lluviaMm) }} mm (≈ {{ n(bal.lluviaL, 1) }} L)</div></div>
  <div class="rg-kpi"><div class="lbl"><v-icon size="16">mdi-sprout</v-icon>Cultivo · etapa</div>
    <div class="val" style="font-size:18px">{{ ST.crop_name || '—' }}</div><div class="sub">{{ ST.stage || '' }} · perfil v{{ ST.profile_version || 0 }}</div></div>
  <div class="rg-kpi"><div class="lbl"><v-icon size="16">mdi-clock-outline</v-icon>Próximo riego posible</div>
    <div class="val">{{ ST.next_window || '—' }}</div><div class="sub">{{ (S.decision || {}).text || '' }}</div></div>
  <div class="rg-kpi"><div class="lbl"><v-icon size="16">mdi-weather-rainy</v-icon>Lluvia (Open-Meteo)</div>
    <div class="val">{{ n(WX.next24h_precip_mm) }} <small>mm/24 h</small></div>
    <div class="sub">prob. máx {{ n(WX.next24h_prob_max, 0) }} % · {{ WX.fresh ? 'vigente' : 'VENCIDO o sin datos' }}</div></div>
  <div class="rg-kpi"><div class="lbl"><v-icon size="16">mdi-pump</v-icon>Bomba / válvula</div>
    <div class="val" style="font-size:18px"><span :class="ST.pump ? 'rg-bad' : ''">{{ ST.pump ? 'BOMBA ON' : 'Bomba OFF' }}</span> · <span :class="ST.valve ? 'rg-bad' : ''">{{ ST.valve ? 'VÁLVULA ON' : 'Válvula OFF' }}</span></div>
    <div class="sub">estado {{ ST.state || '—' }} {{ S.simulated ? '(simulado)' : '' }}</div></div>
  <div class="rg-kpi"><div class="lbl"><v-icon size="16">mdi-brain</v-icon>IA</div>
    <div class="val" style="font-size:16px">{{ IA.status || '—' }}</div><div class="sub">{{ IA.events_learned || 0 }} riegos · {{ n(IA.drying_hours_learned, 0) }} h de secado aprendidas</div></div>
  <div class="rg-kpi"><div class="lbl"><v-icon size="16">mdi-wifi</v-icon>Conexión ESP32</div>
    <div class="val" style="font-size:16px">{{ ST.wifi ? 'Wi-Fi ' + (ST.rssi || '') + ' dBm' : 'Sin Wi-Fi' }}</div><div class="sub">MQTT {{ ST.mqtt ? 'OK' : 'sin conexión' }} · hora {{ ST.time_valid ? 'sincronizada' : 'NO sincronizada' }}</div></div>
</div>

<div class="rg-sec"><v-icon>mdi-gauge</v-icon>Banda de humedad del cultivo</div>
<div class="rg-box">
  <div class="rg-band">
    <div :style="seg(0, C.hum_critical, '#ef9a9a')"></div>
    <div :style="seg(C.hum_critical, C.hum_min, '#ffcc80')"></div>
    <div :style="seg(C.hum_min, C.hum_reserve, '#a5d6a7')"></div>
    <div :style="seg(C.hum_reserve, C.hum_max, '#90caf9')"></div>
    <div :style="seg(C.hum_max, 60, '#b39ddb')"></div>
    <div v-if="vwc !== null" class="mark" :style="{ left: pos(vwc) + '%' }"></div>
  </div>
  <div class="rg-row rg-muted"><span>■ emergencia &lt; {{ n(C.hum_critical) }}</span><span>■ mínima {{ n(C.hum_min) }}</span><span>■ óptima {{ n(C.hum_target) }}</span><span>■ reserva {{ n(C.hum_reserve) }}</span><span>■ máxima {{ n(C.hum_max) }} %VWC</span><span>| actual {{ n(vwc) }}</span></div>
  <div class="rg-muted mt-1">Los umbrales son %VWC del EC-5 con la calibración vigente (versión de datos {{ C.data_version || 1 }}). {{ ST.crop === 'sin_perfil' ? 'Valores de EJEMPLO: aún no hay perfil de cultivo calibrado.' : '' }}</div>
</div>

<div class="rg-sec"><v-icon>mdi-steering</v-icon>Modo de operación</div>
<div class="rg-modes">
  <div v-for="m in ['MANUAL','AUTOMATICO','IA']" :key="m" class="rg-mode" :class="{ on: modeNow === m }">
    <div><b>{{ modeName(m) }}</b> <v-chip v-if="modeNow === m" size="x-small" color="success">ACTIVO</v-chip></div>
    <div class="rg-muted">{{ m === 'MANUAL' ? 'Solo riegos que tú pidas' : (m === 'AUTOMATICO' ? 'Umbrales del cultivo y horarios' : 'Todo lo del automático + lluvia; predice y dosifica lo mínimo') }}</div>
  </div>
</div>
<v-btn class="mt-2" color="primary" prepend-icon="mdi-swap-horizontal" :disabled="busy" @click="modeMenu = true">SELECCIONAR MODO</v-btn>
<v-dialog v-model="modeMenu" max-width="420"><v-card><v-card-title>Elige el modo</v-card-title>
  <v-card-text><v-btn v-for="m in ['MANUAL','AUTOMATICO','IA']" :key="m" block class="mb-2" :color="modeNow === m ? 'success' : 'primary'" variant="tonal" @click="modeMenu = false; pickMode(m)">{{ modeName(m) }}</v-btn></v-card-text>
  <v-card-actions><v-spacer></v-spacer><v-btn @click="modeMenu = false">CANCELAR</v-btn></v-card-actions></v-card></v-dialog>

<div class="rg-sec"><v-icon>mdi-bell-alert</v-icon>Alertas recientes</div>
<div class="rg-box rg-scroll" style="max-height:220px">
  <div v-if="!(S.alerts || []).length" class="rg-muted">Sin alertas.</div>
  <div v-for="(a, i) in (S.alerts || []).slice(0, 8)" :key="i" class="mb-1">
    <v-chip size="x-small" :color="sevColor(a.severity)">{{ a.severity }}</v-chip> <b>{{ a.name }}</b> <span class="rg-muted">{{ dt(a.ts) }} {{ a.simulated ? '[simulado]' : '' }}</span><div class="rg-muted">{{ a.message }}</div>
  </div>
</div>
@@DIALOGOS@@
</div>
</template>
<script>
export default {
    mixins: [@@COMUNJS@@],
    data () { return { modeMenu: false, volMl: 1000, lastMl: 0, lastTgtMl: 0, lastDev: '' }; },
    computed: {
        W () { return this.ST.watering || {}; },
        watering () { return !!this.W.active; },
        powerOn () { return !!this.ST.power_outputs; },
        mv () { const v = (this.T.soil || {}).mv; return (typeof v === 'number') ? v : null; },
        maxMl () { return Math.max(100, Math.round(Math.min(this.C.max_liters_event || 3, 10) * 1000 / 50) * 50); },
        deliveredMl () { return this.watering ? (this.W.delivered_l || 0) * 1000 : this.lastMl; },
        gaugeMaxMl () { return Math.max(100, Math.round((this.watering && this.W.target_l) ? this.W.target_l * 1000 : (this.lastTgtMl || this.volMl))); },
        H () { return (this.S.hist24 || []).filter(h => h && typeof h.ts === 'number').slice().sort((a, b) => a.ts - b.ts); },
        waterMax () { return Math.max(1, ...this.H.map(h => h.water || 0)); }
    },
    methods: {
        onSnap (p) {
            const w = ((p || {}).state || {}).watering || {};
            if (p && p.device !== this.lastDev) { this.lastDev = p.device; this.lastMl = 0; this.lastTgtMl = 0; }
            if (w.active) { this.lastMl = (w.delivered_l || 0) * 1000; this.lastTgtMl = (w.target_l || 0) * 1000; }
        },
        arc (f) {
            f = Math.max(0.001, Math.min(1, f || 0));
            const a = Math.PI * (1 - f), x = 60 + 50 * Math.cos(a), y = 62 - 50 * Math.sin(a);
            return 'M 10 62 A 50 50 0 0 1 ' + x.toFixed(2) + ' ' + y.toFixed(2);
        },
        chartPts (k) {
            const H = this.H; if (H.length < 2) return '';
            const t0 = H[0].ts, span = Math.max(1, H[H.length - 1].ts - t0);
            const top = k === 'water' ? this.waterMax : 60;
            let d = '', prev = null;
            for (const h of H) {
                if (typeof h[k] !== 'number') { prev = null; continue; }
                const x = (40 + (h.ts - t0) / span * 550).toFixed(1), y = (170 - Math.max(0, Math.min(1, h[k] / top)) * 160).toFixed(1);
                d += ((prev === null || h.ts - prev > 1800) ? ' M ' : ' L ') + x + ' ' + y;
                prev = h.ts;
            }
            return d.trim();
        },
        askStart () {
            const ml = Math.round(this.volMl / 50) * 50;
            this.ask('¿Confirmas iniciar riego de ' + ml + ' mL?', 'Dispositivo: ' + this.S.device + (this.S.simulated ? ' (SIMULADOR)' : ' (ESP32 REAL)') +
                '\nSecuencia: abre válvula → bomba → corta por volumen medido con pulsos → cierra válvula.' +
                (!this.powerOn && !this.S.simulated ? '\nLas salidas de potencia están deshabilitadas: el ESP32 rechazará el riego.' : '') + this.avisoModo(),
                () => this.riego('START_MANUAL', { liters: ml / 1000 }, 'Riego ' + ml + ' mL'), 'INICIAR');
        },
        pos (v) { return Math.max(0, Math.min(100, (v || 0) / 60 * 100)); },
        seg (a, b, color) {
            if (typeof a !== 'number' || typeof b !== 'number') return { display: 'none' };
            return { left: this.pos(a) + '%', width: Math.max(0, this.pos(b) - this.pos(a)) + '%', background: color };
        }
    },
    mounted () { this.rgMount(); },
    unmounted () { this.rgUnmount(); }
};
</script>
<style>@@ESTILOS@@</style>
