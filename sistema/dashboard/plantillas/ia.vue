<template>
<div class="rg">
@@CABECERA@@
<div class="rg-row mb-2">
  <v-chip :color="modeNow === 'IA' ? 'success' : 'grey'" variant="flat">{{ modeNow === 'IA' ? 'MODO IA ACTIVO' : 'Pestaña IA (modo activo: ' + modeName(modeNow) + ')' }}</v-chip>
  <v-btn size="small" color="primary" variant="tonal" prepend-icon="mdi-swap-horizontal" :disabled="busy || modeNow === 'IA'" @click="pickMode('IA')">SELECCIONAR MODO IA</v-btn>
</div>
<v-alert v-if="IA.simulated_model || S.simulated" type="warning" variant="tonal" density="compact" class="mb-2">Modelo aprendido con DATOS SIMULADOS (física sintética del simulador). Sus coeficientes NO describen el suelo real y no se copian al ESP32.</v-alert>
<div class="rg-grid">
  <div class="rg-kpi"><div class="lbl">Aprendizaje</div><div class="val" style="font-size:16px">{{ IA.events_learned || 0 }}/{{ IA.min_events || '?' }} riegos</div>
    <v-progress-linear :model-value="pct(IA.events_learned, IA.min_events)" color="primary" height="6"></v-progress-linear>
    <div class="sub">{{ n(IA.drying_hours_learned, 0) }}/{{ IA.min_hours || '?' }} h de secado</div>
    <v-progress-linear :model-value="pct(IA.drying_hours_learned, IA.min_hours)" color="primary" height="6"></v-progress-linear></div>
  <div class="rg-kpi"><div class="lbl">Validación</div><div class="val" style="font-size:16px">{{ IA.status === 'APRENDIZAJE' ? 'Pendiente' : (IA.status === 'VALIDACION' ? 'En curso' : 'Superada') }}</div>
    <div class="sub">error respuesta {{ n(IA.mae_response_pp, 2) }} pp (meta ±{{ n(IA.tolerance_pp, 1) }}) · secado {{ n(IA.mae_drying_pph, 3) }} pp/h</div></div>
  <div class="rg-kpi"><div class="lbl">Control predictivo</div><div class="val" style="font-size:16px" :class="IA.controls_watering ? 'rg-ok' : ''">{{ IA.controls_watering ? 'ACTIVO' : 'NO ACTIVO' }}</div>
    <div class="sub">{{ IA.controls_watering ? 'La IA calcula los litros' : (IA.mode_ia_selected ? 'Respaldo: automático conservador' : 'Modo IA no seleccionado') }}</div></div>
  <div class="rg-kpi"><div class="lbl">Estado del modelo</div><div class="val" style="font-size:16px">{{ IA.status || '—' }}</div>
    <div class="sub">versión {{ IA.model_version || 0 }} · datos v{{ IA.data_version || 1 }} {{ IA.change_detected ? '· CAMBIO DETECTADO' : '' }}</div></div>
  <div class="rg-kpi"><div class="lbl">Humedad actual</div><div class="val">{{ n(P.vwc_now) }} <small>%VWC</small></div><div class="sub">pérdida prevista {{ n(P.rate_now_pph, 3) }} pp/h</div></div>
  <div class="rg-kpi"><div class="lbl">Humedad objetivo prevista</div><div class="val">{{ n(P.goal_vwc) }} <small>%VWC</small></div><div class="sub">plan: {{ planText }}</div></div>
  <div class="rg-kpi"><div class="lbl">Litros calculados</div><div class="val">{{ n(P.liters, 2) }} <small>L</small></div><div class="sub">ganancia prevista {{ n(P.gain_pp_per_l, 2) }} pp/L</div></div>
  <div class="rg-kpi"><div class="lbl">Autonomía estimada</div><div class="val">{{ P.autonomy_h >= 99 ? '> 48' : n(P.autonomy_h, 0) }} <small>h</small></div>
    <div class="sub">límite inferior ≈ {{ limitTime }}</div></div>
</div>

<div class="rg-sec"><v-icon>mdi-chart-bell-curve</v-icon>Predicción del día (sin regar) y real</div>
<div class="rg-box">
  <svg class="rg-svg" viewBox="0 0 600 190" preserveAspectRatio="none">
    <rect x="0" y="0" width="600" height="190" fill="#fbfdfb"></rect>
    <rect v-if="band" x="0" :y="y(C.hum_reserve)" width="600" :height="Math.max(0, y(C.hum_min) - y(C.hum_reserve))" fill="#e8f5e9"></rect>
    <line x1="0" x2="600" :y1="y(C.hum_min)" :y2="y(C.hum_min)" stroke="#ff9800" stroke-dasharray="4 3"></line>
    <line x1="0" x2="600" :y1="y(C.hum_critical)" :y2="y(C.hum_critical)" stroke="#e53935" stroke-dasharray="4 3"></line>
    <polyline :points="trajPts" fill="none" stroke="#1565c0" stroke-width="2.5"></polyline>
    <polyline :points="realPts" fill="none" stroke="#2e7d32" stroke-width="2"></polyline>
    <polyline :points="predPts" fill="none" stroke="#8e24aa" stroke-width="1.5" stroke-dasharray="3 2"></polyline>
  </svg>
  <div class="rg-row rg-muted"><span style="color:#1565c0">━ trayectoria prevista próximas 24 h</span><span style="color:#2e7d32">━ humedad real (24 h previas)</span><span style="color:#8e24aa">┅ predicción a 1 h vs real</span><span style="color:#ff9800">┅ mínima</span><span style="color:#e53935">┅ emergencia</span>
    <span>escala {{ n(lo, 0) }}–{{ n(hi, 0) }} %VWC</span></div>
</div>

<div class="rg-grid2 mt-2">
  <div class="rg-box">
    <div class="rg-sec" style="margin-top:0"><v-icon>mdi-comment-text</v-icon>Explicación de la decisión</div>
    <div>{{ explanation }}</div>
    <div class="rg-muted mt-2">Variables: {{ (IA.variables || []).join(', ') }}. {{ P.uses_forecast ? (S.simulated ? 'Usa el pronóstico SINTÉTICO del simulador.' : 'Usa el pronóstico vigente de Open-Meteo.') : 'Sin pronóstico vigente: usa solo sensores locales.' }}</div>
    <div class="rg-muted mt-1">Meta de precisión: ±{{ n(IA.tolerance_pp, 0) }} pp tras la infiltración, si las mediciones y la calibración lo permiten. No es una garantía de exactitud física.</div>
  </div>
  <div class="rg-box">
    <div class="rg-sec" style="margin-top:0"><v-icon>mdi-function-variant</v-icon>Coeficientes actuales (RLS)</div>
    <div class="rg-muted">Respuesta al riego Δ%VWC = L·(a0 + a1·u1 + a2·u2 + a3·u3 + a4·u4)</div>
    <div><code>{{ (IA.coef_response || []).join(' · ') }}</code></div>
    <div class="rg-muted mt-1">Secado pp/h = b0 + b1·θ + b2·Kc·VPD + b3·Kc·ET0 + b4·sin(h) + b5·cos(h)</div>
    <div><code>{{ (IA.coef_drying || []).join(' · ') }}</code></div>
    <div class="rg-row mt-2"><v-btn size="small" variant="tonal" prepend-icon="mdi-refresh" @click="loadCompare">ACTUALIZAR COMPARACIONES</v-btn>
      <v-btn size="small" color="error" variant="tonal" prepend-icon="mdi-restore" :disabled="busy" @click="askReset">REINICIAR MODELO</v-btn></div>
  </div>
</div>

<div class="rg-grid2 mt-2">
  <div class="rg-box"><div class="rg-sec" style="margin-top:0"><v-icon>mdi-compare</v-icon>Comparación de modelos (error a 1 h)</div>
    <table class="rg-table"><tr><th>Versión</th><th>Estado</th><th>N</th><th>Error medio (pp)</th></tr>
      <tr v-for="(r, i) in cmp.by_version" :key="i"><td>{{ r.model_version }}</td><td>{{ r.ia_status }}</td><td>{{ r.n }}</td><td>{{ r.mae }}</td></tr>
      <tr v-if="!cmp.by_version.length"><td colspan="4" class="rg-muted">Sin predicciones comparadas todavía.</td></tr></table>
    <div class="rg-sec"><v-icon>mdi-weather-sunny</v-icon>Por estación / cultivo / etapa</div>
    <table class="rg-table"><tr><th>Estación</th><th>Cultivo</th><th>Etapa</th><th>N</th><th>Error (pp)</th></tr>
      <tr v-for="(r, i) in cmp.by_season" :key="i"><td>{{ r.season }}</td><td>{{ r.crop }}</td><td>{{ r.stage }}</td><td>{{ r.n }}</td><td>{{ r.mae }}</td></tr>
      <tr v-if="!cmp.by_season.length"><td colspan="5" class="rg-muted">Se llenará con el uso (verano vs invierno, cultivos y etapas).</td></tr></table>
  </div>
  <div class="rg-box"><div class="rg-sec" style="margin-top:0"><v-icon>mdi-history</v-icon>Historial de correcciones y observaciones</div>
    <div class="rg-scroll"><table class="rg-table"><tr><th>Fecha</th><th>Modelo</th><th>Predicho</th><th>Real</th><th>Error</th><th>Uso</th></tr>
      <tr v-for="(o, i) in cmp.observations" :key="i"><td>{{ dt(o.ts) }}</td><td>{{ o.model === 'SECADO' ? 'Secado pp/h' : 'Respuesta pp' }}</td><td>{{ n(o.predicted, 2) }}</td><td>{{ n(o.observed, 2) }}</td><td>{{ n(o.error, 2) }}</td><td>{{ o.used }}{{ o.simulated ? ' [sim]' : '' }}</td></tr>
      <tr v-if="!cmp.observations.length"><td colspan="6" class="rg-muted">{{ IA.events_learned ? 'Sin observaciones registradas en la base de datos desde que se conectó (las previas no se enviaron).' : 'Sin observaciones: el modelo aún no tiene datos (no se considera entrenado).' }}</td></tr></table></div>
  </div>
</div>
@@DIALOGOS@@
</div>
</template>
<script>
export default {
    mixins: [@@COMUNJS@@],
    data () { return { cmp: { pred: [], by_version: [], by_season: [], snapshots: [], observations: [] } }; },
    computed: {
        P () { return this.IA.plan || {}; },
        band () { return typeof this.C.hum_min === 'number'; },
        lo () { const v = [].concat(this.P.trajectory || [], (this.S.hist24 || []).map(h => h.vwc), [this.C.hum_critical]).filter(x => typeof x === 'number'); return v.length ? Math.floor(Math.min(...v) - 2) : 0; },
        hi () { const v = [].concat(this.P.trajectory || [], (this.S.hist24 || []).map(h => h.vwc), [this.C.hum_reserve]).filter(x => typeof x === 'number'); return v.length ? Math.ceil(Math.max(...v) + 2) : 50; },
        trajPts () { const t = this.P.trajectory || []; return t.map((v, i) => (300 + i * 300 / 24).toFixed(1) + ',' + this.y(v).toFixed(1)).join(' '); },
        realPts () { const now = this.S.server_time || Date.now() / 1000; return (this.S.hist24 || []).filter(h => typeof h.vwc === 'number').map(h => (300 - (now - h.ts) / 86400 * 300).toFixed(1) + ',' + this.y(h.vwc).toFixed(1)).join(' '); },
        predPts () { const now = this.S.server_time || Date.now() / 1000; return (this.cmp.pred || []).filter(p => typeof p.p === 'number' && now - p.t < 86400).map(p => (300 - (now - p.t) / 86400 * 300).toFixed(1) + ',' + this.y(p.p).toFixed(1)).join(' '); },
        planText () { return { NOT_NEEDED: 'no hace falta regar', WATER: 'regar lo mínimo', LIMITED: 'limitado a la reserva', ABOVE_RESERVE: 'sobre la reserva', NO_SOIL: 'sin lectura de suelo', NONE: '—' }[this.P.code] || '—'; },
        limitTime () { if (!(this.P.autonomy_h > 0) || this.P.autonomy_h >= 99) return 'más de 48 h'; return this.dt((this.S.server_time || 0) + this.P.autonomy_h * 3600); },
        explanation () {
            const P = this.P, I = this.IA;
            if (!P.valid) return 'Sin lectura válida de humedad del suelo: la IA no puede planear. Se mantienen las protecciones locales.';
            let t = 'Horizonte hasta el siguiente horario preferido: ' + this.n(P.horizon_h) + ' h. Sin regar, la humedad pasaría de ' + this.n(P.vwc_now) + ' a ' + this.n(P.vwc_end_no_water) + ' %VWC (pérdida prevista ' + this.n(P.loss_pred_pp, 2) + ' pp). ';
            if (P.code === 'NOT_NEEDED') t += 'Se mantiene sobre la mínima + margen: no se riega innecesariamente.';
            else if (P.code === 'WATER') t += 'Para llegar al próximo horario sobre la mínima basta subir a ' + this.n(P.goal_vwc) + ' %VWC: ' + this.n(P.liters, 2) + ' L (menor volumen razonable, sin acercarse al máximo).';
            else if (P.code === 'LIMITED') t += 'La meta necesaria supera la reserva superior: no es alcanzable sin exceder límites; solo se riega hasta ' + this.n(P.goal_vwc) + ' %VWC.';
            else if (P.code === 'ABOVE_RESERVE') t += 'La humedad ya está sobre la reserva superior.';
            if (I.status !== 'PREDICTIVO_ACTIVO') t += ' El modelo está en ' + I.status + ': este plan solo se registra (modo sombra); decide el automático conservador.';
            return t;
        }
    },
    methods: {
        pct (a, b) { return b ? Math.min(100, (a || 0) / b * 100) : 0; },
        y (v) { return 185 - ((v - this.lo) / Math.max(1, this.hi - this.lo)) * 180; },
        loadCompare () { this.req('ia_compare', {}); },
        onPage (m) { if (m.topic === 'ia_compare') this.cmp = m.payload; },
        askReset () {
            this.ask('¿Reiniciar el modelo IA del ESP32?', 'Se borran los coeficientes aprendidos del ESP32 y vuelve a APRENDIZAJE.\nEl historial completo en la base de datos se conserva.',
                () => this.cmd('IA_RESET', { confirm: 'BORRAR_MODELO' }, 'Reinicio del modelo IA'), 'REINICIAR', true);
        }
    },
    mounted () { this.rgMount(); this.loadCompare(); },
    unmounted () { this.rgUnmount(); }
};
</script>
<style>@@ESTILOS@@</style>
