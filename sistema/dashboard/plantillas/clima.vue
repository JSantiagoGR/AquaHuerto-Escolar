<template>
<div class="rg">
@@CABECERA@@
<div class="rg-row mb-2">
  <v-chip :color="WX.ok && WX.fresh ? 'success' : (WX.ts_fetch ? 'warning' : 'error')" variant="flat"><v-icon start>mdi-cloud-check</v-icon>Open-Meteo: {{ WX.ok && WX.fresh ? 'VIGENTE' : (WX.ts_fetch ? 'VENCIDO / con error' : 'sin datos') }}</v-chip>
  <span class="rg-muted">Actualizado {{ dt(WX.ts_fetch) }} ({{ ago(WX.ts_fetch) }}) · {{ WX.ok_count || 0 }} consultas OK, {{ WX.fail_count || 0 }} fallidas {{ WX.last_error ? '· último error: ' + WX.last_error : '' }}</span>
  <v-btn size="small" variant="tonal" prepend-icon="mdi-refresh" @click="req('weather_refresh')">ACTUALIZAR</v-btn>
</div>
<div class="rg-muted mb-2">Ubicación {{ n(WX.lat, 4) }}, {{ n(WX.lon, 4) }} ({{ (S.location || {}).label }}) · elevación {{ WX.elevation }} m · {{ WX.timezone }}. Datos de MODELO meteorológico: no son mediciones del huerto. Uso gratuito no comercial, consulta cada 30 min.</div>
<div class="rg-grid">
  <div class="rg-kpi"><div class="lbl">Temperatura (modelo)</div><div class="val">{{ n(cur.temp) }} <small>°C</small></div><div class="sub">sensor local: {{ n((T.env || {}).temp_c) }} °C</div></div>
  <div class="rg-kpi"><div class="lbl">Humedad relativa (modelo)</div><div class="val">{{ n(cur.rh, 0) }} <small>%</small></div><div class="sub">sensor local: {{ n((T.env || {}).rh_pct, 0) }} %</div></div>
  <div class="rg-kpi"><div class="lbl">VPD próxima hora</div><div class="val">{{ n((H[firstFuture] || {}).vpd, 2) }} <small>kPa</small></div><div class="sub">local: {{ n((T.env || {}).vpd_kpa, 2) }} kPa</div></div>
  <div class="rg-kpi"><div class="lbl">ET0 hoy (FAO)</div><div class="val">{{ n(WX.et0_today_mm, 2) }} <small>mm</small></div><div class="sub">ETc ≈ Kc {{ n(C.kc, 2) }} × ET0 = {{ n((C.kc || 1) * (WX.et0_today_mm || 0), 2) }} mm</div></div>
  <div class="rg-kpi"><div class="lbl">Balance de agua de hoy</div><div class="val">{{ bal.pierde === null ? '—' : '≈ ' + n(bal.pierde, 1) }} <small>L</small></div><div class="sub">pierde la planta en {{ n(bal.area, 1) }} m² (1 mm = 1 L/m²) · regado hoy {{ n(bal.regado, 2) }} L · lluvia prevista 24 h ≈ {{ n(bal.lluviaL, 1) }} L. Informativo: el riego lo decide la humedad medida.</div></div>
  <div class="rg-kpi"><div class="lbl">Lluvia últimas 24 h</div><div class="val">{{ n(WX.past24h_precip_mm) }} <small>mm</small></div><div class="sub">estimada por el modelo</div></div>
  <div class="rg-kpi"><div class="lbl">Lluvia próximas 24 h</div><div class="val">{{ n(WX.next24h_precip_mm) }} <small>mm</small></div><div class="sub">probabilidad máx {{ n(WX.next24h_prob_max, 0) }} %</div></div>
  <div class="rg-kpi"><div class="lbl">Decisión del ESP32</div><div class="val" style="font-size:16px">{{ ST.rain_expected ? 'Lluvia prevista: la IA pospone solo si cubre lo que falta' : 'Sin lluvia relevante' }}</div><div class="sub">pronóstico del ESP32: {{ (S.weather_dev || {}).fresh ? 'vigente' : 'no vigente' }}</div></div>
  <div class="rg-kpi"><div class="lbl">Horas recomendadas</div><div class="val" style="font-size:16px">{{ (WX.recommended || []).map(r => r.hour + ':00').join(', ') || '—' }}</div><div class="sub">horarios preferidos con menor VPD y sin lluvia probable</div></div>
</div>
<div class="rg-sec"><v-icon>mdi-chart-line</v-icon>Pronóstico horario (48 h)</div>
<div class="rg-box">
  <svg class="rg-svg" viewBox="0 0 600 190" preserveAspectRatio="none">
    <rect width="600" height="190" fill="#fbfdfb"></rect>
    <rect v-for="(h, i) in H" :key="'p' + i" :x="x(i) - 2" :y="190 - Math.min(80, (h.pprob || 0) * 0.8)" width="4" :height="Math.min(80, (h.pprob || 0) * 0.8)" fill="#90caf9"></rect>
    <rect v-for="(h, i) in H" :key="'r' + i" :x="x(i) - 2" :y="190 - Math.min(120, (h.precip || 0) * 40)" width="4" :height="Math.min(120, (h.precip || 0) * 40)" fill="#1565c0"></rect>
    <polyline :points="H.map((h, i) => x(i) + ',' + yt(h.temp)).join(' ')" fill="none" stroke="#e65100" stroke-width="2"></polyline>
    <polyline :points="H.map((h, i) => x(i) + ',' + yv(h.vpd)).join(' ')" fill="none" stroke="#6a1b9a" stroke-width="1.5" stroke-dasharray="4 2"></polyline>
    <line v-if="firstFuture >= 0" :x1="x(firstFuture)" :x2="x(firstFuture)" y1="0" y2="190" stroke="#455a64" stroke-dasharray="2 3"></line>
  </svg>
  <div class="rg-row rg-muted"><span style="color:#e65100">━ temperatura ({{ n(tmin, 0) }}–{{ n(tmax, 0) }} °C)</span><span style="color:#6a1b9a">┅ VPD</span><span style="color:#90caf9">▮ probabilidad de lluvia</span><span style="color:#1565c0">▮ lluvia mm</span><span>┆ ahora</span></div>
</div>
<div class="rg-sec"><v-icon>mdi-calendar</v-icon>Días (7 previos estimados y 3 de pronóstico)</div>
<div class="rg-box rg-scroll"><table class="rg-table"><tr><th>Fecha</th><th>Tipo</th><th>T máx</th><th>T mín</th><th>Lluvia mm</th><th>Prob. %</th><th>ET0 mm</th></tr>
  <tr v-for="d in (WX.daily || [])" :key="d.date"><td>{{ d.date }}</td><td>{{ d.date < today ? 'reciente (modelo)' : (d.date === today ? 'hoy' : 'pronóstico') }}</td><td>{{ n(d.tmax) }}</td><td>{{ n(d.tmin) }}</td><td>{{ n(d.precip) }}</td><td>{{ n(d.pprob, 0) }}</td><td>{{ n(d.et0, 2) }}</td></tr></table></div>
@@DIALOGOS@@
</div>
</template>
<script>
export default {
    mixins: [@@COMUNJS@@],
    data () { return {}; },
    computed: {
        cur () { return this.WX.current || {}; },
        H () { return this.WX.hourly || []; },
        firstFuture () { const now = this.S.server_time || Date.now() / 1000; return this.H.findIndex(h => h.t > now); },
        tmin () { const v = this.H.map(h => h.temp).filter(x => typeof x === 'number'); return v.length ? Math.min(...v) : 0; },
        tmax () { const v = this.H.map(h => h.temp).filter(x => typeof x === 'number'); return v.length ? Math.max(...v) : 1; },
        today () { return new Date(Date.now() - 6 * 3600 * 1000).toISOString().slice(0, 10); }
    },
    methods: {
        x (i) { return 4 + i * 592 / Math.max(1, this.H.length - 1); },
        yt (t) { return 180 - ((t - this.tmin) / Math.max(1, this.tmax - this.tmin)) * 160; },
        yv (v) { return 180 - Math.min(1, (v || 0) / 5) * 160; }
    },
    mounted () { this.rgMount(); },
    unmounted () { this.rgUnmount(); }
};
</script>
<style>@@ESTILOS@@</style>
