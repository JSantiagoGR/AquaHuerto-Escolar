// Código común inyectado en data / computed / methods de cada página (Dashboard 2.0 no admite mixins)
//@@DATA
            snap: null, res: null, busy: false, pendingLabel: '',
            riegoPend: null, riegoUlt: null, extraDiario: null,
            dlg: { show: false, title: '', text: '', ok: 'CONFIRMAR', danger: false, fn: null },
            modeDlg: { show: false, mode: null },
//@@COMPUTED
        S () { return this.snap || {}; },
        lpp () { const b = (this.snap && this.snap.bed) || null; return (b && b.area_m2 > 0 && b.depth_cm > 0) ? b.area_m2 * b.depth_cm / 10 : null; },
        T () { return (this.snap && this.snap.telemetry) || {}; },
        ST () { return (this.snap && this.snap.state) || {}; },
        C () { return (this.snap && this.snap.config) || {}; },
        IA () { return (this.snap && this.snap.ia) || {}; },
        WX () { return (this.snap && this.snap.weather) || {}; },
        bal () {
            // Balance de agua de HOY (informativo, no decide riegos): ETc = Kc × ET0 (FAO-56); 1 mm sobre 1 m² = 1 L
            const b = (this.snap && this.snap.bed) || {}, area = b.area_m2 > 0 ? b.area_m2 : 1;
            const et0 = this.WX.et0_today_mm, kc = this.C.kc, w = this.ST.watering || {};
            const pierde = (typeof et0 === 'number' && typeof kc === 'number') ? kc * et0 * area : null;
            const lluvia = typeof this.WX.next24h_precip_mm === 'number' ? this.WX.next24h_precip_mm : null;
            return { et0, kc, area, pierde, puntos: (pierde !== null && this.lpp) ? pierde / this.lpp : null,
                regado: ((this.T.flow || {}).today_l || 0) + (w.active ? (w.delivered_l || 0) : 0),
                lluviaMm: lluvia, lluviaL: lluvia === null ? null : lluvia * area };
        },
        modeNow () { return this.ST.mode || null; },
        devOptions () { return ((this.snap && this.snap.devices) || []).map(d => ({ title: d.id + (d.simulated ? ' (SIMULADOR)' : ' (ESP32 real)') + (d.online ? '' : ' - sin conexión'), value: d.id })); },
        vwc () { const s = this.T.soil || {}; return s.valid ? s.vwc_pct : null; },
//@@METHODS
        rgMount () {
            if (this.msg) this.rgIn(this.msg);
            this._h = (m) => this.rgIn(m);
            if (this.$socket) this.$socket.on('msg-input:' + this.id, this._h);
        },
        rgUnmount () { if (this.$socket && this._h) this.$socket.off('msg-input:' + this.id, this._h); },
        rgIn (m) {
            if (!m) return;
            if (m.topic === 'snapshot') { this.snap = m.payload; if (this.onSnap) this.onSnap(m.payload); }
            else if (m.topic === 'cmd_result') {
                this.res = m.payload;
                const p = m.payload, fin = p.status !== 'SENDING' && p.status !== 'PENDING';
                if (fin) this.busy = false;
                // Riego pedido desde otro modo: ya se cambió a MANUAL -> ahora sí se manda el riego
                if (fin && p.cmd === 'SET_MODE' && this.riegoPend) {
                    const r = this.riegoPend; this.riegoPend = null;
                    if (p.status === 'OK') { this.riegoUlt = r; this.cmd(r.name, r.extra, r.label); }
                }
                // Rechazado por el máximo diario: se ofrece el botón de riego extra
                if (fin && (p.cmd === 'START_MANUAL' || p.cmd === 'START_TO_TARGET') && p.status !== 'OK' &&
                    /maximo diario/i.test(p.message || '') && this.riegoUlt) this.extraDiario = this.riegoUlt;
                if (this.onResult) this.onResult(p);
            } else if (this.onPage) this.onPage(m);
        },
        cmd (name, extra, label) {
            this.busy = true; this.pendingLabel = label || name;
            this.res = { status: 'SENDING', label: label || name, message: 'Enviando...' };
            this.send({ topic: 'cmd', payload: Object.assign({ cmd: name, _ui: { label: label || name } }, extra || {}) });
        },
        riego (name, extra, label) {
            // El riego manual solo se hace en MANUAL: desde otro modo primero se cambia (y se recuerda el anterior)
            const r = { name, extra: extra || {}, label };
            this.extraDiario = null;
            if (this.modeNow && this.modeNow !== 'MANUAL') {
                this.riegoPend = r;
                this.cmd('SET_MODE', { mode: 'MANUAL', from_mode: this.modeNow }, 'Cambio a MANUAL para regar');
            } else { this.riegoUlt = r; this.cmd(name, r.extra, label); }
        },
        avisoModo () {
            return (this.modeNow && this.modeNow !== 'MANUAL') ? '\n\nEstás en modo ' + this.modeName(this.modeNow) +
                ': el riego manual solo se hace en MANUAL, así que el sistema cambiará a MANUAL. Al terminar te preguntará si regresas a ' +
                this.modeName(this.modeNow) + ' (si no, se queda en MANUAL y no regará solo).' : '';
        },
        permitirExtra () {
            const r = this.extraDiario; if (!r) return;
            this.ask('¿Permitir un riego extra hoy?', 'Ya se alcanzó el máximo diario (' + this.n(this.C.max_liters_daily, this.C.max_liters_daily % 1 ? 1 : 0) + ' L). ' +
                'Este riego pasará el límite SOLO esta vez; el siguiente vuelve a pedir autorización. Las demás protecciones (tiempo de bomba, sin flujo, máximo por riego) siguen activas.',
                () => { this.extraDiario = null; this.riegoUlt = r; this.cmd(r.name, Object.assign({}, r.extra, { over_daily: true }), r.label + ' (extra autorizado)'); },
                'PERMITIR RIEGO EXTRA', true);
        },
        req (type, args) { this.send({ topic: 'req', payload: Object.assign({ type }, args || {}) }); },
        ask (title, text, fn, ok, danger) { this.dlg = { show: true, title, text, ok: ok || 'CONFIRMAR', danger: !!danger, fn }; },
        dlgOk () { const f = this.dlg.fn; this.dlg.show = false; if (f) f(); },
        pickMode (m) { this.modeDlg = { show: true, mode: m }; },
        confirmMode () {
            const m = this.modeDlg.mode; this.modeDlg.show = false;
            this.cmd('SET_MODE', { mode: m }, 'Cambio a modo ' + this.modeName(m));
        },
        selectDevice (d) { this.req('select_device', { device: d }); },
        n (v, d) { return (typeof v === 'number' && isFinite(v)) ? v.toFixed(d === undefined ? 1 : d) : '—'; },
        dt (ts) { if (!ts) return '—'; return new Date(ts * 1000).toLocaleString('es-MX', { timeZone: 'America/Chihuahua', dateStyle: 'short', timeStyle: 'short' }); },
        hm (ts) { if (!ts) return '—'; return new Date(ts * 1000).toLocaleTimeString('es-MX', { timeZone: 'America/Chihuahua', hour: '2-digit', minute: '2-digit' }); },
        ago (ts) { if (!ts) return 'nunca'; const s = Math.max(0, Math.floor(Date.now() / 1000) - ts); return s < 60 ? 'hace ' + s + ' s' : (s < 3600 ? 'hace ' + Math.floor(s / 60) + ' min' : 'hace ' + Math.floor(s / 3600) + ' h'); },
        modeName (m) { return ({ MANUAL: 'MANUAL', AUTOMATICO: 'AUTOMÁTICO', IA: 'IA' })[m] || m || '—'; },
        resColor (s) { return { OK: 'success', SENDING: 'info', PENDING: 'info', REJECTED: 'error', INVALID: 'error', TIMEOUT: 'warning', DUPLICATE: 'warning', STALE: 'warning', RETAINED: 'warning', UNAUTHORIZED: 'error' }[s] || 'info'; },
        sevColor (s) { return s === 'CRITICAL' ? 'error' : (s === 'WARNING' ? 'warning' : 'info'); },
        decColor (code) { if (!code) return 'grey'; if (/START|CONTINUE/.test(code)) return 'primary'; if (/FAULT|FAILED|INVALID|LOCKED|TANK/.test(code)) return 'error'; if (/OK|NOT_NEEDED|REACHED/.test(code)) return 'success'; return 'warning'; },
