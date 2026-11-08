<template>
<div class="rg">
@@CABECERA@@
<div class="rg-box mb-2 rg-muted">
  <v-icon size="16">mdi-information</v-icon> Las etapas se ESTIMAN por calendario FAO-56 (ajustado con tus correcciones) y grados-día con temperatura del aire de Open-Meteo. Los sensores no pueden confirmar floración ni frutos.
  Comportamiento según el modo activo ({{ modeName(modeNow) }}): MANUAL = tú cambias la etapa · AUTOMÁTICO = el sistema recomienda y pide confirmación · IA = actualiza la etapa estimada, notifica y puedes corregirla.
</div>
<div class="rg-box mb-2"><v-icon size="16">mdi-package-variant-closed</v-icon> <b>Una caja = una plantación.</b> Esta caja ({{ S.device }}) {{ items.length ? 'tiene su plantación activa abajo' : 'no tiene plantación activa' }}. Registrar una nueva cierra la actual, que queda en el historial.</div>
<div class="rg-row mb-2"><v-btn color="primary" variant="tonal" prepend-icon="mdi-plus" @click="newPlanting">{{ items.length ? 'NUEVA PLANTACIÓN (reemplaza la actual)' : 'NUEVA PLANTACIÓN' }}</v-btn>
  <v-btn variant="text" prepend-icon="mdi-refresh" @click="req('plantings_list')">ACTUALIZAR</v-btn></div>
<div v-if="!items.length" class="rg-box rg-muted">No hay plantación activa en esta caja. Registra una con su fecha de siembra o trasplante.</div>
<div v-for="g in items" :key="g.id" class="rg-box mb-3">
  <div class="rg-row" style="justify-content:space-between">
    <div><b style="font-size:16px">{{ g.crop_name }}</b> <span class="rg-muted">{{ g.variety }}</span> <v-chip v-if="g.locked" size="x-small" color="grey">cambios automáticos bloqueados</v-chip></div>
    <div class="rg-muted">siembra {{ g.sow_date || '—' }} · trasplante {{ g.transplant_date || '—' }} · {{ g.elapsed_days }} días</div>
  </div>
  <div class="rg-grid mt-2">
    <div class="rg-kpi"><div class="lbl">Etapa actual</div><div class="val" style="font-size:17px">{{ g.stage_name }}</div><div class="sub">{{ g.stage_index + 1 }} de {{ g.n_stages }}</div></div>
    <div class="rg-kpi"><div class="lbl">Tiempo en etapa</div><div class="val">{{ g.days_in_stage }} <small>de ~{{ g.stage_days }} d</small></div><div class="sub">restan ~{{ g.remaining_stage_days }} días</div></div>
    <div class="rg-kpi"><div class="lbl">Próxima etapa probable</div><div class="val" style="font-size:16px">{{ g.next_stage }}</div></div>
    <div class="rg-kpi"><div class="lbl">Cosecha estimada</div><div class="val" style="font-size:17px">{{ g.harvest_date }}</div><div class="sub">~{{ g.remaining_weeks }} semanas restantes</div></div>
    <div class="rg-kpi"><div class="lbl">Grados-día</div><div class="val">{{ g.gdd ? g.gdd.gdd : '—' }}</div><div class="sub">base {{ g.gdd_base ?? '—' }} °C · {{ g.gdd ? g.gdd.days_with_data + ' días con dato, ' + g.gdd.days_missing + ' sin dato' : 'sin base GDD' }}</div></div>
    <div class="rg-kpi"><div class="lbl">Etapa estimada por calendario</div><div class="val" style="font-size:16px" :class="g.estimated_index > g.stage_index ? 'rg-warn' : ''">{{ g.estimated_name }}</div><div class="sub">{{ g.estimated_index > g.stage_index ? 'sugiere avanzar' : 'coincide' }}</div></div>
  </div>
  <div class="mt-2"><div class="rg-muted">Progreso del ciclo {{ g.progress_pct }} %</div><v-progress-linear :model-value="g.progress_pct" height="12" color="success" rounded></v-progress-linear>
    <div class="rg-muted mt-1">Progreso de la etapa {{ g.stage_progress_pct }} %</div><v-progress-linear :model-value="g.stage_progress_pct" height="8" color="primary" rounded></v-progress-linear></div>
  <div class="rg-row mt-2" style="flex-wrap:nowrap; overflow-x:auto">
    <v-chip v-for="(s, i) in g.stages" :key="i" size="small" :color="i === g.stage_index ? 'primary' : (i < g.stage_index ? 'success' : 'default')" :variant="i === g.stage_index ? 'flat' : 'tonal'">{{ s.nombre }} · {{ s.dias_estimados }} d</v-chip></div>
  <div class="rg-muted mt-1">{{ g.estimate_note }}</div>
  <div class="rg-row mt-2">
    <v-btn size="small" variant="tonal" prepend-icon="mdi-skip-previous" :disabled="g.stage_index === 0" @click="stage(g, 'back')">RETRASAR ETAPA</v-btn>
    <v-btn size="small" variant="tonal" prepend-icon="mdi-skip-next" :disabled="g.stage_index >= g.n_stages - 1" @click="stage(g, 'advance')">ADELANTAR ETAPA</v-btn>
    <v-btn size="small" color="primary" variant="tonal" prepend-icon="mdi-check" :disabled="g.estimated_index === g.stage_index" @click="stage(g, 'confirm')">CONFIRMAR ETAPA ESTIMADA</v-btn>
    <v-btn size="small" variant="tonal" :prepend-icon="g.locked ? 'mdi-lock-open' : 'mdi-lock'" @click="stage(g, g.locked ? 'unlock' : 'lock')">{{ g.locked ? 'DESBLOQUEAR' : 'BLOQUEAR CAMBIOS AUTOMÁTICOS' }}</v-btn>
    <v-btn size="small" variant="tonal" prepend-icon="mdi-calendar-edit" @click="editDates(g)">CORREGIR FECHAS</v-btn>
  </div>
</div>
<div class="rg-sec"><v-icon>mdi-history</v-icon>Historial de cambios de etapa</div>
<div class="rg-box rg-scroll"><table class="rg-table"><tr><th>Fecha</th><th>Plantación</th><th>De → a</th><th>Origen</th><th>Tipo</th><th>Nota</th></tr>
  <tr v-for="(h, i) in hist" :key="i"><td>{{ dt(h.ts) }}</td><td>{{ h.planting_id }}</td><td>{{ h.from_stage ?? '—' }} → {{ h.to_stage ?? '—' }}</td><td>{{ h.source }}</td><td>{{ h.estimated ? 'estimado' : 'confirmado' }}</td><td>{{ h.note }}</td></tr>
  <tr v-if="!hist.length"><td colspan="6" class="rg-muted">Sin cambios registrados.</td></tr></table></div>

<v-dialog v-model="pd.show" max-width="560"><v-card><v-card-title>{{ pd.p.id ? 'Corregir fechas' : 'Nueva plantación' }}</v-card-title><v-card-text>
  <label class="rg-devlbl mb-3">Cultivo <select class="rg-devsel" v-model="pd.p.crop_id"><option :value="null" disabled>Seleccione...</option><option v-for="o in cropItems" :key="o.value" :value="o.value">{{ o.title }}</option></select></label>
  <v-text-field v-model="pd.p.variety" label="Variedad" density="compact" variant="outlined"></v-text-field>
  <div class="rg-row"><v-text-field v-model="pd.p.sow_date" type="date" label="Fecha de siembra" density="compact" variant="outlined"></v-text-field>
    <v-text-field v-model="pd.p.transplant_date" type="date" label="Fecha de trasplante" density="compact" variant="outlined"></v-text-field></div>
  <div v-if="!pd.p.id && items.length" class="rg-warn mb-2">Se cerrará la plantación actual ({{ items[0].crop_name }}); queda en el historial.</div>
  <v-textarea v-model="pd.p.notes" label="Notas" rows="2" density="compact" variant="outlined"></v-textarea></v-card-text>
  <v-card-actions><v-spacer></v-spacer><v-btn @click="pd.show = false">CANCELAR</v-btn><v-btn color="primary" variant="flat" @click="savePlanting">GUARDAR</v-btn></v-card-actions></v-card></v-dialog>
@@DIALOGOS@@
</div>
</template>
<script>
export default {
    mixins: [@@COMUNJS@@],
    data () { return { hist: [], crops: [], pd: { show: false, p: {}, only: true } }; },
    computed: {
        items () { return (((this.S.growth || {}).items) || []).filter(g => g.device === this.S.device); },
        cropItems () { return this.crops.map(c => ({ title: c.nombre + (c.tipo === 'custom' ? ' (personalizado)' : ''), value: c.id })); }
    },
    methods: {
        onPage (m) {
            if (m.topic === 'plantings') { this.hist = m.payload.history || []; if (m.payload.message) this.res = { status: 'OK', label: 'Crecimiento', message: m.payload.message }; }
            else if (m.topic === 'crops') this.crops = m.payload.list || [];
            else if (m.topic === 'growth_result') this.res = { status: m.payload.ok ? 'OK' : 'REJECTED', label: 'Crecimiento', message: m.payload.message };
            else if (m.topic === 'crop_result') this.res = { status: m.payload.ok ? 'SENDING' : 'REJECTED', label: 'Perfil de la etapa', message: m.payload.message };
        },
        stage (g, action) {
            const names = { back: 'retrasar a la etapa anterior', advance: 'adelantar a la siguiente etapa', confirm: 'confirmar la etapa estimada "' + g.estimated_name + '"', lock: 'bloquear los cambios automáticos', unlock: 'desbloquear los cambios automáticos' };
            const applies = !['lock', 'unlock'].includes(action);
            this.ask('¿Confirmas ' + names[action] + '?', g.crop_name + (applies ? '\nSe registrará el cambio y se enviará el perfil de la nueva etapa al ESP32 (requiere su confirmación).' : ''),
                () => this.req('planting_stage', { id: g.id, action }), 'CONFIRMAR');
        },
        newPlanting () { this.req('crops_list'); this.pd = { show: true, only: true, p: { crop_id: null, variety: '', sow_date: new Date(Date.now() - 6 * 3600 * 1000).toISOString().slice(0, 10), transplant_date: '', notes: '' } }; },
        editDates (g) { this.req('crops_list'); this.pd = { show: true, only: false, p: { id: g.id, crop_id: g.crop_id, variety: g.variety, sow_date: g.sow_date, transplant_date: g.transplant_date, notes: '' } }; },
        savePlanting () {
            const p = this.pd.p;
            const repl = (!p.id && this.items.length ? '\nSe cerrará la plantación actual (' + this.items[0].crop_name + '); queda en el historial.' : '') +
                (!p.id ? '\nSe enviará al ESP32 de esta caja el perfil del cultivo en su primera etapa (umbrales calculados con el suelo y la cama); el ESP32 debe confirmarlo.' : '');
            this.ask('¿Confirmas aplicar esta configuración?', 'Caja: ' + this.S.device + '\nCultivo: ' + p.crop_id + '\nSiembra: ' + (p.sow_date || '—') + ' · Trasplante: ' + (p.transplant_date || '—') + repl,
                () => { this.req('planting_save', { planting: p, device: this.S.device }); this.pd.show = false; }, 'GUARDAR');
        }
    },
    mounted () { this.rgMount(); this.req('plantings_list'); this.req('crops_list'); },
    unmounted () { this.rgUnmount(); }
};
</script>
<style>@@ESTILOS@@</style>
