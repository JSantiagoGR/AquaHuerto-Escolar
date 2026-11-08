<template>
<div class="rg">
@@CABECERA@@
<div class="rg-row mb-2">
  <v-chip :color="modeNow === 'MANUAL' ? 'success' : 'grey'" variant="flat">{{ modeNow === 'MANUAL' ? 'MODO MANUAL ACTIVO' : 'Estás viendo la pestaña MANUAL (modo activo: ' + modeName(modeNow) + ')' }}</v-chip>
  <v-btn size="small" color="primary" variant="tonal" prepend-icon="mdi-swap-horizontal" :disabled="busy || modeNow === 'MANUAL'" @click="pickMode('MANUAL')">SELECCIONAR MODO MANUAL</v-btn>
</div>
<div class="rg-grid2">
  <div class="rg-box">
    <div class="rg-sec" style="margin-top:0"><v-icon>mdi-cup-water</v-icon>Regar una cantidad fija</div>
    <v-slider v-model="liters" :min="0.1" :max="maxL" :step="0.1" thumb-label color="primary" hide-details></v-slider>
    <div class="rg-row"><v-text-field v-model.number="liters" type="number" label="Litros" density="compact" variant="outlined" hide-details style="max-width:140px" :min="0.1" :max="maxL" step="0.1"></v-text-field>
      <span class="rg-muted">máximo por evento {{ n(C.max_liters_event, 2) }} L · quedan hoy {{ n(remainingToday, 2) }} L</span></div>
    <div v-if="lpp" class="rg-muted mt-1">≈ +{{ n(liters / lpp, 2) }} puntos de %VWC en toda la cama (1 punto ≈ {{ n(lpp, 2) }} L)</div>
    <v-btn class="mt-3" color="primary" prepend-icon="mdi-water" :disabled="busy || watering || !(liters > 0)" @click="askLiters">REGAR {{ n(liters, 1) }} L</v-btn>
  </div>
  <div class="rg-box">
    <div class="rg-sec" style="margin-top:0"><v-icon>mdi-target</v-icon>Regar hasta una humedad</div>
    <v-text-field v-model.number="goal" type="number" step="0.5" :label="'Humedad deseada (%VWC) · óptima ' + n(C.hum_target) + ' · máx ' + n(C.hum_max)" density="compact" variant="outlined" hide-details style="max-width:260px"></v-text-field>
    <div class="mt-1">Actual <b>{{ n(vwc) }}</b> %VWC → meta <b>{{ n(goalVal) }}</b> %VWC</div>
    <div v-if="lpp && vwc !== null">Faltan ≈ <b>{{ n(Math.max(0, goalVal - vwc) * lpp, 1) }} L</b> ({{ n(Math.max(0, goalVal - vwc)) }} puntos × {{ n(lpp, 2) }} L)</div>
    <div class="rg-muted">Se aplica en dosis de hasta {{ n(C.liters_per_cycle, 2) }} L, con {{ n(C.infilt_min, 0) }} min de infiltración y una nueva lectura entre dosis (máx. {{ C.max_cycles }} ciclos y {{ n(C.max_liters_event, 2) }} L). <b>No riega sin parar:</b> echa una dosis, hace una pausa, vuelve a medir y repite hasta llegar a la meta o al límite.</div>
    <v-btn class="mt-3" color="primary" variant="tonal" prepend-icon="mdi-water-check" :disabled="busy || watering || vwc === null" @click="askTarget">REGAR HASTA {{ n(goalVal) }} %</v-btn>
  </div>
  <div class="rg-box">
    <div class="rg-sec" style="margin-top:0"><v-icon>mdi-stop-circle</v-icon>Detener</div>
    <div class="rg-muted">STOP apaga bomba y electroválvula de inmediato (no requiere confirmación).</div>
    <v-btn class="mt-3" color="error" size="large" block prepend-icon="mdi-stop" @click="cmd('STOP', {}, 'STOP')">DETENER TODO</v-btn>
  </div>
</div>

<div class="rg-sec"><v-icon>mdi-progress-clock</v-icon>Ejecución</div>
<div class="rg-box">
  <div class="rg-row"><v-chip :color="watering ? 'primary' : 'grey'" variant="flat">{{ ST.state || '—' }}</v-chip>
    <span v-if="watering">{{ W.type }} · {{ n(W.delivered_l, 3) }} de {{ n(W.target_l, 3) }} L · {{ W.elapsed_s }} s</span>
    <span v-else-if="EV.active">Evento {{ EV.kind }} · ciclo {{ EV.cycles }} · {{ n(EV.liters, 2) }} L · infiltración restante {{ EV.infiltration_remaining_s }} s</span>
    <span v-else class="rg-muted">Sin riego en curso</span></div>
  <v-progress-linear class="mt-2" :model-value="W.progress_pct || 0" height="14" color="primary" rounded><small>{{ W.progress_pct || 0 }} %</small></v-progress-linear>
  <div class="rg-grid mt-3">
    <div class="rg-kpi"><div class="lbl">Caudal</div><div class="val">{{ n(watering ? W.flow_lpm : (T.flow || {}).lpm, 2) }} <small>L/min</small></div></div>
    <div class="rg-kpi"><div class="lbl">Pulsos del riego</div><div class="val">{{ W.pulses || 0 }}</div><div class="sub">total {{ (T.flow || {}).pulses || 0 }}</div></div>
    <div class="rg-kpi"><div class="lbl">Volumen calculado</div><div class="val">{{ n(W.delivered_l, 3) }} <small>L</small></div><div class="sub">por pulsos: no medido con recipiente</div></div>
    <div class="rg-kpi"><div class="lbl">Temperatura</div><div class="val">{{ n((T.env || {}).temp_c) }} <small>°C</small></div></div>
    <div class="rg-kpi"><div class="lbl">Tinaco</div><div class="val" style="font-size:18px">{{ (T.tank || {}).calibrated ? n((T.tank || {}).level_pct, 0) + ' %' : 'Sin calibrar' }}</div></div>
    <div class="rg-kpi"><div class="lbl">Humedad</div><div class="val">{{ n(vwc) }} <small>%VWC</small></div><div class="sub">objetivo {{ n(C.hum_target) }}</div></div>
  </div>
</div>

<div class="rg-sec"><v-icon>mdi-chart-line</v-icon>Humedad y riego</div>
<div class="rg-grid2">
  <div class="rg-box">
    <div class="rg-row" style="justify-content:space-between"><b>En vivo (últimos 30 min)</b><span class="rg-muted">{{ live.length }} lecturas</span></div>
    <svg class="rg-svg" viewBox="0 0 600 190" preserveAspectRatio="none">
      <rect width="600" height="190" fill="#fbfdfb"></rect>
      <line v-if="C.hum_target" x1="0" x2="600" :y1="yV(C.hum_target, liveLo, liveHi)" :y2="yV(C.hum_target, liveLo, liveHi)" stroke="#2e7d32" stroke-dasharray="2 4"></line>
      <text x="4" y="12" font-size="11" fill="#1565c0">{{ n(liveHi, 0) }} %</text><text x="4" y="186" font-size="11" fill="#1565c0">{{ n(liveLo, 0) }} %</text>
      <text x="596" y="12" text-anchor="end" font-size="11" fill="#0288d1">{{ n(liveLmax, 1) }} L</text>
      <path :d="livePath('vwc')" fill="none" stroke="#1565c0" stroke-width="2"></path>
      <path :d="livePath('l')" fill="none" stroke="#0288d1" stroke-width="2" stroke-dasharray="6 3"></path>
      <text v-if="!live.length" x="300" y="100" text-anchor="middle" font-size="13" fill="#9e9e9e">Juntando lecturas en vivo...</text>
    </svg>
    <div class="rg-row rg-muted"><span style="color:#1565c0">━ humedad %VWC</span><span style="color:#0288d1">- - litros regados hoy</span><span style="color:#2e7d32">··· óptima {{ n(C.hum_target) }}</span></div>
  </div>
  <div class="rg-box">
    <div class="rg-row" style="justify-content:space-between"><b>Historial</b>
      <span><v-btn v-for="r in [[1, '24 h'], [7, '7 d'], [30, '30 d'], [365, '1 año']]" :key="r[0]" size="x-small" class="ml-1" :variant="histDays === r[0] ? 'flat' : 'tonal'" color="primary" @click="loadHist(r[0])">{{ r[1] }}</v-btn></span></div>
    <svg class="rg-svg" viewBox="0 0 600 190" preserveAspectRatio="none">
      <rect width="600" height="190" fill="#fbfdfb"></rect>
      <rect v-for="(e, i) in histEvents" :key="'e' + i" :x="e.x - 3" :y="185 - e.h" width="6" :height="e.h" fill="#0288d1" opacity="0.55"><title>{{ e.txt }}</title></rect>
      <text x="4" y="12" font-size="11" fill="#1565c0">{{ n(histHi, 0) }} %</text><text x="4" y="186" font-size="11" fill="#1565c0">{{ n(histLo, 0) }} %</text>
      <path :d="histPath" fill="none" stroke="#1565c0" stroke-width="2"></path>
      <text v-if="!histPath" x="300" y="100" text-anchor="middle" font-size="13" fill="#9e9e9e">{{ histLoading ? 'Consultando...' : 'Sin lecturas en este periodo' }}</text>
    </svg>
    <div class="rg-row rg-muted"><span style="color:#1565c0">━ humedad %VWC</span><span style="color:#0288d1">▮ riegos (alto = litros)</span><span>{{ histEventsN }} riegos · {{ n(histLiters, 2) }} L</span></div>
  </div>
</div>

<div class="rg-sec"><v-icon>mdi-sprout</v-icon>Recomendaciones del cultivo</div>
<div class="rg-box">
  <div><b>{{ ST.crop_name || 'Sin perfil' }}</b> · {{ ST.stage }} · Kc {{ n(C.kc, 2) }}</div>
  <ul class="rg-muted" style="margin-left:18px">
    <li>Mantener entre {{ n(C.hum_min) }} y {{ n(C.hum_reserve) }} %VWC; óptima {{ n(C.hum_target) }}.</li>
    <li>Preferir riego entre {{ C.win1_start }}–{{ C.win1_end }}{{ C.win2_en ? ' y ' + C.win2_start + '–' + C.win2_end : '' }}; evitar {{ C.midday_start }}–{{ C.midday_end }}.</li>
    <li v-if="vwc !== null && vwc >= C.hum_reserve">La humedad ya supera la reserva superior: no se recomienda regar.</li>
    <li v-if="vwc !== null && vwc < C.hum_critical" class="rg-bad">Humedad bajo el umbral de emergencia.</li>
    <li v-if="ST.crop === 'sin_perfil'" class="rg-warn">Los umbrales actuales son de ejemplo; aplica un cultivo en la página CULTIVOS.</li>
  </ul>
</div>
@@DIALOGOS@@
</div>
</template>
<script>
export default {
    mixins: [@@COMUNJS@@],
    data () { return { liters: 1.0, goal: null, live: [], hist: {}, histDays: 1, histLoading: false }; },
    computed: {
        W () { return this.ST.watering || {}; },
        goalVal () { return (typeof this.goal === 'number' && this.goal > 0) ? this.goal : this.C.hum_target; },
        EV () { return this.ST.event || {}; },
        watering () { return !!this.W.active; },
        maxL () { return Math.max(0.1, Math.min(this.C.max_liters_event || 3, 10)); },
        remainingToday () { return (this.C.max_liters_daily || 0) - ((this.T.flow || {}).today_l || 0); },
        liveLo () { const v = this.live.filter(p => typeof p.vwc === 'number').map(p => p.vwc).concat([this.C.hum_target || 30]); return Math.floor(Math.min(...v) - 2); },
        liveHi () { const v = this.live.filter(p => typeof p.vwc === 'number').map(p => p.vwc).concat([this.C.hum_target || 30]); return Math.ceil(Math.max(...v) + 2); },
        liveLmax () { return Math.max(1, ...this.live.map(p => p.l || 0)); },
        histRange () { const a = this.hist.args || {}; const now = Math.floor(Date.now() / 1000); return [a.from || now - 86400, a.to || now]; },
        histVals () { return (this.hist.series || []).filter(r => typeof r.vwc === 'number'); },
        histLo () { return this.histVals.length ? Math.floor(Math.min(...this.histVals.map(r => r.vwc)) - 2) : 0; },
        histHi () { return this.histVals.length ? Math.ceil(Math.max(...this.histVals.map(r => r.vwc)) + 2) : 60; },
        histPath () {
            const [t0, t1] = this.histRange, gap = 3 * (this.hist.bucket || 3600);
            let d = '', prev = null;
            for (const r of this.histVals) {
                const x = 2 + (r.t - t0) / Math.max(1, t1 - t0) * 596;
                d += ((prev === null || r.t - prev > gap) ? ' M ' : ' L ') + x.toFixed(1) + ' ' + this.yV(r.vwc, this.histLo, this.histHi).toFixed(1);
                prev = r.t;
            }
            return d.trim();
        },
        histEv () { return (this.hist.events || []).filter(e => (e.delivered_l || 0) > 0); },
        histEventsN () { return this.histEv.length; },
        histLiters () { return this.histEv.reduce((a, e) => a + (e.delivered_l || 0), 0); },
        histEvents () {
            const [t0, t1] = this.histRange, mx = Math.max(0.5, ...this.histEv.map(e => e.delivered_l));
            return this.histEv.map(e => ({ x: 2 + (e.ts_start - t0) / Math.max(1, t1 - t0) * 596, h: Math.max(3, e.delivered_l / mx * 120),
                txt: this.dt(e.ts_start) + ': ' + this.n(e.delivered_l, 2) + ' L (' + e.result + ')' }));
        }
    },
    methods: {
        yV (v, lo, hi) { return 185 - (v - lo) / Math.max(1, hi - lo) * 175; },
        onSnap (p) {
            // Serie en vivo: humedad y litros del día (incluye el riego en curso). Se guardan 30 min.
            if (!p || !p.device) return;
            if (this._dev !== p.device) { this._dev = p.device; this.live = []; this.loadHist(this.histDays); }
            const tel = p.telemetry || {}, st = p.state || {}, w = st.watering || {};
            const soil = tel.soil || {};
            const v = soil.valid ? soil.vwc_pct : null;
            const l = ((tel.flow || {}).today_l || 0) + (w.active ? (w.delivered_l || 0) : 0);
            const now = Math.floor(Date.now() / 1000), last = this.live[this.live.length - 1];
            if (!last || last.vwc !== v || Math.abs((last.l || 0) - l) > 0.005 || now - last.t >= 15) {
                this.live.push({ t: now, vwc: v, l });
                while (this.live.length && this.live[0].t < now - 1800) this.live.shift();
            }
        },
        livePath (k) {
            const now = Math.floor(Date.now() / 1000), t0 = now - 1800;
            const lo = k === 'vwc' ? this.liveLo : 0, hi = k === 'vwc' ? this.liveHi : this.liveLmax;
            let d = '', prev = null;
            for (const p of this.live) {
                if (typeof p[k] !== 'number') { prev = null; continue; }
                const x = 2 + (p.t - t0) / 1800 * 596;
                d += ((prev === null || p.t - prev > 120) ? ' M ' : ' L ') + x.toFixed(1) + ' ' + this.yV(p[k], lo, hi).toFixed(1);
                prev = p.t;
            }
            return d.trim();
        },
        loadHist (days) {
            this.histDays = days; this.histLoading = true;
            const now = Math.floor(Date.now() / 1000);
            this.req('history', { from: now - days * 86400, to: now, device: this.S.device });
        },
        onPage (m) { if (m.topic === 'history') { this.hist = m.payload; this.histLoading = false; } },
        askLiters () {
            const L = Math.round(this.liters * 10) / 10;
            this.ask('¿Confirmas regar ' + L + ' L?', 'Dispositivo: ' + this.S.device + (this.S.simulated ? ' (SIMULADOR)' : ' (ESP32 REAL)') +
                '\nSecuencia: abre válvula → bomba → corta por volumen medido con pulsos → cierra válvula.' +
                (this.ST.power_outputs === false && !this.S.simulated ? '\nLas salidas de potencia están deshabilitadas: el ESP32 rechazará el riego.' : '') + this.avisoModo(),
                () => this.riego('START_MANUAL', { liters: L }, 'Riego manual ' + L + ' L'), 'REGAR');
        },
        askTarget () {
            const g = Math.round(this.goalVal * 10) / 10;
            this.ask('¿Regar hasta ' + g + ' %VWC?',
                'Por dosis de hasta ' + this.n(this.C.liters_per_cycle, 1) + ' L con pausa de ' + this.n(this.C.infilt_min, 0) + ' min y nueva lectura entre cada una (no riega sin parar). Puedes detenerlo con STOP.' + this.avisoModo(),
                () => this.riego('START_TO_TARGET', { goal: g }, 'Riego hasta ' + g + ' %'), 'REGAR');
        }
    },
    mounted () { this.rgMount(); },
    unmounted () { this.rgUnmount(); }
};
</script>
<style>@@ESTILOS@@</style>
