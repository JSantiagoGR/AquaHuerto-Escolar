<template>
<div class="rg">
@@CABECERA@@
<div class="rg-grid2">
  <div class="rg-box">
    <div class="rg-sec" style="margin-top:0"><v-icon>mdi-sprout</v-icon>Configuración ACTIVA en el ESP32</div>
    <div><b>{{ ST.crop_name || '—' }}</b> · etapa {{ ST.stage || '—' }} · perfil v{{ ST.profile_version || 0 }}</div>
    <div class="rg-muted">emergencia {{ n(C.hum_critical) }} · mínima {{ n(C.hum_min) }} · óptima {{ n(C.hum_target) }} · reserva {{ n(C.hum_reserve) }} · máxima {{ n(C.hum_max) }} %VWC · Kc {{ n(C.kc, 2) }}</div>
    <div class="rg-muted">Horarios {{ C.win1_start }}–{{ C.win1_end }}{{ C.win2_en ? ' y ' + C.win2_start + '–' + C.win2_end : '' }}</div>
  </div>
  <div class="rg-box">
    <div class="rg-sec" style="margin-top:0"><v-icon>mdi-layers-triple</v-icon>Calibración del suelo</div>
    <div v-if="S.soil_cal">Capacidad de campo <b>{{ S.soil_cal.fc_vwc }}</b> · marchitez <b>{{ S.soil_cal.wp_vwc }}</b> %VWC <span class="rg-muted">({{ S.soil_cal.method }})</span></div>
    <div v-if="lpp" class="rg-muted">Cama {{ S.bed.area_m2 }} m² × {{ S.bed.depth_cm }} cm = {{ n(lpp * 100, 0) }} L de sustrato · 1 punto ≈ {{ n(lpp, 2) }} L{{ S.soil_cal ? ' · agua útil ≈ ' + n((S.soil_cal.fc_vwc - S.soil_cal.wp_vwc) * lpp, 0) + ' L' : '' }}</div>
    <div v-else class="rg-warn"><v-icon size="16">mdi-alert</v-icon> PENDIENTE DE CALIBRACIÓN: sin capacidad de campo y marchitez medidas con el EC-5, los perfiles NO cambian los umbrales de humedad del ESP32 (se conservan los actuales). Configúralo en CONFIGURACIÓN.</div>
    <div class="rg-muted mt-1">ET0 hoy (Open-Meteo): {{ n(WX.et0_today_mm, 2) }} mm</div>
  </div>
</div>

<div class="rg-sec"><v-icon>mdi-format-list-bulleted</v-icon>Cultivos</div>
<div class="rg-row mb-2">
  <v-btn-toggle v-model="filter" density="compact" color="primary" mandatory><v-btn value="base">LOS 10 CULTIVOS</v-btn><v-btn value="custom">MIS CULTIVOS PERSONALIZADOS</v-btn></v-btn-toggle>
  <v-btn color="primary" variant="tonal" prepend-icon="mdi-plus" @click="newCrop">AGREGAR</v-btn>
</div>
<div class="rg-row">
  <v-chip v-for="c in shown" :key="c.id" :color="sel && sel.id === c.id ? 'primary' : (ST.crop === c.id ? 'success' : 'default')" :variant="sel && sel.id === c.id ? 'flat' : 'tonal'" @click="select(c)">
    {{ c.nombre }}<v-icon v-if="ST.crop === c.id" end size="14">mdi-check-circle</v-icon></v-chip>
  <span v-if="!shown.length" class="rg-muted">{{ filter === 'custom' ? 'Aún no hay cultivos personalizados: usa AGREGAR o DUPLICA uno de los 10.' : 'Cargando...' }}</span>
</div>

<div v-if="sel" class="rg-box mt-3">
  <div class="rg-row" style="justify-content:space-between">
    <div class="rg-sec" style="margin:0"><v-icon>mdi-eye</v-icon>VISTA PREVIA (borrador): {{ sel.nombre }} <v-chip size="x-small">{{ sel.tipo === 'base' ? 'cultivo base' : 'personalizado' }}</v-chip></div>
    <div class="rg-row">
      <v-btn size="small" variant="tonal" prepend-icon="mdi-content-copy" @click="duplicate">DUPLICAR</v-btn>
      <v-btn v-if="sel.tipo === 'custom'" size="small" variant="tonal" prepend-icon="mdi-pencil" @click="edit">EDITAR</v-btn>
      <v-btn v-if="sel.tipo === 'custom'" size="small" color="error" variant="tonal" prepend-icon="mdi-delete" @click="del">ELIMINAR</v-btn>
    </div>
  </div>
  <div class="rg-muted">{{ sel.cientifico }} · {{ sel.familia }} · temporada {{ sel.temporada }} · ciclo ~{{ sel.ciclo_total_dias }} días · p = {{ sel.p_agotamiento }} · raíz {{ (sel.raiz_m || []).join('–') }} m</div>
  <div class="rg-muted" v-if="sel.sensibilidad_deficit">Sensibilidad al déficit: <b>{{ sel.sensibilidad_deficit.nivel }}</b> ({{ sel.sensibilidad_deficit.texto }})</div>
  <div class="rg-muted" v-if="sel.temp_aire_crecimiento">Temperatura del aire óptima {{ sel.temp_aire_crecimiento.opt_min_c ?? '—' }}–{{ sel.temp_aire_crecimiento.opt_max_c ?? '—' }} °C, máx {{ sel.temp_aire_crecimiento.max_c ?? '—' }} °C · germinación (suelo) {{ (sel.temp_germinacion_suelo || {}).opt_min_c }}–{{ (sel.temp_germinacion_suelo || {}).opt_max_c }} °C · base GDD {{ (sel.gdd || {}).base_c ?? '—' }} °C</div>
  <div class="rg-muted">{{ sel.notas }}</div>
  <table class="rg-table mt-2"><tr><th></th><th>Etapa</th><th>Días</th><th>Kc</th><th>Emerg.</th><th>Mín.</th><th>Óptima</th><th>Reserva</th><th>Máx.</th><th>Estado</th></tr>
    <tr v-for="(e, i) in sel.etapas" :key="i" :style="i === stageSel ? 'background:#fff8e1' : ''">
      <td><v-radio-group v-model="stageSel" hide-details density="compact" inline><v-radio :value="i"></v-radio></v-radio-group></td>
      <td>{{ e.nombre }}</td><td>{{ e.dias }}</td><td>{{ e.kc }}</td>
      <template v-if="th(i).ok"><td>{{ th(i).hum_critical }}</td><td>{{ th(i).hum_min }}</td><td><b>{{ th(i).hum_target }}</b></td><td>{{ th(i).hum_reserve }}</td><td>{{ th(i).hum_max }}</td><td class="rg-ok">calculado</td></template>
      <template v-else><td colspan="5" class="rg-warn">{{ th(i).estado }}</td><td class="rg-muted">{{ th(i).motivo }}</td></template>
    </tr></table>
  <div class="rg-muted mt-1">{{ th(stageSel).metodo || '' }}</div>
  <div class="rg-muted">Fuentes: {{ (sel.fuentes || []).join(', ') }}</div>
  <div class="rg-row mt-3">
    <v-btn color="primary" prepend-icon="mdi-upload" :disabled="busy" @click="applyCrop">GUARDAR COMO CULTIVO ACTIVO (etapa {{ (sel.etapas[stageSel] || {}).nombre }})</v-btn>
    <v-btn variant="tonal" prepend-icon="mdi-close" @click="sel = null">CANCELAR</v-btn>
  </div>
  <div class="rg-muted mt-1">Seleccionar un cultivo solo muestra la vista previa: el cultivo activo no cambia hasta GUARDAR y confirmar, y solo se reporta como aplicado cuando el ESP32 confirma la versión.</div>
</div>

<v-dialog v-model="ed.show" max-width="900" scrollable>
  <v-card>
    <v-card-title>{{ ed.isNew ? 'Nuevo cultivo personalizado' : 'Editar cultivo personalizado' }}</v-card-title>
    <v-card-text>
      <div v-if="edDirty" class="rg-draft">Cambios sin guardar</div>
      <div class="rg-row"><v-text-field v-model="ed.c.nombre" label="Nombre" density="compact" variant="outlined" hide-details></v-text-field>
        <v-text-field v-model.number="ed.c.p_agotamiento" label="p (0.1–0.8, FAO-56)" type="number" step="0.05" density="compact" variant="outlined" hide-details style="max-width:170px"></v-text-field>
        <v-text-field v-model.number="ed.c.gdd.base_c" label="Base GDD (°C)" type="number" density="compact" variant="outlined" hide-details style="max-width:150px"></v-text-field></div>
      <div class="rg-row mt-2"><v-text-field v-model.number="ed.c.temp_aire_crecimiento.opt_min_c" label="T. óptima mín (°C)" type="number" density="compact" variant="outlined" hide-details></v-text-field>
        <v-text-field v-model.number="ed.c.temp_aire_crecimiento.opt_max_c" label="T. óptima máx (°C)" type="number" density="compact" variant="outlined" hide-details></v-text-field>
        <v-text-field v-model.number="ed.c.temp_aire_crecimiento.max_c" label="T. máxima (°C)" type="number" density="compact" variant="outlined" hide-details></v-text-field></div>
      <div class="rg-row mt-2"><v-text-field v-model="ed.c.horarios.win1[0]" label="Horario 1 inicio" type="time" density="compact" variant="outlined" hide-details></v-text-field>
        <v-text-field v-model="ed.c.horarios.win1[1]" label="fin" type="time" density="compact" variant="outlined" hide-details></v-text-field>
        <v-text-field v-model="ed.c.horarios.win2[0]" label="Horario 2 inicio" type="time" density="compact" variant="outlined" hide-details></v-text-field>
        <v-text-field v-model="ed.c.horarios.win2[1]" label="fin" type="time" density="compact" variant="outlined" hide-details></v-text-field></div>
      <div class="rg-sec">Etapas (umbrales opcionales en %VWC; si se dejan vacíos se calculan con la calibración del suelo)</div>
      <div v-for="(e, i) in ed.c.etapas" :key="i" class="rg-box mb-2">
        <div class="rg-row"><v-text-field v-model="e.nombre" label="Etapa" density="compact" variant="outlined" hide-details></v-text-field>
          <v-text-field v-model.number="e.dias" label="Días" type="number" density="compact" variant="outlined" hide-details style="max-width:100px"></v-text-field>
          <v-text-field v-model.number="e.kc" label="Kc" type="number" step="0.05" density="compact" variant="outlined" hide-details style="max-width:100px"></v-text-field>
          <v-btn icon="mdi-delete" size="small" variant="text" :disabled="ed.c.etapas.length <= 1" @click="ed.c.etapas.splice(i, 1)"></v-btn></div>
        <div class="rg-row mt-1"><v-text-field v-for="k in UK" :key="k.k" v-model.number="e.umbrales[k.k]" :label="k.l" type="number" step="0.5" density="compact" variant="outlined" hide-details style="max-width:120px"></v-text-field></div>
      </div>
      <v-btn size="small" variant="tonal" prepend-icon="mdi-plus" :disabled="ed.c.etapas.length >= 8" @click="addStage">AGREGAR ETAPA</v-btn>
      <v-textarea v-model="ed.c.notas" label="Notas" rows="2" density="compact" variant="outlined" class="mt-2" hide-details></v-textarea>
      <div v-if="ed.err" class="rg-bad mt-2">{{ ed.err }}</div>
    </v-card-text>
    <v-card-actions><v-spacer></v-spacer>
      <v-btn @click="cancelEdit">CANCELAR</v-btn>
      <v-btn color="primary" variant="flat" @click="saveEdit">GUARDAR</v-btn></v-card-actions>
  </v-card>
</v-dialog>
@@DIALOGOS@@
</div>
</template>
<script>
export default {
    mixins: [@@COMUNJS@@],
    data () {
        return ({ crops: [], filter: 'base', sel: null, stageSel: 0, ed: { show: false, c: this.blankCrop(), orig: '', isNew: true, err: '' },
            UK: [{ k: 'hum_critical', l: 'Emerg.' }, { k: 'hum_min', l: 'Mínima' }, { k: 'hum_target', l: 'Óptima' }, { k: 'hum_reserve', l: 'Reserva' }, { k: 'hum_max', l: 'Máxima' }] });
    },
    computed: {
        shown () { return this.crops.filter(c => c.tipo === this.filter); },
        edDirty () { return JSON.stringify(this.ed.c) !== this.ed.orig; }
    },
    methods: {
        calcUmbrales: @@UMBRALES_FN@@,
        blankCrop () { return ({ nombre: '', tipo: 'custom', temporada: '', familia: '', cientifico: '', p_agotamiento: 0.4, raiz_m: [0.3, 0.6],
    gdd: { base_c: 10 }, temp_aire_crecimiento: { opt_min_c: null, opt_max_c: null, max_c: null }, horarios: { win1: ['06:00', '09:00'], win2: ['18:00', '20:00'] },
    etapas: [{ nombre: 'Establecimiento', dias: 20, kc: 0.6, umbrales: {} }, { nombre: 'Desarrollo', dias: 30, kc: 0.85, umbrales: {} },
        { nombre: 'Producción', dias: 40, kc: 1.05, umbrales: {} }, { nombre: 'Final', dias: 15, kc: 0.8, umbrales: {} }], notas: '', fuentes: ['Definido por el usuario'] }); },
        clean (c) { const x = JSON.parse(JSON.stringify(c)); x.etapas.forEach(e => { e.umbrales = e.umbrales || {}; Object.keys(e.umbrales).forEach(k => { if (e.umbrales[k] === '' || e.umbrales[k] === null) delete e.umbrales[k]; }); }); return x; },
        onPage (m) {
            if (m.topic === 'crops') {
                this.crops = m.payload.list || [];
                if (m.payload.saved) { const c = this.crops.find(x => x.id === m.payload.saved); if (c) { this.filter = 'custom'; this.select(c); } }
                if (m.payload.message) this.res = { status: 'OK', label: 'Cultivos', message: m.payload.message };
            } else if (m.topic === 'crop_result') {
                this.res = { status: m.payload.ok ? (m.payload.sending ? 'SENDING' : 'OK') : 'REJECTED', label: 'Cultivo', message: m.payload.message };
                if (m.payload.ok && m.payload.sending) this.busy = true;
                if (!m.payload.ok) this.ed.err = m.payload.message;
                else if (this.ed.show) this.ed.show = false;
            }
        },
        th (i) { return this.sel ? this.calcUmbrales(this.sel, i, this.S.soil_cal, this.WX.et0_today_mm) : {}; },
        select (c) { this.sel = c; this.stageSel = 0; },
        newCrop () { this.ed = { show: true, c: this.blankCrop(), isNew: true, err: '', orig: '' }; this.ed.orig = JSON.stringify(this.ed.c); },
        edit () { const c = this.clean(this.sel); this.ed = { show: true, c, isNew: false, err: '', orig: JSON.stringify(c) }; },
        duplicate () {
            const c = this.clean(this.sel); delete c.id; c.tipo = 'custom'; c.nombre = this.sel.nombre + ' (copia)';
            c.gdd = c.gdd || { base_c: 10 }; c.temp_aire_crecimiento = c.temp_aire_crecimiento || { opt_min_c: null, opt_max_c: null, max_c: null };
            c.horarios = c.horarios || { win1: ['06:00', '09:00'], win2: ['18:00', '20:00'] };
            this.ed = { show: true, c, isNew: true, err: '', orig: '' };
        },
        addStage () { this.ed.c.etapas.push({ nombre: 'Nueva etapa', dias: 15, kc: 1.0, umbrales: {} }); },
        cancelEdit () { if (this.edDirty) this.ask('¿Descartar los cambios?', 'Se conservan los parámetros anteriores del cultivo.', () => { this.ed.show = false; }, 'DESCARTAR'); else this.ed.show = false; },
        saveEdit () {
            const c = this.clean(this.ed.c);
            this.ask('¿Confirmas aplicar esta configuración?', 'Se guardará el cultivo personalizado "' + c.nombre + '" (' + c.etapas.length + ' etapas). No cambia el cultivo activo del ESP32.',
                () => this.req('crop_save', { crop: c, is_new: this.ed.isNew }), 'GUARDAR');
        },
        del () { this.ask('¿Eliminar "' + this.sel.nombre + '"?', 'Se oculta de la lista; el historial que lo usó se conserva.', () => { this.req('crop_delete', { id: this.sel.id }); this.sel = null; }, 'ELIMINAR', true); },
        applyCrop () {
            const t = this.th(this.stageSel);
            const st = this.sel.etapas[this.stageSel];
            const txt = 'Cultivo: ' + this.sel.nombre + '\nEtapa: ' + st.nombre + ' (Kc ' + st.kc + ')\n' +
                (t.ok ? 'Humedad: emergencia ' + t.hum_critical + ' · mínima ' + t.hum_min + ' · óptima ' + t.hum_target + ' · reserva ' + t.hum_reserve + ' · máxima ' + t.hum_max + ' %VWC'
                    : 'Humedad: ' + t.estado + ' → el ESP32 conserva los umbrales actuales (' + this.C.hum_min + '/' + this.C.hum_target + '/' + this.C.hum_max + ').') +
                '\nDispositivo: ' + this.S.device + (this.S.simulated ? ' (SIMULADOR)' : ' (ESP32 real)');
            this.ask('¿Confirmas aplicar esta configuración?', txt, () => { this.busy = true; this.req('apply_crop', { crop_id: this.sel.id, stage_index: this.stageSel }); }, 'APLICAR');
        }
    },
    mounted () { this.rgMount(); this.req('crops_list', {}); },
    unmounted () { this.rgUnmount(); }
};
</script>
<style>@@ESTILOS@@</style>
