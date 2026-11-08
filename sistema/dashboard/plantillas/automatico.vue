<template>
<div class="rg">
@@CABECERA@@
<div class="rg-row mb-2">
  <v-chip :color="modeNow === 'AUTOMATICO' ? 'success' : 'grey'" variant="flat">{{ modeNow === 'AUTOMATICO' ? 'MODO AUTOMÁTICO ACTIVO' : 'Pestaña AUTOMÁTICO (modo activo: ' + modeName(modeNow) + ')' }}</v-chip>
  <v-btn size="small" color="primary" variant="tonal" prepend-icon="mdi-swap-horizontal" :disabled="busy || modeNow === 'AUTOMATICO'" @click="pickMode('AUTOMATICO')">SELECCIONAR MODO AUTOMÁTICO</v-btn>
</div>
<div class="rg-grid2">
  <div class="rg-box">
    <div class="rg-sec" style="margin-top:0"><v-icon>mdi-lightbulb-on</v-icon>Decisión actual</div>
    <v-chip :color="decColor((S.decision || {}).code)" variant="flat">{{ (S.decision || {}).code || '—' }}</v-chip>
    <div class="mt-1"><b>{{ (S.decision || {}).text || 'Sin decisión' }}</b></div>
    <div class="rg-muted mt-1">Humedad {{ n(vwc) }} %VWC · próximo horario {{ ST.next_window }} · {{ (S.decision || {}).in_window ? 'dentro de horario' : 'fuera de horario' }}{{ (S.decision || {}).in_midday ? ' · MEDIODÍA' : '' }}{{ ST.rain_expected ? ' · lluvia prevista' : '' }}</div>
  </div>
  <div class="rg-box">
    <div class="rg-sec" style="margin-top:0"><v-icon>mdi-information</v-icon>Cómo decide</div>
    <ul class="rg-muted" style="margin-left:18px">
      <li>No riega si la humedad está en el rango adecuado (sobre óptima − histéresis).</li>
      <li>Si está bajo la óptima pero segura, espera el horario preferido (mañana; tarde opcional).</li>
      <li>Evita el mediodía. Con humedad bajo la emergencia riega un ciclo limitado a cualquier hora.</li>
      <li>El pronóstico de lluvia NO lo usa este modo: solo el modo IA pospone por lluvia, y solo si la lluvia prevista alcanza a cubrir lo que le falta a la tierra (cama de 1 m²: 1 mm = 1 L).</li>
      <li>Si el tinaco está en el mínimo, riega igual y avisa.</li>
      <li>Tras cada dosis: espera infiltración, vuelve a medir y repite solo si los límites lo permiten.</li>
      <li v-if="lpp">En tu cama 1 punto de %VWC ≈ {{ n(lpp, 2) }} L: la histéresis de {{ n(C.auto_hyst_pp) }} puntos ≈ {{ n(C.auto_hyst_pp * lpp, 1) }} L y una dosis de {{ n(C.liters_per_cycle, 1) }} L sube ≈ {{ n(C.liters_per_cycle / lpp, 2) }} puntos.</li>
    </ul>
  </div>
</div>

<div class="rg-sec"><v-icon>mdi-tune</v-icon>Parámetros (borrador)</div>
<div v-if="dirty" class="rg-draft"><v-icon>mdi-pencil-alert</v-icon> Hay cambios SIN GUARDAR. Los valores activos en el ESP32 no cambian hasta confirmar.</div>
<div class="rg-grid2">
  <div class="rg-box">
    <div class="rg-muted mb-2">Humedad volumétrica del suelo (%VWC)</div>
    <v-text-field v-for="f in humFields" :key="f.k" v-model.number="draft[f.k]" :label="f.l" type="number" step="0.5" density="compact" variant="outlined" :hint="'activo: ' + n(C[f.k])" persistent-hint class="mb-2"></v-text-field>
  </div>
  <div class="rg-box">
    <div class="rg-muted mb-2">Horarios preferidos (hora local)</div>
    <v-switch v-model="draft.win1_en" label="Ventana matutina" color="primary" density="compact" hide-details></v-switch>
    <div class="rg-row"><v-text-field v-model="draft.win1_start" label="Inicio" type="time" density="compact" variant="outlined" hide-details></v-text-field><v-text-field v-model="draft.win1_end" label="Fin" type="time" density="compact" variant="outlined" hide-details></v-text-field></div>
    <v-switch v-model="draft.win2_en" label="Ventana al atardecer" color="primary" density="compact" hide-details class="mt-2"></v-switch>
    <div class="rg-row"><v-text-field v-model="draft.win2_start" label="Inicio" type="time" density="compact" variant="outlined" hide-details></v-text-field><v-text-field v-model="draft.win2_end" label="Fin" type="time" density="compact" variant="outlined" hide-details></v-text-field></div>
    <div class="rg-row mt-2"><v-text-field v-model="draft.midday_start" label="Evitar desde" type="time" density="compact" variant="outlined" hide-details></v-text-field><v-text-field v-model="draft.midday_end" label="hasta" type="time" density="compact" variant="outlined" hide-details></v-text-field></div>
  </div>
  <div class="rg-box">
    <div class="rg-muted mb-2">Límites y tiempos</div>
    <v-text-field v-for="f in limFields" :key="f.k" v-model.number="draft[f.k]" :label="f.l" type="number" :step="f.s || 0.1" density="compact" variant="outlined" :hint="'activo: ' + C[f.k]" persistent-hint class="mb-2"></v-text-field>
    <v-switch v-model="draft.emergency_en" label="Riego de emergencia habilitado" color="primary" density="compact" hide-details></v-switch>
    <v-switch v-model="draft.rain_postpone_en" label="Posponer si se pronostica lluvia" color="primary" density="compact" hide-details></v-switch>
  </div>
</div>
<div class="rg-row mt-3">
  <v-btn color="primary" prepend-icon="mdi-content-save" :disabled="!dirty || busy" @click="save">GUARDAR</v-btn>
  <v-btn variant="tonal" prepend-icon="mdi-undo" :disabled="!dirty" @click="cancel">CANCELAR</v-btn>
  <span class="rg-muted">El ESP32 valida la configuración completa y responde con la versión aplicada.</span>
</div>

<div class="rg-sec"><v-icon>mdi-history</v-icon>Justificación de las decisiones recientes</div>
<div class="rg-box rg-scroll"><table class="rg-table"><tr><th>Hora</th><th>Decisión</th><th>Motivo</th><th>Humedad</th></tr>
  <tr v-for="(x, i) in (S.decisions || [])" :key="i"><td>{{ dt(x.ts) }}</td><td><v-chip size="x-small" :color="decColor(x.code)">{{ x.code }}</v-chip></td><td>{{ x.text }}</td><td>{{ n(x.vwc) }}</td></tr></table></div>
@@DIALOGOS@@
</div>
</template>
<script>
export default {
    mixins: [@@COMUNJS@@],
    data () {
        return ({ KEYS: ['hum_critical', 'hum_min', 'hum_target', 'hum_reserve', 'hum_max', 'auto_hyst_pp', 'win1_en', 'win1_start', 'win1_end',
    'win2_en', 'win2_start', 'win2_end', 'midday_start', 'midday_end', 'liters_per_cycle', 'max_liters_event', 'max_liters_daily',
    'infilt_min', 'max_cycles', 'emergency_en', 'emergency_liters', 'temp_postpone_c', 'rain_postpone_en', 'rain_prob_pct', 'rain_mm'],  draft: {}, base: {},
            humFields: [{ k: 'hum_critical', l: 'Umbral de emergencia' }, { k: 'hum_min', l: 'Humedad mínima normal' }, { k: 'hum_target', l: 'Humedad óptima (recomendada)' },
                { k: 'hum_reserve', l: 'Reserva superior segura' }, { k: 'hum_max', l: 'Humedad máxima permitida' }, { k: 'auto_hyst_pp', l: 'Histéresis bajo la óptima' }],
            limFields: [{ k: 'liters_per_cycle', l: 'Litros por ciclo' }, { k: 'max_liters_event', l: 'Máx. litros por evento' }, { k: 'max_liters_daily', l: 'Máx. litros por día' },
                { k: 'infilt_min', l: 'Infiltración (min)', s: 1 }, { k: 'max_cycles', l: 'Máx. ciclos por evento', s: 1 }, { k: 'emergency_liters', l: 'Litros de emergencia' },
                { k: 'temp_postpone_c', l: 'Posponer sobre (°C)', s: 0.5 }, { k: 'rain_prob_pct', l: 'Prob. de lluvia para posponer (%)', s: 5 }, { k: 'rain_mm', l: 'Lluvia prevista para posponer (mm/6 h)' }] });
    },
    computed: {
        dirty () { return this.KEYS.some(k => String(this.draft[k]) !== String(this.base[k])); }
    },
    methods: {
        load (force) {
            const c = this.C;
            if (!c || c.hum_min === undefined) return;
            const b = {}; this.KEYS.forEach(k => { b[k] = c[k]; });
            const was = this.dirty;
            this.base = b;
            if (force || !was) this.draft = Object.assign({}, b);
        },
        onSnap () { this.load(false); },
        cancel () { this.draft = Object.assign({}, this.base); },
        save () {
            const params = {};
            this.KEYS.forEach(k => { if (String(this.draft[k]) !== String(this.base[k])) params[k] = this.draft[k]; });
            const d = Object.assign({}, this.base, this.draft);
            if (!(d.hum_critical + 1 <= d.hum_min && d.hum_min + 1 <= d.hum_target && d.hum_target + 0.5 <= d.hum_reserve && d.hum_reserve <= d.hum_max)) {
                this.ask('Revisa los umbrales', 'Debe cumplirse: emergencia < mínima < óptima < reserva ≤ máxima.', null, 'ENTENDIDO'); return;
            }
            const txt = Object.keys(params).map(k => k + ': ' + this.base[k] + ' → ' + params[k]).join('\n');
            this.ask('¿Confirmas aplicar esta configuración?', txt, () => {
                this.cmd('APPLY_CONFIG', { version: (this.S.profile_version || 0) + 1, params }, 'Parámetros automáticos');
            }, 'APLICAR');
        },
        onResult (r) { if (r.cmd === 'APPLY_CONFIG' && r.status === 'OK') this.$nextTick(() => setTimeout(() => this.load(true), 1500)); }
    },
    mounted () { this.rgMount(); this.load(true); },
    unmounted () { this.rgUnmount(); }
};
</script>
<style>@@ESTILOS@@</style>
