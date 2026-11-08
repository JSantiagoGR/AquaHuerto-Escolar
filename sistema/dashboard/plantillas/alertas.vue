<template>
<div class="rg">
@@CABECERA@@
<div class="rg-grid">
  <div v-for="g in groups" :key="g.k" class="rg-kpi" :style="count(g) ? 'border-color:#e57373;background:#fff5f5' : ''">
    <div class="lbl"><v-icon size="16">{{ g.icon }}</v-icon>{{ g.t }}</div>
    <div class="val" :class="count(g) ? 'rg-bad' : 'rg-ok'">{{ count(g) ? count(g) + ' activa(s)' : 'OK' }}</div>
  </div>
</div>
<div class="rg-row mt-2"><v-btn size="small" variant="tonal" prepend-icon="mdi-refresh" @click="load">ACTUALIZAR</v-btn>
  <v-switch v-model="onlyActive" label="Solo activas" color="primary" density="compact" hide-details></v-switch>
  <label class="rg-devlbl">Severidad <select class="rg-devsel" style="min-width:140px" v-model="sev"><option v-for="o in ['TODAS','CRITICAL','WARNING','INFO']" :key="o" :value="o">{{ o }}</option></select></label></div>

<div class="rg-sec"><v-icon>mdi-weather-pouring</v-icon>Aumentos de humedad sin riego de la bomba (confirma la causa)</div>
<div class="rg-box rg-scroll">
  <div v-if="!pending.length" class="rg-muted">Sin eventos pendientes de confirmar.</div>
  <div v-for="r in pending" :key="r.id" class="mb-2">
    <b>{{ label(r.server_classification || r.classification) }}</b> · {{ dt(r.ts) }} · humedad {{ n(r.vwc_from) }} → {{ n(r.vwc_to) }} %VWC (+{{ n(r.rise_pp) }}) {{ r.simulated ? '[SIMULADO]' : '' }}
    <span class="rg-muted"> · lluvia del modelo 24 h: {{ n(r.weather_precip_mm) }} mm</span>
    <div class="rg-row mt-1"><v-btn v-for="c in causes" :key="c.v" size="x-small" variant="tonal" @click="confirm(r, c)">{{ c.t }}</v-btn></div>
  </div>
  <div class="rg-muted">Estos aumentos NO se suman a los litros de la bomba. La IA no los usa para aprender el secado.</div>
</div>

<div class="rg-sec"><v-icon>mdi-bell</v-icon>Registro de alertas</div>
<div class="rg-box rg-scroll" style="max-height:480px"><table class="rg-table"><tr><th>Fecha</th><th>Dispositivo</th><th>Severidad</th><th>Código</th><th>Mensaje</th><th>Estado</th><th></th></tr>
  <tr v-for="a in shown" :key="a.id"><td>{{ dt(a.ts) }}</td><td>{{ a.device }}{{ a.simulated ? ' [sim]' : '' }}</td><td><v-chip size="x-small" :color="sevColor(a.severity)">{{ a.severity }}</v-chip></td><td>{{ a.code }}</td><td>{{ a.message }}</td>
    <td>{{ a.acknowledged ? 'revisada' : (a.active ? 'ACTIVA' : 'resuelta') }}</td><td><v-btn v-if="!a.acknowledged" size="x-small" variant="text" @click="ack(a)">MARCAR REVISADA</v-btn></td></tr>
  <tr v-if="!shown.length"><td colspan="7" class="rg-muted">Sin alertas.</td></tr></table></div>
@@DIALOGOS@@
</div>
</template>
<script>
export default {
    mixins: [@@COMUNJS@@],
    data () {
        return ({ list: [], rain: [], onlyActive: false, sev: 'TODAS',
            causes: [{ v: 'LLUVIA', t: 'FUE LLUVIA' }, { v: 'RIEGO_EXTERNO', t: 'RIEGO EXTERNO' }, { v: 'ERROR_SENSOR', t: 'ERROR DEL SENSOR' }, { v: 'OTRO', t: 'OTRA CAUSA' }],
            groups: [{ k: ['HUM_CRITICAL'], t: 'Humedad crítica', icon: 'mdi-water-alert' }, { k: ['HUM_EXCESS'], t: 'Humedad excesiva', icon: 'mdi-water-plus' },
                { k: ['TANK_LOW'], t: 'Nivel bajo del tinaco', icon: 'mdi-storage-tank-outline' }, { k: ['NO_FLOW', 'FLOW_HIGH', 'FLOW_WHEN_IDLE', 'PUMP_TIMEOUT', 'SAFETY_TRIP'], t: 'Flujo / bomba', icon: 'mdi-pipe-leak' },
                { k: ['SOIL_SENSOR', 'TANK_SENSOR', 'ENV_SENSOR', 'POSIBLE_ERROR_SENSOR', 'SOIL_NO_RESPONSE'], t: 'Fallos de sensores', icon: 'mdi-chip' },
                { k: ['DEVICE_OFFLINE', 'BROKER_DOWN', 'COMMS'], t: 'Pérdida MQTT', icon: 'mdi-lan-disconnect' }, { k: ['WEATHER_STALE', 'WEATHER_ERROR'], t: 'Pronóstico vencido', icon: 'mdi-cloud-off-outline' },
                { k: ['POSIBLE_LLUVIA'], t: 'Posible lluvia', icon: 'mdi-weather-rainy' }, { k: ['POSIBLE_RIEGO_EXTERNO', 'AUMENTO_NO_EXPLICADO'], t: 'Posible riego externo', icon: 'mdi-sprinkler' },
                { k: ['IA_PREDICTION_ERROR', 'IA_CHANGE_DETECTED'], t: 'Errores del modelo IA', icon: 'mdi-brain' }, { k: ['STAGE_CHANGE', 'STAGE_RECOMMENDED'], t: 'Cambios de etapa', icon: 'mdi-sprout' },
                { k: ['STORAGE_ERROR'], t: 'Almacenamiento', icon: 'mdi-database-alert' }] });
    },
    computed: {
        shown () { return this.list.filter(a => (!this.onlyActive || (a.active && !a.acknowledged)) && (this.sev === 'TODAS' || a.severity === this.sev)); },
        pending () { return this.rain.filter(r => !r.confirmed_cause); }
    },
    methods: {
        count (g) { return this.list.filter(a => a.active && !a.acknowledged && g.k.includes(a.code)).length; },
        label (c) { return { POSIBLE_LLUVIA: 'POSIBLE LLUVIA', POSIBLE_RIEGO_EXTERNO: 'POSIBLE RIEGO EXTERNO', AUMENTO_NO_EXPLICADO: 'AUMENTO DE HUMEDAD NO EXPLICADO', POSIBLE_ERROR_SENSOR: 'POSIBLE ERROR DEL SENSOR' }[c] || c; },
        load () { this.req('alerts_list', { limit: 300 }); },
        ack (a) { this.req('alert_ack', { id: a.id }); },
        confirm (r, c) { this.ask('¿Registrar la causa como "' + c.t + '"?', 'Evento del ' + this.dt(r.ts) + '. Queda guardado en la base de datos.', () => this.req('rain_confirm', { id: r.id, cause: c.v }), 'REGISTRAR'); },
        onPage (m) { if (m.topic === 'alerts_list') { this.list = m.payload.alerts || []; this.rain = m.payload.rain || []; } },
        onSnap () { const t = (this.S.alerts || [])[0]; if (t && t.ts !== this._lastTs) { this._lastTs = t.ts; this.load(); } }
    },
    mounted () { this.rgMount(); this.load(); },
    unmounted () { this.rgUnmount(); }
};
</script>
<style>@@ESTILOS@@</style>
