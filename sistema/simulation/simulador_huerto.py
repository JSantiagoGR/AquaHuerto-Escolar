"""SIMULADOR DEL HUERTO - dispositivo virtual "sim_01" (MODO DEMOSTRACIÓN — DATOS SIMULADOS)

- Usa la MISMA lógica en C del firmware (riego_core.dll): máquina de estados, límites,
  validación de configuración e IA (RLS). Lo simulado es solo el "mundo": suelo, clima,
  tinaco, caudal, lluvia, riego externo, fallos de sensores y de MQTT.
- Publica con el MISMO protocolo y formato que el ESP32 en huerto/casa/sim_01/...
  con usuario MQTT propio (simulador_casa). El broker (ACL) le impide tocar los topics
  del ESP32 real: sus comandos nunca pueden activar hardware.
- Todos los mensajes llevan "simulated": true.

Uso:
  python simulador_huerto.py                    # en vivo (velocidad x1)
  python simulador_huerto.py --preentrenar 14   # simula 14 días sin MQTT para entrenar la IA y sale
  python simulador_huerto.py --velocidad 60     # 1 s real = 1 min simulado
Control en vivo (topic huerto/casa/sim_01/command, cmd SIM_CONTROL): velocidad, lluvia,
riego externo, fallas de sensores, tinaco, caudal, perder MQTT, secado.
"""
import argparse
import base64
import json
import math
import os
import queue
import random
import sys
import threading
import time

import ctypes as C
import paho.mqtt.client as mqtt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from riego_core import (Core, Inputs, Env, Plan, EV_STATE, EV_WATER_START, EV_WATER_END, EV_EVENT_END,  # noqa: E402
                        EV_DECISION, EV_ALARM_SET, EV_ALARM_CLEAR, EV_COUNTERS)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STATE_FILE = os.path.join(HERE, "estado_simulador.json")
TZ_OFF = -6 * 3600                       # Chihuahua (UTC-6, sin horario de verano)
DEVICE = "sim_01"
FW = "simulador-2.0.0 (logica del firmware riego-2.0.0)"


def read_env(path):
    vals = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                vals[k.strip()] = v.strip()
    return vals


class World:
    """Física simplificada (NO es una medición): suelo, clima y tinaco."""

    def __init__(self, rnd):
        self.r = rnd
        self.vwc = 27.0              # Humedad "verdadera"
        self.true_gain = 3.0         # pp por litro (desconocido para la IA: lo aprende)
        self.tank_l = 170.0          # Tinaco de 200 L
        self.tank_cap = 200.0
        self.pending = []            # Agua que se infiltra poco a poco [(pp, minutos restantes)]
        self.rain_now = 0.0          # mm/h simulados
        self.t_mean, self.t_amp, self.rh_mean = 22.0, 8.0, 40.0
        self.flow_lpm = 4.0
        self.dry_scale = 1.0
        self.fail = {"soil": False, "env": False, "tank": False, "flow": False}

    def weather(self, local_h):
        t = self.t_mean + self.t_amp * math.sin(2 * math.pi * (local_h - 9) / 24)
        rh = max(10.0, min(95.0, self.rh_mean - 1.6 * (t - self.t_mean) + (25 if self.rain_now > 0 else 0)))
        return t, rh

    def step(self, dt_h, local_h, kc):
        t, rh = self.weather(local_h)
        es = 0.6108 * math.exp(17.27 * t / (t + 237.3))
        vpd = es * (1 - rh / 100)
        rate = self.dry_scale * (0.03 + 0.09 * vpd * kc + 0.004 * (self.vwc - 20))
        if self.rain_now <= 0:
            self.vwc -= max(0.0, rate) * dt_h
        for i, (pp, mins) in enumerate(self.pending):
            take = pp * min(1.0, dt_h * 60 / max(mins, 1e-6))
            self.vwc += take
            self.pending[i] = (pp - take, max(0.0, mins - dt_h * 60))
        self.pending = [x for x in self.pending if x[0] > 1e-4]
        self.vwc = max(3.0, min(50.0, self.vwc))
        return t, rh, vpd

    def add_water(self, liters):
        gain = max(0.3, self.true_gain - 0.06 * (self.vwc - 25)) * liters
        self.pending.append((gain + self.r.gauss(0, 0.15), 12.0))   # se infiltra en ~12 min
        self.tank_l = max(0.0, self.tank_l - liters)

    def external(self, pp):
        self.pending.append((pp, 20.0))


class SimDevice:
    def __init__(self, args):
        self.a = args
        self.rnd = random.Random(42)
        self.core = Core()
        self.w = World(self.rnd)
        self.speed = float(args.velocidad)
        self.t0_real = time.time()
        self.sim_epoch = time.time()
        self.virt_ms = 1000
        self.pulses = 0
        self.pulse_acc = 0.0
        self.soil_seq = 0
        self.soil_last_v = None
        self.soil_due = 0.0
        self.soil_next_ms = 0
        self.telem_seq = 0
        self.boot = 1
        self.event_seq = 0
        self.event_id = ""
        self.pred_dv = float("nan")
        self.pend = None
        self.anchor = None
        self.last_water_end = None
        self.rise_ref = None
        self.rise_ref_t = 0
        self.rise_pending = 0
        self.rise_last = -1e12
        self.ids = []
        self.connected = False
        self.mqtt_drop_until = 0
        self.q = queue.Queue()
        self.dec_last = None
        self.last_pub = {}
        self.plan = Plan()
        self.inp = Inputs()
        self.client = None
        self.state_dirty = self.dec_dirty = self.ia_dirty = False
        self.tank_cfg = {"tank_empty_cm": 110, "tank_full_cm": 20}
        self.load_state()
        # Tinaco simulado calibrado (el real NO lo está)
        ok, m = self.core.apply(self.tank_cfg, remote_only=False)
        self.build_inputs()
        self.core.L.rc_step(self.core.h, C.byref(self.inp))
        self.core.events()

    # ---------------------------------------------------------------- estado
    def load_state(self):
        if not os.path.exists(STATE_FILE):
            return
        try:
            st = json.load(open(STATE_FILE, encoding="utf-8"))
            ok, m = self.core.apply(st.get("config", {}), st.get("profile_version"), remote_only=False)
            if st.get("ia"):
                self.core.ia_import(base64.b64decode(st["ia"]))
            self.core.L.rc_set_counters(self.core.h, float(st.get("daily_ml", 0)), float(st.get("total_ml", 0)),
                                        int(st.get("day_key", 0)))
            self.event_seq = st.get("event_seq", 0)
            self.boot = st.get("boot", 0) + 1
            self.w.vwc = st.get("vwc", self.w.vwc)
            self.w.tank_l = st.get("tank_l", self.w.tank_l)
        except Exception as e:  # noqa: BLE001
            print("Estado previo ilegible, se inicia de cero:", e)

    def save_state(self):
        cfg = self.core.config()
        keep = {k: v for k, v in cfg.items() if k not in ("mode", "power_enabled", "auto_saved", "profile_version")}
        st = self.core.state()
        json.dump({"config": keep, "profile_version": cfg.get("profile_version"), "ia": base64.b64encode(self.core.ia_export()).decode(),
                   "daily_ml": st.daily_ml, "total_ml": st.total_ml, "day_key": self.day_key(), "event_seq": self.event_seq,
                   "boot": self.boot, "vwc": self.w.vwc, "tank_l": self.w.tank_l, "saved": time.time()},
                  open(STATE_FILE, "w", encoding="utf-8"), indent=1)

    # ------------------------------------------------------------ utilidades
    def local(self):
        t = time.gmtime(self.sim_epoch + TZ_OFF)
        return t.tm_hour * 60 + t.tm_min, t.tm_hour + t.tm_min / 60.0

    def day_key(self):
        t = time.gmtime(self.sim_epoch + TZ_OFF)
        return t.tm_year * 1000 + t.tm_yday

    def ts(self):
        return int(self.sim_epoch)

    def base(self, d):
        d.update({"ts": self.ts(), "uptime_s": int(self.virt_ms / 1000), "device": DEVICE, "simulated": True})
        return d

    def pub(self, sub, obj, qos=0, retain=False):
        if not self.connected or self.client is None:
            return
        self.client.publish("huerto/casa/%s/%s" % (DEVICE, sub), json.dumps(self.base(obj), ensure_ascii=False),
                            qos=qos, retain=retain)

    def tank_pct(self):
        return 100.0 * self.w.tank_l / self.w.tank_cap

    # -------------------------------------------------------------- entradas
    def build_inputs(self):
        i = self.inp
        minute, hour = self.local()
        t, rh = self.w.weather(hour)
        cfg_rain_prob = self.core.cfg("rain_prob_pct")
        i.now_ms = self.virt_ms & 0xFFFFFFFF
        i.time_valid = True
        i.minute_of_day = minute
        i.day_key = self.day_key()
        i.epoch = self.ts()
        i.soil_valid = (not self.w.fail["soil"]) and self.soil_last_v is not None
        i.soil_vwc = self.soil_last_v if self.soil_last_v is not None else float("nan")
        i.soil_seq = self.soil_seq
        i.tank_valid = not self.w.fail["tank"]
        i.tank_calibrated = True
        i.tank_pct = self.tank_pct()
        i.env_valid = not self.w.fail["env"]
        i.temp_c = t + self.rnd.gauss(0, 0.1)
        i.rh_pct = rh + self.rnd.gauss(0, 0.5)
        i.flow_pulses = self.pulses
        i.outputs_enabled = True              # Actuadores VIRTUALES
        i.sensors_ready = self.soil_seq > 0
        i.rain_expected = self.rain_forecast_prob() >= cfg_rain_prob and self.rain_forecast_mm() >= self.core.cfg("rain_mm")
        i.rain_mm6 = self.rain_forecast_mm() if i.rain_expected else 0.0
        return i

    def rain_forecast_prob(self):
        return 90.0 if getattr(self, "forecast_rain_until", 0) > self.sim_epoch else 5.0

    def rain_forecast_mm(self):
        return getattr(self, "forecast_rain_mm", 6.0) if getattr(self, "forecast_rain_until", 0) > self.sim_epoch else 0.0

    def env_for_ia(self):
        e = Env()
        minute, hour = self.local()
        e.env_valid = self.inp.env_valid
        e.temp_c, e.rh_pct, e.hour = self.inp.temp_c, self.inp.rh_pct, hour
        e.kc = self.core.cfg("kc")
        e.hours_since_water = (self.virt_ms - self.last_water_end) / 3.6e6 if self.last_water_end else 24.0
        e.n_fc = 24
        for k in range(24):
            tt, rr = self.w.weather((hour + k + 0.5) % 24)
            es = 0.6108 * math.exp(17.27 * tt / (tt + 237.3))
            e.fc_temp[k], e.fc_rh[k], e.fc_vpd[k] = tt, rr, es * (1 - rr / 100)
            e.fc_et0[k] = max(0.0, 0.12 * e.fc_vpd[k])
        return e

    def update_plan(self):
        st = self.core.state()
        minute, _ = self.local()
        horizon = self.core.L.rc_hours_following(self.core.h, minute)
        v = self.inp.soil_vwc if self.inp.soil_valid else float("nan")
        self.core.L.rc_ia_plan(self.core.h, C.byref(self.env_for_ia()), v, horizon, C.byref(self.plan))
        info = self.core.ia_info()
        i = self.inp
        i.ia_active = info.status == 2
        i.ia_need = self.plan.valid and self.plan.code in (2, 3)
        i.ia_limited = self.plan.code == 3
        i.ia_liters = self.plan.liters
        i.ia_goal = self.plan.goal
        i.ia_corr_liters = (self.core.L.rc_ia_correction(self.core.h, i.soil_vwc, st.ev_goal, int(i.env_valid), i.temp_c, i.rh_pct)
                            if st.ev_active and st.ev_kind == 4 and i.soil_valid else 0.0)

    # --------------------------------------------------------------- sensores
    def soil_sample(self):
        self.soil_seq += 1
        if self.w.fail["soil"]:
            self.soil_last_v = None
            return
        self.soil_last_v = round(self.w.vwc + self.rnd.gauss(0, 0.2), 2)
        self.on_new_soil()

    # ------------------------------------------------------------------- IA
    def on_new_soil(self):
        v = self.soil_last_v
        st = self.core.state()
        now = self.virt_ms
        infilt_ms = self.core.cfg("infilt_min") * 60000
        recent = st.pump or st.ev_active or st.state in (3, 4) or (self.last_water_end and now - self.last_water_end < infilt_ms + 30 * 60000)
        if self.pend and now - self.pend["t_end"] >= infilt_ms:
            dv = v - self.pend["v0"]
            pred = C.c_float(float("nan"))
            p = self.pend
            r = self.core.L.rc_ia_learn_response(self.core.h, p["L"], p["v0"], int(p["env"]), p["t"], p["rh"], p["hs"], dv, C.byref(pred))
            self.pub_ia_obs("RESPUESTA_RIEGO", p["eid"], pred.value, dv, r, p["L"], p["v0"])
            self.pend = None
            self.ia_dirty = True
        rise = self.core.cfg("rise_pp")
        # Referencia = mínimo de las últimas 3 h (igual que el firmware)
        if recent or self.rise_ref is None or v < self.rise_ref or now - self.rise_ref_t > 3 * 3.6e6:
            self.rise_ref, self.rise_ref_t = v, now
        if not recent and now - self.rise_last > 2 * 3.6e6 and v - self.rise_ref >= rise:
            self.rise_pending += 1
            if self.rise_pending >= 2:
                cls = "POSIBLE_LLUVIA" if self.w.rain_now > 0 or getattr(self, "rained_recently", 0) > self.sim_epoch - 6 * 3600 else "POSIBLE_RIEGO_EXTERNO"
                if v - self.rise_ref > 15:
                    cls = "POSIBLE_ERROR_SENSOR"
                self.pub("event", {"type": "UNEXPLAINED_RISE", "classification": cls, "vwc_from": round(self.rise_ref, 1), "vwc_to": round(v, 1),
                                   "rise_pp": round(v - self.rise_ref, 1), "weather_fresh": True, "past6h_precip_mm": None,
                                   "note": "No se atribuye a litros de la bomba. Confirme la causa en el dashboard."}, 1)
                self.rise_last, self.rise_pending = now, 0
                self.rise_ref, self.rise_ref_t = v, now
            self.anchor = None
            return
        self.rise_pending = 0
        if recent:
            self.anchor = None
            return
        if not self.anchor:
            self.anchor = {"v": v, "t": now, "temp": self.inp.temp_c, "rh": self.inp.rh_pct}
            return
        dt = now - self.anchor["t"]
        if dt >= 3.6e6:
            dh = dt / 3.6e6
            rate = (self.anchor["v"] - v) / dh
            _, hour = self.local()
            pred = C.c_float(float("nan"))
            r = self.core.L.rc_ia_learn_drying(self.core.h, (self.anchor["v"] + v) / 2, (self.anchor["temp"] + self.inp.temp_c) / 2,
                                               (self.anchor["rh"] + self.inp.rh_pct) / 2, int(self.inp.env_valid), self.core.cfg("kc"),
                                               float("nan"), (hour - dh / 2) % 24, rate, C.byref(pred))
            self.pub_ia_obs("SECADO", None, pred.value, rate, r, (self.anchor["v"] + v) / 2, hour)
            self.anchor = {"v": v, "t": now, "temp": self.inp.temp_c, "rh": self.inp.rh_pct}
            self.ia_dirty = True

    def pub_ia_obs(self, model, eid, pred, obs, r, x1, x2):
        info = self.core.ia_info()
        nz = lambda x: None if x is None or (isinstance(x, float) and math.isnan(x)) else round(x, 3)
        self.pub("event", {"type": "IA_OBSERVATION", "model": model, "event_id": eid or "", "predicted": nz(pred), "observed": nz(obs),
                           "error": nz(obs - pred) if pred == pred else None,
                           "used": {0: "APRENDIDO", 1: "ATIPICO_DESCARTADO"}.get(r, "INVALIDO"), "x1": nz(x1), "x2": nz(x2),
                           "model_version": info.model_version, "status": self.core.name("rc_ia_status_name", info.status)}, 1)

    # --------------------------------------------------------------- eventos
    def handle_events(self):
        st = self.core.state()
        for e in self.core.events():
            if e.type == EV_STATE:
                self.state_dirty = True
            elif e.type == EV_DECISION:
                self.pub("decision", self.decision_json(), 1, True)
                self.dec_dirty = True
            elif e.type == EV_WATER_START:
                self.event_seq += 1
                self.event_id = "%s-%d" % (DEVICE, self.event_seq)
                self.pend, self.anchor = None, None
                hs = (self.virt_ms - self.last_water_end) / 3.6e6 if self.last_water_end else 24.0
                self.pred_dv = (self.core.L.rc_ia_predict_response(self.core.h, e.target_ml / 1000, e.vwc_before, int(self.inp.env_valid),
                                                                    self.inp.temp_c, self.inp.rh_pct, hs) if e.vwc_before == e.vwc_before else None)
                self.pub("event", {"type": "WATERING_START", "event_id": self.event_id, "reason": self.core.name("rc_reason_name", e.code),
                                   "mode": self.core.name("rc_mode_name", st.mode), "crop": self.cfgv("crop_id"), "stage": self.cfgv("stage"),
                                   "target_l": round(e.target_ml / 1000, 3), "vwc_before": self.nz(e.vwc_before), "goal_vwc": self.nz(st.ev_goal if st.ev_active else None),
                                   "ia_pred_dvwc": self.nz(self.pred_dv), "cycle": e.cycles}, 1)
                self.state_dirty = True
            elif e.type == EV_WATER_END:
                hs = (self.virt_ms - self.last_water_end) / 3.6e6 if self.last_water_end else 24.0
                self.last_water_end = self.virt_ms
                if e.delivered_ml >= 100 and e.vwc_before == e.vwc_before:
                    self.pend = {"L": e.delivered_ml / 1000, "v0": e.vwc_before, "t": self.inp.temp_c, "rh": self.inp.rh_pct,
                                 "env": self.inp.env_valid, "hs": hs, "t_end": self.virt_ms, "eid": self.event_id}
                dur = e.duration_ms / 60000
                self.pub("event", {"type": "WATERING_END", "event_id": self.event_id, "reason": self.core.name("rc_reason_name", e.code),
                                   "result": self.core.name("rc_result_name", e.code2), "mode": self.core.name("rc_mode_name", st.mode),
                                   "crop": self.cfgv("crop_id"), "stage": self.cfgv("stage"), "target_l": round(e.target_ml / 1000, 3),
                                   "delivered_l": round(e.delivered_ml / 1000, 3), "pulses": e.pulses, "pulses_per_liter": self.core.cfg("pulses_per_liter"),
                                   "avg_flow_lpm": round(e.delivered_ml / 1000 / dur, 2) if dur > 0 else None, "duration_s": round(e.duration_ms / 1000, 1),
                                   "vwc_before": self.nz(e.vwc_before), "vwc_after_immediate": self.nz(e.vwc_after),
                                   "today_l": round(st.daily_ml / 1000, 3), "ia_pred_dvwc": self.nz(self.pred_dv),
                                   "safety": "OK" if e.code2 in (1, 2) else self.core.name("rc_result_name", e.code2)}, 1)
                self.state_dirty = True
                self.save_state()
            elif e.type == EV_EVENT_END:
                self.pub("event", {"type": "EVENT_END", "event_id": self.event_id, "why": self.core.name("rc_decision_name", e.code),
                                   "why_text": self.core.name("rc_decision_text", e.code), "cycles": e.cycles,
                                   "liters": round(e.delivered_ml / 1000, 3), "vwc_before": self.nz(e.vwc_before),
                                   "vwc_after_infiltration": self.nz(e.vwc_after), "goal_vwc": self.nz(st.ev_goal)}, 1)
            elif e.type in (EV_ALARM_SET, EV_ALARM_CLEAR):
                a = e.code
                self.pub("alarm", {"code": self.core.name("rc_alarm_code", a), "severity": self.core.name("rc_alarm_sev", a),
                                   "active": e.type == EV_ALARM_SET, "latched": bool(self.core.L.rc_alarm_latched(a)),
                                   "message": "[SIMULADO] " + self.core.name("rc_alarm_text", a)}, 1)
                self.state_dirty = True

    @staticmethod
    def nz(v, d=1):
        return None if v is None or v != v else round(v, d)

    def cfgv(self, k):
        return self.core.config().get(k)

    # --------------------------------------------------------------- JSON
    def telemetry_json(self):
        self.telem_seq += 1
        st = self.core.state()
        i = self.inp
        es = self.core.L.rc_vpd(i.temp_c, i.rh_pct)
        mv = int((i.soil_vwc - self.core.cfg("ec5_offset")) / self.core.cfg("ec5_slope")) if i.soil_valid else 0
        dist = 110 - 0.9 * self.tank_pct()
        return {"seq": self.telem_seq, "boot": self.boot, "mode": self.core.name("rc_mode_name", st.mode),
                "state": self.core.name("rc_state_name", st.state), "crop": self.cfgv("crop_id"), "stage": self.cfgv("stage"),
                "data_version": self.cfgv("data_version"),
                "soil": {"valid": bool(i.soil_valid), "vwc_pct": self.nz(i.soil_vwc) if i.soil_valid else None, "mv": mv,
                         "in_cal_range": 360 <= mv <= 870, "status": "SIMULADO" if i.soil_valid else "SIMULADO_FALLA", "age_s": 0},
                "tank": {"valid": bool(i.tank_valid), "calibrated": True, "distance_cm": round(dist, 1) if i.tank_valid else None,
                         "level_pct": round(self.tank_pct()) if i.tank_valid else None, "below_min": bool(st.alarms & (1 << 10)),
                         "status": "SIMULADO" if i.tank_valid else "SIMULADO_SIN_ECO"},
                "env": {"valid": bool(i.env_valid), "temp_c": self.nz(i.temp_c) if i.env_valid else None,
                        "rh_pct": self.nz(i.rh_pct) if i.env_valid else None, "vpd_kpa": self.nz(es, 2) if i.env_valid else None,
                        "last_valid_ts": self.ts(), "status": "SIMULADO" if i.env_valid else "SIN_LECTURA"},
                "flow": {"lpm": round(st.w_flow_lpm if st.state in (3, 4) else 0.0, 2),
                         "session_l": round(st.w_delivered_ml / 1000, 3) if st.state in (3, 4) else 0.0,
                         "today_l": round(st.daily_ml / 1000, 3), "total_l": round(st.total_ml / 1000, 3), "pulses": self.pulses,
                         "pulses_per_liter": self.core.cfg("pulses_per_liter")}}

    def state_json(self):
        st = self.core.state()
        minute, _ = self.local()
        w = st.state in (3, 4)
        nw = self.core.L.rc_next_window(self.core.h, minute)
        alarms = [self.core.name("rc_alarm_code", a) for a in range(self.core.L.rc_alarm_count()) if st.alarms & (1 << a)]
        info = self.core.ia_info()
        inf_rem = 0
        if st.state == 5 and not st.infil_waiting:
            wait = self.core.cfg("infilt_min") * 60000
            inf_rem = max(0, int((wait - (self.virt_ms - st.infil_t_start)) / 1000 / max(1, self.speed)))
        cfg = self.core.config()
        return {"fw": FW, "state": self.core.name("rc_state_name", st.state), "phase": self.core.name("rc_phase_name", st.phase),
                "mode": self.core.name("rc_mode_name", st.mode), "install_profile": "A", "auto_enabled": st.mode != 0,
                "power_outputs": False, "pump": bool(st.pump), "valve": bool(st.valve), "pump_cmd": bool(st.pump),
                "valve_cmd": bool(st.valve), "emergency_latch": False, "ia_status": self.core.name("rc_ia_status_name", info.status),
                "crop": cfg["crop_id"], "crop_name": cfg["crop_name"], "stage": cfg["stage"], "profile_version": cfg["profile_version"],
                "watering": {"active": w, "type": self.core.name("rc_reason_name", st.w_reason) if w else "NONE", "event_id": self.event_id if w else "",
                             "target_l": round(st.w_target_ml / 1000, 3) if w else 0, "delivered_l": round(st.w_delivered_ml / 1000, 3) if w else 0,
                             "remaining_l": round(max(0, st.w_target_ml - st.w_delivered_ml) / 1000, 3) if w else 0,
                             "progress_pct": round(min(100, 100 * st.w_delivered_ml / st.w_target_ml)) if w and st.w_target_ml > 0 else 0,
                             "elapsed_s": int((self.virt_ms - st.w_t_start) / 1000) if w else 0, "flow_lpm": round(st.w_flow_lpm, 2) if w else 0,
                             "pulses": self.pulses - st.w_p0 if w else 0},
                "event": {"active": bool(st.ev_active), "kind": self.core.name("rc_kind_name", st.ev_kind), "emergency": bool(st.ev_emergency),
                          "cycles": st.ev_cycles, "liters": round(st.ev_ml / 1000, 3), "goal_vwc": self.nz(st.ev_goal) if st.ev_active else None,
                          "infiltration_remaining_s": inf_rem},
                "alarms": alarms, "decision": {"code": self.core.name("rc_decision_name", st.decision), "text": self.core.name("rc_decision_text", st.decision)},
                "next_window": "%02d:%02d" % (nw // 60, nw % 60) if nw >= 0 else "SIN_HORARIOS", "time_valid": True,
                "local_time": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(self.sim_epoch + TZ_OFF)),
                "wifi": True, "mqtt": True, "rssi": -50, "free_heap": 0, "rain_expected": bool(self.inp.rain_expected),
                "sim_speed": self.speed, "sim_world": {"true_vwc": round(self.w.vwc, 2), "tank_l": round(self.w.tank_l, 1),
                                                         "rain_now": self.w.rain_now, "fails": self.w.fail}}

    def decision_json(self):
        st = self.core.state()
        minute, _ = self.local()
        cfg = self.core.config()
        nw = self.core.L.rc_next_window(self.core.h, minute)
        return {"code": self.core.name("rc_decision_name", st.decision), "text": self.core.name("rc_decision_text", st.decision),
                "mode": self.core.name("rc_mode_name", st.mode), "soil_vwc": self.nz(self.inp.soil_vwc) if self.inp.soil_valid else None,
                "hum_critical": cfg["hum_critical"], "hum_min": cfg["hum_min"], "hum_target": cfg["hum_target"],
                "hum_reserve": cfg["hum_reserve"], "hum_max": cfg["hum_max"], "next_window": "%02d:%02d" % (nw // 60, nw % 60) if nw >= 0 else "SIN_HORARIOS",
                "in_window": bool(self.core.L.rc_in_window(self.core.h, minute)), "in_midday": bool(self.core.L.rc_in_midday(self.core.h, minute)),
                "rain_expected": bool(self.inp.rain_expected), "ia_active": bool(self.inp.ia_active),
                "state": self.core.name("rc_state_name", st.state)}

    def config_json(self):
        cfg = self.core.config()
        return {"profile_version": cfg["profile_version"], "params": cfg, "tank_calibrated": True, "flow_calibrated": False}

    def ia_json(self):
        info = self.core.ia_info()
        st = self.core.state()
        p = self.plan
        nz = self.nz
        status = self.core.name("rc_ia_status_name", info.status)
        return {"status": status, "mode_ia_selected": st.mode == 2, "controls_watering": st.mode == 2 and info.status == 2,
                "fallback": "AUTOMATICO_CONSERVADOR" if st.mode == 2 and info.status != 2 else "NINGUNO",
                "model_version": info.model_version, "data_version": info.data_version, "events_learned": info.n_a,
                "events_outliers": info.out_a, "drying_hours_learned": round(info.hours_b), "drying_outliers": info.out_b,
                "mae_response_pp": nz(info.mae_a, 2), "mae_drying_pph": nz(info.mae_b, 3),
                "last_response_error_pp": nz(info.last_err_a, 2) if info.n_a else None, "change_detected": bool(info.change_flag),
                "min_events": self.core.cfg("ia_min_events"), "min_hours": self.core.cfg("ia_min_hours"), "tolerance_pp": self.core.cfg("ia_tol_pp"),
                "coef_response": [round(x, 3) for x in info.wa], "coef_drying": [round(x, 4) for x in info.wb],
                "plan": {"valid": bool(p.valid), "code": self.core.name("rc_ia_plan_name", p.code), "vwc_now": nz(p.vwc_now) if p.valid else None,
                         "horizon_h": nz(p.horizon_h), "loss_pred_pp": nz(p.loss_pred, 2) if p.valid else None,
                         "vwc_end_no_water": nz(p.vwc_end_no_water) if p.valid else None, "goal_vwc": nz(p.goal) if p.valid else None,
                         "liters": nz(p.liters, 2) if p.valid else None, "gain_pp_per_l": nz(p.gain_per_l, 2) if p.valid else None,
                         "rate_now_pph": nz(p.rate_now, 3) if p.valid else None, "autonomy_h": nz(p.autonomy_h) if p.valid else None,
                         "uses_forecast": True, "pred_next_hour_vwc": nz(p.traj[1], 2) if p.valid else None,
                         "trajectory": [round(x, 2) for x in p.traj] if p.valid else []},
                "variables": ["humedad_suelo", "litros", "temperatura", "humedad_relativa", "VPD", "ET0_pronostico",
                              "Kc_etapa", "hora_del_dia", "horas_desde_riego"], "simulated_model": True}

    def weather_json(self):
        _, hour = self.local()
        t, rh = self.w.weather(hour)
        return {"source": "SIMULADOR (clima sintetico)", "valid": True, "fresh": True, "age_s": 0, "fetch_ts": self.ts(),
                "temp_c": round(t, 1), "rh_pct": round(rh), "precip_mm": self.w.rain_now, "past6h_precip_mm": None,
                "next6h_precip_mm": self.rain_forecast_mm(), "next6h_prob_max_pct": self.rain_forecast_prob(), "et0_24h_mm": 4.5,
                "rain_expected": bool(self.inp.rain_expected), "ok_count": 1, "fail_count": 0, "last_error": "", "lat": None, "lon": None}

    def diag_json(self):
        return {"fw": FW, "idf": "n/a (simulador en PC)", "mac": "00:00:00:00:00:00", "env": "casa", "base_topic": "huerto/casa/" + DEVICE,
                "wifi": {"connected": True, "network": "simulada", "ssid": "SIMULADOR", "ip": "127.0.0.1", "rssi": -50, "channel": 0,
                         "last_reason": 0, "last_reason_text": "sin error", "reconnects": 1, "saved_networks": []},
                "mqtt": {"broker": "mqtt://127.0.0.1:1883", "client_id": "simulador-" + DEVICE, "connected": self.connected,
                         "connects": 1, "broker_change": "NONE"},
                "free_heap": 0, "min_free_heap": 0, "reset_reason": 0, "boot_count": self.boot, "offline_buffer": 0}

    # -------------------------------------------------------------- comandos
    def ack(self, c, status, msg, extra=None):
        st = self.core.state()
        d = {"id": c.get("id", ""), "cmd": c.get("cmd", "?"), "status": status, "message": "[SIMULADOR] " + msg,
             "state": self.core.name("rc_state_name", st.state), "mode": self.core.name("rc_mode_name", st.mode)}
        if extra:
            d.update(extra)
        self.pub("ack", d, 1)

    def command(self, payload, retained):
        try:
            c = json.loads(payload)
            assert isinstance(c, dict)
        except Exception:  # noqa: BLE001
            return self.ack({}, "INVALID", "JSON invalido")
        cid, name = c.get("id"), str(c.get("cmd", "?"))
        if not cid or len(str(cid)) >= 40:
            return self.ack(c, "INVALID", "Falta 'id'")
        i = self.inp
        if name == "STOP":
            self.core.L.rc_cmd_stop(self.core.h, C.byref(i))
            return self.ack(c, "OK", "STOP ejecutado: bomba y electrovalvula (virtuales) apagadas")
        if retained:
            return self.ack(c, "RETAINED", "Comando retenido ignorado")
        if isinstance(c.get("ts"), (int, float)) and abs(time.time() - c["ts"]) > 60:
            return self.ack(c, "STALE", "Comando antiguo o con hora incorrecta")
        if cid in self.ids:
            return self.ack(c, "DUPLICATE", "Comando con id repetido")
        self.ids = (self.ids + [cid])[-32:]
        if name == "START_MANUAL":
            s, m = self.core.cmd("rc_cmd_start_manual", i, float(c.get("liters", 0)),
                               (1 if c.get("force") is True else 0) | (2 if c.get("over_daily") is True else 0))
            return self.ack(c, s, m)
        if name == "START_TO_TARGET":
            s, m = self.core.cmd("rc_cmd_to_target", i, float(c.get("goal") or 0), 2 if c.get("over_daily") is True else 0)
            return self.ack(c, s, m)
        if name in ("SET_MODE", "ENABLE_AUTO", "DISABLE_AUTO"):
            mode = self.core.L.rc_mode_from_name(str(c.get("mode", "")).encode()) if name == "SET_MODE" else (1 if name == "ENABLE_AUTO" else 0)
            if mode < 0:
                return self.ack(c, "INVALID", "'mode' debe ser MANUAL, AUTOMATICO o IA")
            s, m = self.core.cmd("rc_cmd_set_mode", i, mode)
            self.ia_dirty = True
            return self.ack(c, s, m, {"mode_applied": self.core.name("rc_mode_name", self.core.state().mode),
                                      "ia_status": self.core.name("rc_ia_status_name", self.core.ia_info().status)})
        if name in ("APPLY_CONFIG", "APPLY_PROFILE"):
            if self.core.state().state in (3, 4):
                return self.ack(c, "REJECTED", "Riego en curso: la configuracion anterior se mantiene")
            params, ver = c.get("params"), c.get("version")
            if not isinstance(params, dict) or not params or not isinstance(ver, (int, float)):
                return self.ack(c, "REJECTED", "Se requiere 'params' y 'version'")
            ok, m = self.core.apply(params, int(ver))
            cur = self.core.config()["profile_version"]
            if ok:
                self.save_state()
                self.pub("config", self.config_json(), 1, True)
                self.state_dirty = True          # cultivo, etapa y versión se ven de inmediato
                return self.ack(c, "OK", "Configuracion v%d aplicada (%d parametros)" % (ver, len(params)),
                                {"txn": cid, "version_requested": ver, "version_applied": ver, "params_changed": len(params)})
            return self.ack(c, "REJECTED", m, {"txn": cid, "version_requested": ver, "version_applied": cur})
        if name == "CLEAR_ALARM":
            a = c.get("alarm", "ALL")
            idx = -1 if a in (None, "ALL") else self.core.L.rc_alarm_from_name(str(a).encode())
            s, m = self.core.cmd("rc_cmd_clear", i, idx)
            return self.ack(c, s, m)
        if name == "IA_RESET":
            if c.get("confirm") != "BORRAR_MODELO":
                return self.ack(c, "INVALID", "Falta confirm")
            self.core.L.rc_ia_reset(self.core.h)
            self.save_state()
            self.ia_dirty = True
            return self.ack(c, "OK", "Modelo IA del simulador reiniciado")
        if name in ("GET_STATUS", "GET_CONFIG", "GET_IA", "NET_DIAG", "GET_HISTORY", "WEATHER_REFRESH"):
            self.publish_all()
            if name == "NET_DIAG":
                self.pub("diag", self.diag_json(), 1)
            return self.ack(c, "OK", "Estado publicado")
        if name == "SIM_CONTROL":
            return self.sim_control(c)
        if name == "SET_BROKER":
            return self.ack(c, "REJECTED", "El simulador no cambia de broker")
        return self.ack(c, "INVALID", "Comando no soportado por el simulador")

    def sim_control(self, c):
        a = c.get("action")
        v = c.get("value")
        msg = ""
        if a == "speed":
            self.speed = max(1.0, min(3600.0, float(v)))
            msg = "Velocidad x%g" % self.speed
        elif a == "rain":
            self.w.rain_now = 2.0
            self.w.external(float(v or 6))
            self.rained_recently = self.sim_epoch
            self.forecast_rain_until = self.sim_epoch + 3 * 3600
            msg = "Lluvia simulada (+%s pp)" % (v or 6)
        elif a == "external":
            self.w.external(float(v or 5))
            msg = "Riego externo simulado (+%s pp, no pasa por la bomba)" % (v or 5)
        elif a == "forecast_rain":
            self.forecast_rain_until = self.sim_epoch + 6 * 3600 if v else 0
            # 1 = 6 mm (valor de siempre); otro número = esos mm previstos en 6 h
            self.forecast_rain_mm = 6.0 if float(v or 0) in (0.0, 1.0) else float(v)
            msg = "Pronostico de lluvia simulado " + ("ACTIVO (%g mm)" % self.forecast_rain_mm if v else "desactivado")
        elif a in ("fail_soil", "fail_env", "fail_tank", "fail_flow"):
            self.w.fail[a[5:]] = bool(v)
            msg = "Falla simulada %s: %s" % (a[5:], "ACTIVA" if v else "resuelta")
        elif a == "tank":
            self.w.tank_l = max(0.0, min(self.w.tank_cap, float(v) / 100 * self.w.tank_cap))
            msg = "Tinaco simulado al %s %%" % v
        elif a == "soil":
            self.w.vwc = float(v)
            msg = "Humedad real simulada fijada en %s %%VWC" % v
        elif a == "dry":
            self.w.dry_scale = float(v)
            msg = "Secado x%s" % v
        elif a == "mqtt_drop":
            self.mqtt_drop_until = time.time() + float(v or 60)
            msg = "Se perdera MQTT %s s" % (v or 60)
            self.ack(c, "OK", msg)
            return
        elif a == "hour":
            h, m = str(v).split(":")
            minute, _ = self.local()
            self.sim_epoch += ((int(h) * 60 + int(m)) - minute) % 1440 * 60
            msg = "Hora simulada %s" % v
        else:
            return self.ack(c, "INVALID", "Accion desconocida")
        self.state_dirty = True
        return self.ack(c, "OK", msg)

    # ----------------------------------------------------------------- MQTT
    def connect(self):
        sec = read_env(self.a.env_file)
        cl = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="simulador-" + DEVICE, clean_session=True)
        cl.username_pw_set(sec["MQTT_SIM_USER"], sec["MQTT_SIM_PASS"])
        cl.will_set("huerto/casa/%s/status" % DEVICE, json.dumps({"online": False, "reason": "LWT", "device": DEVICE, "simulated": True}), 1, True)
        cl.reconnect_delay_set(1, 30)

        def on_connect(c, u, f, rc, p=None):
            if rc == 0:
                self.connected = True
                c.subscribe("huerto/casa/%s/command" % DEVICE, 1)
                c.publish("huerto/casa/%s/status" % DEVICE, json.dumps({"online": True, "device": DEVICE, "simulated": True,
                                                                        "client_id": "simulador-" + DEVICE}), 1, True)
                self.q.put(("connected", None, None))
            else:
                print("MQTT rechazo la conexion:", rc)

        def on_disconnect(c, u, f, rc, p=None):
            self.connected = False

        def on_message(c, u, m):
            self.q.put(("cmd", m.payload.decode("utf-8", "replace"), m.retain))

        cl.on_connect, cl.on_disconnect, cl.on_message = on_connect, on_disconnect, on_message
        cl.connect_async(self.a.host, 1883, 30)
        cl.loop_start()
        self.client = cl

    def publish_all(self):
        self.pub("state", self.state_json(), 1, True)
        self.pub("telemetry", self.telemetry_json(), 0)
        self.pub("decision", self.decision_json(), 1, True)
        self.pub("config", self.config_json(), 1, True)
        self.pub("ia", self.ia_json(), 1, True)
        self.pub("weather", self.weather_json(), 1, True)

    # ---------------------------------------------------------------- ciclo
    def tick(self, dt_real):
        dt_sim = dt_real * self.speed
        self.sim_epoch += dt_sim
        self.virt_ms += int(dt_sim * 1000)
        _, hour = self.local()
        st = self.core.state()
        if self.w.rain_now > 0 and self.rnd.random() < dt_sim / 1800:
            self.w.rain_now = 0.0
        self.w.step(dt_sim / 3600, hour, self.core.cfg("kc"))
        if st.pump and st.valve and not self.w.fail["flow"] and self.w.tank_l > 0:
            lpm = self.w.flow_lpm * (1 + self.rnd.gauss(0, 0.02))
            liters = lpm * dt_sim / 60
            self.pulse_acc += liters * self.core.cfg("pulses_per_liter")
            n = int(self.pulse_acc)
            self.pulses += n
            self.pulse_acc -= n
            self.w.add_water(liters)
        interval_ms = max(30, st.soil_interval_s) * 1000
        if st.want_soil or self.virt_ms >= self.soil_next_ms or (self.pend and self.virt_ms - self.pend["t_end"] >= self.core.cfg("infilt_min") * 60000):
            if self.virt_ms >= self.soil_next_ms or st.want_soil or self.pend:
                self.soil_sample()
                self.soil_next_ms = self.virt_ms + interval_ms
        self.build_inputs()
        self.update_plan()
        self.core.L.rc_step(self.core.h, C.byref(self.inp))
        self.handle_events()

    def run_live(self):
        self.connect()
        self.state_dirty = self.dec_dirty = self.ia_dirty = True
        last = time.time()
        t_tel = t_state = t_ia = t_save = 0.0
        print("Simulador en marcha: huerto/casa/%s (DATOS SIMULADOS) x%g" % (DEVICE, self.speed))
        dropped = False
        while True:
            now = time.time()
            self.tick(now - last)
            last = now
            if self.mqtt_drop_until > now and not dropped:
                dropped = True
                # Corte "sucio" (sin DISCONNECT): el broker publica la última voluntad (LWT)
                sock = self.client.socket()
                self.client.loop_stop()
                try:
                    sock.shutdown(2)
                    sock.close()
                except Exception:  # noqa: BLE001
                    pass
                self.connected = False
            elif dropped and self.mqtt_drop_until <= now:
                dropped = False
                self.connect()
            while not self.q.empty():
                kind, payload, retained = self.q.get()
                if kind == "cmd":
                    self.command(payload, retained)
                    self.build_inputs()
                elif kind == "connected":
                    self.publish_all()
                    self.pub("diag", self.diag_json(), 1)
            if now - t_tel >= 10:
                t_tel = now
                self.pub("telemetry", self.telemetry_json(), 0)
            st = self.core.state()
            if self.state_dirty or now - t_state >= (1 if st.state in (3, 4) else 30):
                if now - t_state >= 0.5:
                    self.pub("state", self.state_json(), 1, True)
                    t_state, self.state_dirty = now, False
            if self.ia_dirty or now - t_ia >= 60:
                self.pub("ia", self.ia_json(), 1, True)
                self.pub("weather", self.weather_json(), 1, True)
                t_ia, self.ia_dirty = now, False
            if now - t_save >= 300:
                t_save = now
                self.save_state()
            time.sleep(0.2)

    def pretrain(self, days):
        """Simula N días SIN MQTT con el modo AUTOMÁTICO para que la IA aprenda (modelo SIMULADO)."""
        self.client, self.connected = None, False
        self.state_dirty = self.dec_dirty = self.ia_dirty = False
        self.core.cmd("rc_cmd_set_mode", self.inp, 1)
        self.core.L.rc_allow_auto_now(self.core.h)
        step = 20.0
        total = int(days * 86400 / step)
        for k in range(total):
            self.speed = 1.0
            if self.w.tank_l < 60:
                self.w.tank_l = self.w.tank_cap      # se rellena el tinaco simulado
            self.tick(step)
            if k % int(86400 / step) == 0:
                info = self.core.ia_info()
                print("dia %d: humedad %.1f, IA %s, riegos aprendidos %d, horas %.0f, MAE %.2f / %.3f" % (
                    k * step / 86400, self.w.vwc, self.core.name("rc_ia_status_name", info.status), info.n_a, info.hours_b,
                    info.mae_a, info.mae_b))
        self.core.cmd("rc_cmd_set_mode", self.inp, 0)
        self.sim_epoch = time.time()
        self.save_state()
        info = self.core.ia_info()
        print("Preentrenamiento SIMULADO terminado: IA %s (%d riegos, %.0f h). Guardado en %s" % (
            self.core.name("rc_ia_status_name", info.status), info.n_a, info.hours_b, STATE_FILE))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--velocidad", type=float, default=1.0)
    ap.add_argument("--preentrenar", type=float, default=0, help="Dias simulados para entrenar la IA (sin MQTT)")
    ap.add_argument("--env-file", default=os.path.join(ROOT, "configs", "secrets", "credenciales_casa.env"))
    a = ap.parse_args()
    dev = SimDevice(a)
    if a.preentrenar > 0:
        dev.pretrain(a.preentrenar)
        return
    dev.run_live()


if __name__ == "__main__":
    main()
