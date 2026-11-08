// UMBRALES DE HUMEDAD (%VWC) A PARTIR DEL CULTIVO, LA ETAPA Y EL SUELO CALIBRADO
// Método FAO-56: theta(d) = FC - d*(FC - WP), d = fracción agotada del agua disponible.
// Solo se calculan si FC y WP fueron MEDIDOS con el EC-5 en el suelo real.
// CAMA DE CULTIVO: con %VWC estándar (agua / volumen de suelo) subir 1 punto requiere
// área × profundidad × 1 % de agua. Ej.: 1 m² × 37.5 cm = 375 L de sustrato -> 3.75 L por punto.
function camaLpp(bed) {
    if (!bed || !(bed.area_m2 > 0) || !(bed.depth_cm > 0)) return null;
    return bed.area_m2 * bed.depth_cm / 10;
}
// Límites de riego derivados de la cama (se envían al ESP32 junto con el perfil del cultivo)
function paramsCama(bed) {
    const lpp = camaLpp(bed);
    if (!lpp) return {};
    const r1 = (v) => Math.round(v * 10) / 10, cl = (v, a, b) => Math.min(b, Math.max(a, v));
    // Dosis: ~2/3 de punto, pero que quepa en pump_max_s (90 s) con el caudal real medido (~1.3 L/min) -> máx 1.5 L
    const cyc = cl(r1(Math.min(lpp * 0.67, 1.5)), 0.5, 5);
    const ciclos = cl(Math.ceil((lpp * 2) / cyc), 1, 6);  // dosis necesarias para reponer ~2 puntos (histéresis)
    const ev = cl(r1(cyc * ciclos), cyc, 10);
    const day = cl(Math.round(lpp * 8), Math.ceil(ev), 50);   // 8 puntos al día: 30 L en la cama de 1 m² x 37.5 cm
    return { liters_per_cycle: cyc, max_cycles: ciclos, max_liters_event: ev, max_liters_daily: day,
        emergency_liters: cl(r1(Math.min(lpp * 0.5, cyc)), 0.1, 2),   // cabe en una corrida de bomba
        ia_gain_prior: cl(Math.round(100 / lpp) / 100, 0.1, 30),   // ganancia física promedio (%/L)
        min_response_pp: 0.5 };
}

function calcUmbrales(crop, stageIndex, soil, et0Today) {
    const st = (crop.etapas || [])[stageIndex] || {};
    // Cultivo personalizado con umbrales propios por etapa
    if (st.umbrales && ['hum_critical', 'hum_min', 'hum_target', 'hum_reserve', 'hum_max'].every(k => typeof st.umbrales[k] === 'number')) {
        return Object.assign({ ok: true, metodo: 'Definidos por el usuario para esta etapa', kc: st.kc || 1 }, st.umbrales);
    }
    if (!soil || typeof soil.fc_vwc !== 'number' || typeof soil.wp_vwc !== 'number' || soil.fc_vwc - soil.wp_vwc < 5) {
        return { ok: false, estado: 'PENDIENTE_DE_CALIBRACION', kc: st.kc || 1,
            motivo: 'Falta medir la capacidad de campo y el punto de marchitez del suelo con el EC-5 (Configuracion > Calibraciones)' };
    }
    const kc = typeof st.kc === 'number' ? st.kc : 1;
    const p0 = typeof crop.p_agotamiento === 'number' ? crop.p_agotamiento : 0.4;
    const et0 = (typeof et0Today === 'number' && et0Today > 0) ? et0Today : 5;
    const etc = kc * et0;
    const p = Math.min(0.8, Math.max(0.1, p0 + 0.04 * (5 - etc)));
    const FC = soil.fc_vwc, WP = soil.wp_vwc;
    const th = (dd) => Math.round((FC - dd * (FC - WP)) * 10) / 10;
    const u = {
        ok: true, kc, p_ajustado: Math.round(p * 1000) / 1000, etc_mm_dia: Math.round(etc * 100) / 100,
        hum_max: th(0), hum_reserve: th(Math.min(0.10, p / 4)), hum_target: th(p / 2), hum_min: th(p),
        hum_critical: th(Math.min(p + 0.20, 0.85)),
        metodo: 'FAO-56: p=' + p.toFixed(2) + ' (p tabla ' + p0 + ', ETc ' + etc.toFixed(1) + ' mm/d), FC ' + FC + ', WP ' + WP
    };
    // Mismas reglas que valida el ESP32
    if (!(u.hum_critical + 1 <= u.hum_min && u.hum_min + 1 <= u.hum_target && u.hum_target + 0.5 <= u.hum_reserve && u.hum_reserve <= u.hum_max)) {
        return { ok: false, estado: 'RANGO_INSUFICIENTE', kc,
            motivo: 'El rango entre capacidad de campo y marchitez es demasiado estrecho para separar los umbrales', calculado: u };
    }
    return u;
}
