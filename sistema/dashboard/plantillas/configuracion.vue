<template>
<div class="rg">
@@CABECERA@@
<div class="rg-grid2">
  <div class="rg-box">
    <div class="rg-sec" style="margin-top:0"><v-icon>mdi-devices</v-icon>Dispositivos (datos reales vs simulados)</div>
    <table class="rg-table"><tr><th>Dispositivo</th><th>Tipo de datos</th><th>Conexión</th><th>Último dato</th></tr>
      <tr v-for="d in (S.devices || [])" :key="d.id"><td><b>{{ d.id }}</b></td><td :class="d.simulated ? 'rg-warn' : 'rg-ok'">{{ d.simulated ? 'SIMULADOS' : 'REALES (ESP32)' }}</td><td>{{ d.online ? 'en línea' : 'sin conexión' }}</td><td>{{ ago(d.last_seen) }}</td></tr></table>
    <div class="rg-muted mt-1">Cultivo activo: <b>{{ ST.crop_name }}</b> / {{ ST.stage }} (perfil v{{ ST.profile_version }}) · Modo activo: <b>{{ modeName(modeNow) }}</b> · Perfil de instalación {{ ST.install_profile }} ({{ ST.install_profile === 'B' ? 'definitivo' : 'pruebas' }})</div>
  </div>
  <div class="rg-box">
    <div class="rg-sec" style="margin-top:0"><v-icon>mdi-chip</v-icon>Estado del ESP32</div>
    <div class="rg-muted">Firmware {{ ST.fw || D.fw }} · ESP-IDF {{ D.idf }} · MAC {{ D.mac }}</div>
    <div class="rg-muted">Memoria libre {{ ST.free_heap }} B (mín {{ D.min_free_heap }}) · arranques {{ D.boot_count }} · motivo de reinicio {{ D.reset_reason }}</div>
    <div class="rg-muted">Salidas de potencia: <b>{{ ST.power_outputs ? 'HABILITADAS' : 'DESHABILITADAS (versión segura)' }}</b> — solo se habilitan por consola USB (POWER ON CONFIRMAR) tras verificar la etapa de potencia.</div>
    <div class="rg-row mt-2"><v-btn size="small" variant="tonal" prepend-icon="mdi-stethoscope" :disabled="busy" @click="cmd('NET_DIAG', {}, 'Diagnóstico')">DIAGNÓSTICO</v-btn>
      <v-btn size="small" variant="tonal" prepend-icon="mdi-refresh" :disabled="busy" @click="cmd('GET_STATUS', {}, 'Estado completo')">PEDIR ESTADO</v-btn>
      <v-btn size="small" variant="tonal" prepend-icon="mdi-cog-refresh" :disabled="busy" @click="cmd('GET_CONFIG', {}, 'Configuración')">PEDIR CONFIGURACIÓN</v-btn></div>
  </div>
  <div class="rg-box">
    <div class="rg-sec" style="margin-top:0"><v-icon>mdi-wifi</v-icon>Redes Wi-Fi del ESP32</div>
    <div class="rg-muted">Conectado: {{ W.connected ? 'SÍ' : 'NO' }} · red {{ W.network }} ({{ W.ssid }}) · IP {{ W.ip }} · {{ W.rssi }} dBm · canal {{ W.channel }} · último motivo {{ W.last_reason }} {{ W.last_reason_text }}</div>
    <table class="rg-table mt-1"><tr><th>Nombre</th><th>SSID</th><th>Habilitada</th><th>Preferida</th></tr>
      <tr v-for="s in (W.saved_networks || [])" :key="s.name"><td>{{ s.name }}</td><td>{{ s.ssid || '—' }}</td><td>{{ s.enabled ? 'sí' : 'no' }}</td><td>{{ s.preferred ? '★' : '' }}</td></tr></table>
    <div class="rg-muted mt-1">Por seguridad las contraseñas Wi-Fi se cambian solo por USB (configs\CONFIGURAR_WIFI_ESP32.bat o consola: WIFI casa|tec|huerto). Nunca se muestran ni se publican. El Wi-Fi del Tec puede ser empresarial (802.1X) o aislar dispositivos: no está verificado.</div>
  </div>
  <div class="rg-box">
    <div class="rg-sec" style="margin-top:0"><v-icon>mdi-access-point-network</v-icon>Broker MQTT</div>
    <div class="rg-muted">Actual: <b>{{ M.broker }}</b> · cliente {{ M.client_id }} · conexiones {{ M.connects }} · último cambio {{ M.broker_change }} · topic {{ D.base_topic }}</div>
    <div class="rg-row mt-2"><v-text-field v-model="broker.uri" label="Nuevo broker (mqtt://IP:1883)" density="compact" variant="outlined" hide-details></v-text-field></div>
    <div class="rg-row mt-2"><v-text-field v-model="broker.user" label="Usuario (opcional)" density="compact" variant="outlined" hide-details></v-text-field>
      <v-text-field v-model="broker.pass" label="Contraseña (opcional)" type="password" density="compact" variant="outlined" hide-details autocomplete="new-password"></v-text-field></div>
    <v-btn class="mt-2" size="small" color="primary" variant="tonal" :disabled="busy || !/^mqtts?:\/\/.+/.test(broker.uri)" @click="setBroker">CAMBIAR BROKER</v-btn>
    <div class="rg-muted mt-1">Si el ESP32 no logra conectarse al nuevo broker en 90 s, vuelve solo al anterior.</div>
  </div>
</div>

<div class="rg-sec"><v-icon>mdi-tune-vertical</v-icon>Calibraciones y parámetros de seguridad (borrador)</div>
<div v-if="dirty" class="rg-draft">Cambios SIN GUARDAR</div>
<div class="rg-grid2">
  <div class="rg-box"><div class="rg-muted mb-1">Caudalímetro YF-S201 (provisional 450 p/L: contrástalo con un recipiente)</div>
    <v-text-field v-model.number="draft.pulses_per_liter" label="Pulsos por litro" type="number" density="compact" variant="outlined" :hint="'activo: ' + C.pulses_per_liter" persistent-hint></v-text-field>
    <div class="rg-muted mt-2 mb-1">Tinaco (distancia sensor → agua)</div>
    <div class="rg-row"><v-text-field v-model.number="draft.tank_empty_cm" label="Vacío (cm)" type="number" density="compact" variant="outlined" hide-details></v-text-field>
      <v-text-field v-model.number="draft.tank_full_cm" label="Lleno (cm)" type="number" density="compact" variant="outlined" hide-details></v-text-field></div>
    <v-text-field class="mt-2" v-model.number="draft.tank_min_pct" label="Nivel mínimo para regar (%)" type="number" density="compact" variant="outlined"></v-text-field></div>
  <div class="rg-box"><div class="rg-muted mb-1">EC-5 (%VWC = pendiente · mV + ordenada)</div>
    <v-text-field v-model.number="draft.ec5_slope" label="Pendiente (%/mV)" type="number" step="0.0001" density="compact" variant="outlined" :hint="'activo: ' + C.ec5_slope" persistent-hint></v-text-field>
    <v-text-field class="mt-2" v-model.number="draft.ec5_offset" label="Ordenada (%)" type="number" step="0.01" density="compact" variant="outlined" :hint="'activo: ' + C.ec5_offset" persistent-hint></v-text-field>
    <label class="rg-devlbl mt-2">Escala de la recta <select class="rg-devsel" v-model.number="draft.ec5_scale"><option :value="1">agua/(tierra+agua) de la Act. 2.2 → se convierte a agua/suelo</option><option :value="0">ya es %VWC estándar (agua/suelo)</option></select></label>
    <div class="rg-muted">La Act. 2.2 mezcló 600 mL de tierra seca con 0/105/257/490 mL de agua y calculó agua/(tierra+agua). El %VWC estándar es agua/suelo: theta = s/(1−s). Ej.: 630 mV → recta 27.4 → 37.7 %VWC.</div>
    <div class="rg-muted mt-2">Versión de datos actual: <b>{{ C.data_version }}</b>. Si cambias la calibración o el suelo, crea una versión nueva para no mezclar datos (la IA reinicia su modelo; el historial se conserva).</div>
    <div class="rg-row mt-1"><v-text-field v-model="dvDesc" label="Descripción de la nueva versión" density="compact" variant="outlined" hide-details></v-text-field>
      <v-btn size="small" variant="tonal" :disabled="!dvDesc" @click="newDataVersion">NUEVA VERSIÓN</v-btn></div></div>
  <div class="rg-box"><div class="rg-muted mb-1">Seguridad de bomba y flujo</div>
    <v-text-field v-for="f in safe" :key="f.k" v-model.number="draft[f.k]" :label="f.l" type="number" density="compact" variant="outlined" :hint="'activo: ' + C[f.k]" persistent-hint class="mb-1"></v-text-field></div>
  <div class="rg-box"><div class="rg-muted mb-1">Hora, zona horaria y ubicación</div>
    <div class="rg-muted">Hora del ESP32: {{ ST.local_time }} ({{ ST.time_valid ? 'NTP sincronizada' : 'SIN sincronizar' }})</div>
    <v-text-field v-model="draft.tz" label="Zona horaria POSIX (Chihuahua: CST6)" density="compact" variant="outlined" class="mt-1"></v-text-field>
    <div class="rg-row"><v-text-field v-model.number="loc.lat" label="Latitud" type="number" step="0.0001" density="compact" variant="outlined" hide-details></v-text-field>
      <v-text-field v-model.number="loc.lon" label="Longitud" type="number" step="0.0001" density="compact" variant="outlined" hide-details></v-text-field></div>
    <v-text-field class="mt-2" v-model="loc.label" label="Nombre del lugar" density="compact" variant="outlined" hide-details></v-text-field>
    <v-btn class="mt-2" size="small" variant="tonal" @click="saveLocation">GUARDAR UBICACIÓN</v-btn>
    <div class="rg-muted">Actual: {{ (S.location || {}).lat }}, {{ (S.location || {}).lon }} — {{ (S.location || {}).label }}</div></div>
</div>
<div class="rg-row mt-2"><v-btn color="primary" prepend-icon="mdi-content-save" :disabled="!dirty || busy" @click="save">GUARDAR</v-btn><v-btn variant="tonal" :disabled="!dirty" @click="draft = Object.assign({}, base)">CANCELAR</v-btn></div>

<div class="rg-grid2 mt-3">
  <div class="rg-box"><div class="rg-sec" style="margin-top:0"><v-icon>mdi-sprout-outline</v-icon>Cama de cultivo (servidor)</div>
    <div class="rg-muted">Con humedad volumétrica estándar, subir 1 punto de %VWC requiere área × profundidad × 1 % de agua. Se usa en los tres modos: litros por dosis y por evento, ganancia inicial de la IA y estimaciones del dashboard.</div>
    <div class="rg-row mt-1"><v-text-field v-model.number="bed.area_m2" label="Área (m²)" type="number" step="0.05" density="compact" variant="outlined" hide-details></v-text-field>
      <v-text-field v-model.number="bed.depth_cm" label="Profundidad del sustrato (cm)" type="number" density="compact" variant="outlined" hide-details></v-text-field></div>
    <label class="rg-devlbl mt-2">Drenaje del fondo <select class="rg-devsel" v-model="bed.drainage"><option value="libre">Libre (malla geotextil o lona perforada)</option><option value="restringido">Restringido (lona sin perforar)</option></select></label>
    <v-text-field class="mt-2" v-model="bed.mix" label="Mezcla" density="compact" variant="outlined" hide-details></v-text-field>
    <div v-if="bedLpp" class="mt-1">Sustrato <b>{{ n(bedLpp * 100, 0) }} L</b> · 1 punto de %VWC ≈ <b>{{ n(bedLpp, 2) }} L</b>{{ S.soil_cal ? ' · agua útil (FC−WP) ≈ ' + n((S.soil_cal.fc_vwc - S.soil_cal.wp_vwc) * bedLpp, 0) + ' L' : '' }}</div>
    <div v-if="bed.drainage === 'restringido'" class="rg-warn">Sin drenaje el fondo se encharca: la capacidad de campo estimada no aplica y el frijol es sensible a la asfixia de raíces.</div>
    <v-btn class="mt-2" size="small" variant="tonal" @click="saveBed">GUARDAR CAMA</v-btn>
    <div class="rg-muted">{{ S.bed ? 'Actual: ' + S.bed.area_m2 + ' m² × ' + S.bed.depth_cm + ' cm, drenaje ' + S.bed.drainage : 'Sin datos de la cama' }}</div></div>
  <div class="rg-box"><div class="rg-sec" style="margin-top:0"><v-icon>mdi-layers-triple</v-icon>Calibración del suelo (servidor)</div>
    <div class="rg-muted">Capacidad de campo: satura el suelo, deja drenar 24–48 h sin evaporación y registra la lectura del EC-5. Marchitez: no se inventa; usa una medición o un valor de laboratorio para tu tipo de suelo.</div>
    <div class="rg-row mt-1"><v-text-field v-model.number="soil.fc_vwc" label="Capacidad de campo (%VWC)" type="number" density="compact" variant="outlined" hide-details></v-text-field>
      <v-text-field v-model.number="soil.wp_vwc" label="Punto de marchitez (%VWC)" type="number" density="compact" variant="outlined" hide-details></v-text-field></div>
    <v-text-field class="mt-2" v-model="soil.method" label="Método / fuente" density="compact" variant="outlined" hide-details></v-text-field>
    <v-btn class="mt-2" size="small" variant="tonal" @click="saveSoil">GUARDAR CALIBRACIÓN DEL SUELO</v-btn>
    <div class="rg-muted">{{ S.soil_cal ? 'Actual: FC ' + S.soil_cal.fc_vwc + ' / WP ' + S.soil_cal.wp_vwc + ' (' + dt(S.soil_cal.ts) + ')' : 'PENDIENTE DE CALIBRACIÓN' }}</div></div>
  <div class="rg-box"><div class="rg-sec" style="margin-top:0"><v-icon>mdi-backup-restore</v-icon>Copias de seguridad</div>
    <div class="rg-muted">Base de datos: {{ S.db_ok ? 'OK' : 'CON PROBLEMAS' }} · {{ dbs.readings || 0 }} lecturas, {{ dbs.events || 0 }} riegos, {{ dbs.alerts || 0 }} alertas, {{ dbs.predictions || 0 }} predicciones · desde {{ dt(dbs.first_ts) }}</div>
    <v-btn class="mt-1" size="small" color="primary" variant="tonal" prepend-icon="mdi-content-save-all" @click="req('backup_now')">RESPALDAR AHORA</v-btn>
    <div class="rg-scroll mt-1" style="max-height:160px"><table class="rg-table"><tr><th>Archivo</th><th>KB</th><th>Fecha</th></tr>
      <tr v-for="b in (S.backups || [])" :key="b.file"><td>{{ b.file }}</td><td>{{ b.kb }}</td><td>{{ dt(b.ts) }}</td></tr></table></div>
    <div class="rg-muted">Respaldo automático diario a las 03:00. Carpeta: backups\db (no se borran solos).</div></div>
  <div class="rg-box"><div class="rg-sec" style="margin-top:0"><v-icon>mdi-lan</v-icon>Datos de conexión</div>
    <div class="rg-muted">Entorno: <b>{{ S.env }}</b> · Dashboard: http://&lt;IP de la PC&gt;:1880/dashboard · Editor Node-RED: http://localhost:1880 (protegido) · Broker: puerto 1883 (solo red local, usuario y contraseña).</div>
    <div class="rg-muted">Topics: {{ D.base_topic }}/(telemetry, state, config, decision, event, alarm, ack, ia, weather, diag, status) y {{ D.base_topic }}/command.</div></div>
</div>
<div v-if="S.simulated" class="rg-box mt-3" style="border:2px dashed #f9a825">
  <div class="rg-sec" style="margin-top:0"><v-icon>mdi-flask</v-icon>Controles del SIMULADOR (solo para {{ S.device }}: nunca llegan al ESP32 real)</div>
  <div class="rg-muted">Velocidad actual x{{ ST.sim_speed }} · humedad "real" simulada {{ (ST.sim_world || {}).true_vwc }} %VWC · tinaco {{ (ST.sim_world || {}).tank_l }} L</div>
  <div class="rg-row mt-1">
    <v-btn v-for="sp in [1, 60, 600]" :key="sp" size="small" variant="tonal" @click="sim('speed', sp)">x{{ sp }}</v-btn>
    <v-btn size="small" variant="tonal" prepend-icon="mdi-weather-pouring" @click="sim('rain', 6)">LLUVIA</v-btn>
    <v-btn size="small" variant="tonal" prepend-icon="mdi-sprinkler" @click="sim('external', 5)">RIEGO EXTERNO</v-btn>
    <v-btn size="small" variant="tonal" @click="sim('forecast_rain', 1)">PRONÓSTICO LLUVIA</v-btn>
    <v-btn size="small" variant="tonal" @click="sim('forecast_rain', 0)">SIN PRONÓSTICO</v-btn>
  </div>
  <div class="rg-row mt-1">
    <v-btn v-for="f in ['soil','env','tank','flow']" :key="f" size="small" :color="((ST.sim_world || {}).fails || {})[f] ? 'error' : ''" variant="tonal" @click="sim('fail_' + f, !(((ST.sim_world || {}).fails || {})[f]))">FALLA {{ f.toUpperCase() }}</v-btn>
    <v-btn size="small" variant="tonal" @click="sim('mqtt_drop', 45)">PERDER MQTT 45 s</v-btn>
    <v-btn size="small" variant="tonal" @click="sim('tank', 10)">TINACO 10 %</v-btn>
    <v-btn size="small" variant="tonal" @click="sim('tank', 90)">TINACO 90 %</v-btn>
    <v-btn size="small" variant="tonal" @click="sim('soil', 15)">SUELO 15 %</v-btn>
    <v-btn size="small" variant="tonal" @click="sim('hour', '06:30')">HORA 06:30</v-btn>
    <v-btn size="small" variant="tonal" @click="sim('hour', '13:00')">HORA 13:00</v-btn>
  </div>
</div>
@@DIALOGOS@@
</div>
</template>
<script>
export default {
    mixins: [@@COMUNJS@@],
    data () {
        return ({ KEYS: ['pulses_per_liter', 'tank_empty_cm', 'tank_full_cm', 'tank_min_pct', 'ec5_slope', 'ec5_offset', 'ec5_scale', 'pump_max_s', 'no_flow_s', 'flow_max_lpm', 'valve_lead_ms', 'valve_lag_ms', 'idle_flow_pulses', 'tz'],  draft: {}, base: {}, broker: { uri: '', user: '', pass: '' }, loc: { lat: null, lon: null, label: '' }, soil: { fc_vwc: null, wp_vwc: null, method: '' }, bed: { area_m2: null, depth_cm: null, drainage: 'libre', mix: '' }, dvDesc: '',
            safe: [{ k: 'pump_max_s', l: 'Tiempo máximo de bomba (s)' }, { k: 'no_flow_s', l: 'Sin pulsos para cortar (s)' }, { k: 'flow_max_lpm', l: 'Caudal máximo creíble (L/min)' },
                { k: 'valve_lead_ms', l: 'Válvula antes de bomba (ms)' }, { k: 'valve_lag_ms', l: 'Bomba antes de cerrar válvula (ms)' }, { k: 'idle_flow_pulses', l: 'Pulsos con todo apagado (alarma)' }] });
    },
    computed: {
        D () { return this.S.diag || {}; }, W () { return (this.S.diag || {}).wifi || {}; }, M () { return (this.S.diag || {}).mqtt || {}; },
        dbs () { return this.S.db_stats || {}; },
        bedLpp () { return (this.bed.area_m2 > 0 && this.bed.depth_cm > 0) ? this.bed.area_m2 * this.bed.depth_cm / 10 : null; },
        dirty () { return this.KEYS.some(k => String(this.draft[k]) !== String(this.base[k])); }
    },
    methods: {
        load (force) {
            if (!this.C || this.C.pulses_per_liter === undefined) return;
            const b = {}; this.KEYS.forEach(k => { b[k] = this.C[k]; });
            const was = this.dirty; this.base = b; if (force || !was) this.draft = Object.assign({}, b);
            if (this.loc.lat === null && this.S.location) this.loc = Object.assign({}, this.S.location);
            if (this.bed.area_m2 === null && this.S.bed) this.bed = Object.assign({}, this.S.bed);
            if (this.soil.fc_vwc === null && this.S.soil_cal) this.soil = { fc_vwc: this.S.soil_cal.fc_vwc, wp_vwc: this.S.soil_cal.wp_vwc, method: this.S.soil_cal.method || '' };
        },
        onSnap () { this.load(false); },
        save () {
            const params = {}; this.KEYS.forEach(k => { if (String(this.draft[k]) !== String(this.base[k])) params[k] = this.draft[k]; });
            this.ask('¿Confirmas aplicar esta configuración?', Object.keys(params).map(k => k + ': ' + this.base[k] + ' → ' + params[k]).join('\n'),
                () => this.cmd('APPLY_CONFIG', { version: (this.S.profile_version || 0) + 1, params }, 'Calibraciones y seguridad'), 'APLICAR');
        },
        setBroker () {
            const b = Object.assign({ uri: this.broker.uri }, this.broker.user ? { user: this.broker.user, pass: this.broker.pass } : {});
            this.ask('¿Cambiar el broker del ESP32 a ' + b.uri + '?', 'El dashboard dejará de recibir datos de este ESP32 si el broker nuevo no es este servidor. Si no conecta en 90 s, vuelve al anterior.',
                () => { this.cmd('SET_BROKER', b, 'Cambio de broker'); this.broker.pass = ''; }, 'CAMBIAR', true);
        },
        saveLocation () {
            this.ask('¿Confirmas aplicar esta configuración?', 'Ubicación: ' + this.loc.lat + ', ' + this.loc.lon + ' (' + this.loc.label + ')\nSe usa en Open-Meteo del servidor y del ESP32.', () => {
                this.req('location_save', this.loc);
                this.cmd('APPLY_CONFIG', { version: (this.S.profile_version || 0) + 1, params: { lat: this.loc.lat, lon: this.loc.lon } }, 'Ubicación del huerto');
            }, 'APLICAR');
        },
        saveBed () {
            this.ask('¿Guardar la cama de cultivo?', this.bed.area_m2 + ' m² × ' + this.bed.depth_cm + ' cm = ' + this.n(this.bedLpp * 100, 0) + ' L de sustrato; 1 punto de %VWC ≈ ' + this.n(this.bedLpp, 2) + ' L.\nDespués vuelve a aplicar el cultivo para enviar los litros y la ganancia de la IA al ESP32.',
                () => this.req('bed_save', this.bed), 'GUARDAR');
        },
        saveSoil () { this.ask('¿Guardar la calibración del suelo?', 'FC ' + this.soil.fc_vwc + ' / WP ' + this.soil.wp_vwc + ' %VWC. Los perfiles de cultivo usarán estos valores para calcular umbrales.', () => this.req('soil_cal_save', Object.assign({ data_version: this.C.data_version }, this.soil)), 'GUARDAR'); },
        newDataVersion () { this.ask('¿Crear una nueva versión de datos?', this.dvDesc + '\nLa IA del ESP32 reiniciará su modelo (el historial se conserva y queda separado por versión).', () => this.req('data_version_new', { description: this.dvDesc }), 'CREAR', true); },
        sim (action, value) { this.cmd('SIM_CONTROL', { action, value }, 'Simulador: ' + action); },
        onPage (m) { if (m.topic === 'config_result') this.res = { status: m.payload.ok ? 'OK' : 'REJECTED', label: 'Configuración del servidor', message: m.payload.message }; },
        onResult (r) { if (r.cmd === 'APPLY_CONFIG' && r.status === 'OK') setTimeout(() => this.load(true), 1500); }
    },
    mounted () { this.rgMount(); this.load(true); this.req('db_stats'); },
    unmounted () { this.rgUnmount(); }
};
</script>
<style>@@ESTILOS@@</style>
