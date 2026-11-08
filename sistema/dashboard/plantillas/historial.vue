<template>
<div class="rg">
@@CABECERA@@
<div class="rg-box">
  <div class="rg-row">
    <v-text-field v-model="from" type="date" label="Desde" density="compact" variant="outlined" hide-details style="max-width:170px"></v-text-field>
    <v-text-field v-model="to" type="date" label="Hasta" density="compact" variant="outlined" hide-details style="max-width:170px"></v-text-field>
    <label class="rg-devlbl">Cultivo <select class="rg-devsel" style="min-width:160px" v-model="crop"><option v-for="o in cropItems" :key="o.value" :value="o.value">{{ o.title }}</option></select></label>
    <label class="rg-devlbl">Agrupar por <select class="rg-devsel" style="min-width:130px" v-model.number="bucket" @change="load">
      <option :value="0">Automático</option><option :value="600">10 minutos</option><option :value="3600">Hora</option>
      <option :value="86400">Día</option><option :value="604800">Semana</option><option :value="2592000">Mes (30 días)</option></select></label>
    <v-btn color="primary" prepend-icon="mdi-filter" @click="load">APLICAR FILTROS</v-btn>
    <v-btn-toggle density="compact" variant="outlined"><v-btn @click="quick(1)">24 h</v-btn><v-btn @click="quick(7)">7 d</v-btn><v-btn @click="quick(30)">30 d</v-btn><v-btn @click="quick(365)">1 año</v-btn></v-btn-toggle>
  </div>
  <div class="rg-row mt-2"><span class="rg-muted">Exportar CSV:</span>
    <v-btn v-for="t in ['lecturas','riegos','alertas','predicciones','lluvia']" :key="t" size="small" variant="tonal" prepend-icon="mdi-download" :href="csv(t)" target="_blank">{{ t }}</v-btn></div>
</div>
<div v-if="loading" class="rg-muted mt-2"><v-progress-linear indeterminate></v-progress-linear> Consultando la base de datos...</div>
<div class="rg-muted mt-1" v-if="h.series">{{ h.series.length }} puntos ({{ bucketTxt }}) · {{ simCount ? simCount + ' puntos SIMULADOS' : 'datos reales' }}</div>

<div class="rg-grid2 mt-2">
  <div class="rg-box" v-for="ch in charts" :key="ch.key">
    <div class="rg-row" style="justify-content:space-between"><b>{{ ch.title }}</b><span class="rg-muted" v-if="hover[ch.key]">{{ hover[ch.key] }}</span></div>
    <svg class="rg-svg" viewBox="0 0 600 190" preserveAspectRatio="none" @mousemove="onHover($event, ch)" @mouseleave="hover[ch.key] = ''">
      <rect width="600" height="190" fill="#fbfdfb"></rect>
      <text x="4" y="12" font-size="11" fill="#5f6b62">{{ n(ch.hi, 0) }}</text><text x="4" y="186" font-size="11" fill="#5f6b62">{{ n(ch.lo, 0) }}</text>
      <path v-for="s in ch.series" :key="s.k" :d="pathD(ch, s.k)" fill="none" :stroke="s.color" stroke-width="2"></path>
      <g v-for="s in ch.series" :key="'p' + s.k"><circle v-for="(q, i) in dots(ch, s.k)" :key="i" :cx="q[0]" :cy="q[1]" r="2.5" :fill="s.color"></circle></g>
      <text v-if="!dots(ch, ch.series[0].k).length" x="300" y="100" text-anchor="middle" font-size="13" fill="#9e9e9e">Sin datos en este periodo</text>
    </svg>
    <div class="rg-row rg-muted"><span v-for="s in ch.series" :key="s.k" :style="{ color: s.color }">━ {{ s.label }}</span><span>{{ fmtRange }}</span></div>
  </div>
  <div class="rg-box">
    <b>Litros diarios (calculados por pulsos)</b>
    <svg class="rg-svg" viewBox="0 0 600 190" preserveAspectRatio="none">
      <rect width="600" height="190" fill="#fbfdfb"></rect>
      <rect v-for="(d, i) in (h.daily || [])" :key="i" :x="i * 600 / Math.max(1, h.daily.length)" :y="185 - d.liters / maxDaily * 170" :width="Math.max(2, 600 / Math.max(1, h.daily.length) - 3)" :height="d.liters / maxDaily * 170" fill="#43a047"><title>{{ d.day }}: {{ n(d.liters, 2) }} L ({{ d.n }} riegos)</title></rect>
    </svg>
    <div class="rg-muted">Total del periodo: <b>{{ n(totalL, 2) }} L</b> en {{ totalN }} riegos · acumulado del dispositivo {{ n((T.flow || {}).total_l, 2) }} L</div>
  </div>
</div>

<div class="rg-sec"><v-icon>mdi-water</v-icon>Eventos de riego</div>
<div class="rg-box rg-scroll"><table class="rg-table"><tr><th>Inicio</th><th>ID</th><th>Motivo</th><th>Modo</th><th>Cultivo</th><th>Litros</th><th>Pulsos</th><th>Caudal</th><th>Humedad antes → después</th><th>Predicción IA</th><th>Resultado</th></tr>
  <tr v-for="e in (h.events || [])" :key="e.event_id"><td>{{ dt(e.ts_start) }}</td><td>{{ e.event_id }}{{ e.simulated ? ' [sim]' : '' }}</td><td>{{ e.reason }}</td><td>{{ e.mode }}</td><td>{{ e.crop }}</td><td>{{ n(e.delivered_l, 2) }}</td><td>{{ e.pulses }}</td><td>{{ n(e.avg_flow_lpm, 2) }}</td>
    <td>{{ n(e.vwc_before) }} → {{ n(e.vwc_after) }}</td><td>{{ e.ia_pred_dvwc !== null ? n(e.ia_pred_dvwc, 2) + ' (err ' + n(e.ia_error, 2) + ')' : '—' }}</td><td>{{ e.result }}</td></tr>
  <tr v-if="!(h.events || []).length"><td colspan="11" class="rg-muted">Sin riegos en el periodo.</td></tr></table></div>

<div class="rg-sec"><v-icon>mdi-weather-pouring</v-icon>Eventos meteorológicos / agua externa</div>
<div class="rg-box rg-scroll"><table class="rg-table"><tr><th>Fecha</th><th>Humedad</th><th>Clasificación ESP32</th><th>Servidor</th><th>Lluvia modelo 24 h</th><th>Causa confirmada</th></tr>
  <tr v-for="r in (h.rain || [])" :key="r.id"><td>{{ dt(r.ts) }}</td><td>{{ n(r.vwc_from) }} → {{ n(r.vwc_to) }}</td><td>{{ r.classification }}</td><td>{{ r.server_classification }}</td><td>{{ n(r.weather_precip_mm) }}</td><td>{{ r.confirmed_cause || 'sin confirmar' }}</td></tr>
  <tr v-if="!(h.rain || []).length"><td colspan="6" class="rg-muted">Sin eventos.</td></tr></table></div>

<div class="rg-sec"><v-icon>mdi-compare-horizontal</v-icon>Comparaciones históricas (por mes, cultivo, etapa y modo)</div>
<div class="rg-row mb-1"><v-btn size="small" variant="tonal" @click="req('compare_history', {})">CALCULAR</v-btn><span class="rg-muted">Agua "ahorrada" solo se mostraría con una comparación válida; por ahora se muestran consumos medidos por pulsos, no ahorros estimados.</span></div>
<div class="rg-grid2">
  <div class="rg-box rg-scroll"><table class="rg-table"><tr><th>Mes</th><th>Cultivo</th><th>Etapa</th><th>Humedad media</th><th>T media</th><th>VPD</th><th>N</th></tr>
    <tr v-for="(r, i) in cmp.readings" :key="i"><td>{{ r.mes }}</td><td>{{ r.crop }}</td><td>{{ r.stage }}</td><td>{{ r.vwc }}</td><td>{{ r.temp }}</td><td>{{ r.vpd }}</td><td>{{ r.n }}{{ r.sim ? ' [sim]' : '' }}</td></tr></table></div>
  <div class="rg-box rg-scroll"><table class="rg-table"><tr><th>Mes</th><th>Cultivo</th><th>Modo</th><th>Litros</th><th>Riegos</th></tr>
    <tr v-for="(r, i) in cmp.irrigation" :key="i"><td>{{ r.mes }}</td><td>{{ r.crop }}</td><td>{{ r.mode }}</td><td>{{ r.liters }}</td><td>{{ r.n }}</td></tr></table></div>
</div>
@@DIALOGOS@@
</div>
</template>
<script>
export default {
    mixins: [@@COMUNJS@@],
    data () { return { from: this.day(1), to: this.day(0), crop: '', bucket: 0, crops: [], h: {}, loading: false, hover: {}, cmp: { readings: [], irrigation: [] } }; },
    computed: {
        cropItems () { return [{ title: 'Todos', value: '' }].concat(this.crops.map(c => ({ title: c.nombre, value: c.id }))); },
        bucketTxt () { return ({ 600: 'promedio cada 10 min', 3600: 'promedio por hora', 21600: 'promedio cada 6 h', 86400: 'promedio por día',
            604800: 'promedio por semana', 2592000: 'promedio por mes (30 días)' })[this.h.bucket] || 'promedio'; },
        simCount () { return (this.h.series || []).filter(s => s.sim).length; },
        maxDaily () { return Math.max(1, ...(this.h.daily || []).map(d => d.liters || 0)); },
        totalL () { return (this.h.daily || []).reduce((a, d) => a + (d.liters || 0), 0); },
        totalN () { return (this.h.daily || []).reduce((a, d) => a + (d.n || 0), 0); },
        fmtRange () { const s = this.h.series || []; return s.length ? this.dt(s[0].t) + ' → ' + this.dt(s[s.length - 1].t) : ''; },
        charts () {
            const s = this.h.series || [];
            const rng = (keys) => { const v = []; s.forEach(r => keys.forEach(k => { if (typeof r[k] === 'number') v.push(r[k]); })); return v.length ? [Math.floor(Math.min(...v) - 1), Math.ceil(Math.max(...v) + 1)] : [0, 1]; };
            const mk = (key, title, series) => { const r = rng(series.map(x => x.k)); return { key, title, series, lo: r[0], hi: r[1] }; };
            return [mk('vwc', 'Humedad del suelo (%VWC)', [{ k: 'vwc', label: 'humedad', color: '#1565c0' }]),
                mk('temp', 'Temperatura (°C) y humedad relativa (%)', [{ k: 'temp', label: 'temperatura', color: '#e65100' }, { k: 'rh', label: 'HR', color: '#00897b' }]),
                mk('tank', 'Nivel del tinaco (%)', [{ k: 'tank', label: 'nivel', color: '#6d4c41' }])];
        }
    },
    methods: {
        day (d) { return new Date(Date.now() - 6 * 3600 * 1000 - d * 86400000).toISOString().slice(0, 10); },
        ts (d, end) { return Math.floor(Date.parse(d + (end ? 'T23:59:59-06:00' : 'T00:00:00-06:00')) / 1000); },
        load () { this.loading = true; this.req('history', { from: this.ts(this.from), to: this.ts(this.to, true), crop: this.crop, bucket: this.bucket }); },
        quick (d) { this.from = this.day(d); this.to = this.day(0); this.load(); },
        csv (t) { return '/riego/export.csv?tipo=' + t + '&desde=' + this.from + '&hasta=' + this.to + '&device=' + (this.S.device || ''); },
        dots (ch, k) {
            const s = this.h.series || []; if (!s.length) return [];
            const t0 = s[0].t, t1 = s[s.length - 1].t || t0 + 1;
            return s.filter(r => typeof r[k] === 'number').map(r => [(r.t - t0) / Math.max(1, t1 - t0) * 596 + 2,
                185 - (r[k] - ch.lo) / Math.max(1, ch.hi - ch.lo) * 175, r.t]);
        },
        pathD (ch, k) {
            // Corta la línea donde faltan datos (hueco mayor a 3 intervalos): no inventa valores entre huecos
            const gap = 3 * (this.h.bucket || 3600);
            let d = '', prev = null;
            for (const q of this.dots(ch, k)) {
                d += ((prev === null || q[2] - prev > gap) ? ' M ' : ' L ') + q[0].toFixed(1) + ' ' + q[1].toFixed(1);
                prev = q[2];
            }
            return d.trim();
        },
        onHover (ev, ch) {
            const s = this.h.series || []; if (!s.length) return;
            const rect = ev.currentTarget.getBoundingClientRect();
            const f = (ev.clientX - rect.left) / rect.width;
            const r = s[Math.max(0, Math.min(s.length - 1, Math.round(f * (s.length - 1))))];
            this.hover[ch.key] = this.dt(r.t) + ': ' + ch.series.map(x => x.label + ' ' + this.n(r[x.k])).join(' · ');
        },
        onPage (m) {
            if (m.topic === 'history') { this.h = m.payload; this.loading = false; }
            else if (m.topic === 'crops') this.crops = m.payload.list || [];
            else if (m.topic === 'compare') this.cmp = m.payload;
        }
    },
    mounted () { this.rgMount(); this.req('crops_list'); this.load(); },
    unmounted () { this.rgUnmount(); }
};
</script>
<style>@@ESTILOS@@</style>
