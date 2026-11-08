"""Enlace ctypes con riego_core.dll: la MISMA lógica en C del firmware del ESP32
(máquina de estados, validación de configuración e IA) compilada para la PC."""
import ctypes as C
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DLL = os.path.join(HERE, "..", "tests", "host", "build", "riego_core.dll" if os.name == "nt" else "libriego_core.so")

NA, NB, FC, TRAJ = 5, 6, 24, 25


class Inputs(C.Structure):
    _fields_ = [("now_ms", C.c_uint32), ("time_valid", C.c_bool), ("minute_of_day", C.c_int), ("day_key", C.c_int32),
                ("epoch", C.c_uint32), ("soil_valid", C.c_bool), ("soil_vwc", C.c_float), ("soil_seq", C.c_uint32),
                ("tank_valid", C.c_bool), ("tank_calibrated", C.c_bool), ("tank_pct", C.c_float),
                ("env_valid", C.c_bool), ("temp_c", C.c_float), ("rh_pct", C.c_float),
                ("flow_pulses", C.c_uint32), ("outputs_enabled", C.c_bool), ("sensors_ready", C.c_bool),
                ("rain_expected", C.c_bool), ("ia_active", C.c_bool), ("ia_need", C.c_bool), ("ia_limited", C.c_bool),
                ("ia_liters", C.c_float), ("ia_goal", C.c_float), ("ia_corr_liters", C.c_float),
                ("rain_mm6", C.c_float)]


class Event(C.Structure):
    _fields_ = [("type", C.c_int), ("code", C.c_int), ("code2", C.c_int), ("target_ml", C.c_float),
                ("delivered_ml", C.c_float), ("vwc_before", C.c_float), ("vwc_after", C.c_float),
                ("duration_ms", C.c_uint32), ("pulses", C.c_uint32), ("cycles", C.c_int)]


class Env(C.Structure):
    _fields_ = [("env_valid", C.c_bool), ("temp_c", C.c_float), ("rh_pct", C.c_float), ("hour", C.c_float),
                ("kc", C.c_float), ("hours_since_water", C.c_float), ("n_fc", C.c_int),
                ("fc_temp", C.c_float * FC), ("fc_rh", C.c_float * FC), ("fc_vpd", C.c_float * FC), ("fc_et0", C.c_float * FC)]


class Plan(C.Structure):
    _fields_ = [("valid", C.c_bool), ("code", C.c_int), ("vwc_now", C.c_float), ("horizon_h", C.c_float),
                ("loss_pred", C.c_float), ("vwc_end_no_water", C.c_float), ("goal", C.c_float),
                ("gain_per_l", C.c_float), ("liters", C.c_float), ("autonomy_h", C.c_float), ("rate_now", C.c_float),
                ("traj", C.c_float * TRAJ)]


class State(C.Structure):
    _fields_ = [("state", C.c_int), ("phase", C.c_int), ("mode", C.c_int), ("pump", C.c_int), ("valve", C.c_int),
                ("decision", C.c_int), ("alarms", C.c_uint), ("w_reason", C.c_int), ("w_target_ml", C.c_float),
                ("w_delivered_ml", C.c_float), ("w_flow_lpm", C.c_float), ("w_t_start", C.c_uint), ("w_p0", C.c_uint),
                ("ev_active", C.c_int), ("ev_kind", C.c_int), ("ev_cycles", C.c_int), ("ev_emergency", C.c_int),
                ("ev_ml", C.c_float), ("ev_goal", C.c_float), ("infil_t_start", C.c_uint), ("infil_waiting", C.c_int),
                ("want_soil", C.c_int), ("daily_ml", C.c_float), ("total_ml", C.c_double), ("soil_interval_s", C.c_int),
                ("have_last_event", C.c_int)]


class IaInfo(C.Structure):
    _fields_ = [("status", C.c_int), ("change_flag", C.c_int), ("n_a", C.c_uint), ("out_a", C.c_uint), ("n_b", C.c_uint),
                ("out_b", C.c_uint), ("model_version", C.c_uint), ("hours_b", C.c_float), ("mae_a", C.c_float),
                ("mae_b", C.c_float), ("last_err_a", C.c_float), ("data_version", C.c_float),
                ("wa", C.c_float * NA), ("wb", C.c_float * NB)]


EV_STATE, EV_WATER_START, EV_WATER_END, EV_EVENT_END, EV_DECISION, EV_ALARM_SET, EV_ALARM_CLEAR, EV_COUNTERS = range(8)


class Core:
    def __init__(self, path=DLL):
        self.L = L = C.CDLL(os.path.abspath(path))
        s = lambda f, res, *args: (setattr(getattr(L, f), "restype", res), setattr(getattr(L, f), "argtypes", list(args)))
        P, I, F, S = C.c_void_p, C.c_int, C.c_float, C.c_char_p
        for name in ("rc_state_name", "rc_phase_name", "rc_reason_name", "rc_result_name", "rc_decision_name",
                     "rc_decision_text", "rc_mode_name", "rc_kind_name", "rc_alarm_code", "rc_alarm_text", "rc_alarm_sev",
                     "rc_ia_status_name", "rc_ia_plan_name"):
            s(name, S, I)
        s("rc_new", P)
        s("rc_step", None, P, C.POINTER(Inputs))
        s("rc_pop_event", I, P, C.POINTER(Event))
        s("rc_get_state", None, P, C.POINTER(State))
        s("rc_set_counters", None, P, F, C.c_double, I)
        s("rc_allow_auto_now", None, P)
        s("rc_cand_begin", None, P)
        s("rc_cand_set", I, P, S, S, I, S, I)
        s("rc_cand_set_version", None, P, C.c_uint)
        s("rc_cand_commit", I, P, S, I)
        s("rc_param_count", I)
        s("rc_param_info", I, I, S, I, C.POINTER(I), C.POINTER(I))
        s("rc_param_format", None, P, I, S, I)
        s("rc_param_float", F, P, S)
        s("rc_cmd_start_manual", I, P, C.POINTER(Inputs), F, I, S, I)
        s("rc_cmd_stop", None, P, C.POINTER(Inputs))
        s("rc_cmd_set_mode", I, P, C.POINTER(Inputs), I, S, I)
        s("rc_cmd_to_target", I, P, C.POINTER(Inputs), F, I, S, I)
        s("rc_cmd_clear", I, P, C.POINTER(Inputs), I, S, I)
        s("rc_raise_alarm", None, P, C.POINTER(Inputs), I)
        s("rc_set_condition", None, P, I, I)
        s("rc_next_window", I, P, I)
        s("rc_hours_following", F, P, I)
        s("rc_in_window", I, P, I)
        s("rc_in_midday", I, P, I)
        s("rc_mode_from_name", I, S)
        s("rc_alarm_count", I)
        s("rc_alarm_latched", I, I)
        s("rc_alarm_from_name", I, S)
        s("rc_vpd", F, F, F)
        s("rc_ia_reset", None, P)
        s("rc_ia_predict_response", F, P, F, F, I, F, F, F)
        s("rc_ia_learn_response", I, P, F, F, I, F, F, F, F, C.POINTER(F))
        s("rc_ia_learn_drying", I, P, F, F, F, I, F, F, F, F, C.POINTER(F))
        s("rc_ia_plan", None, P, C.POINTER(Env), F, F, C.POINTER(Plan))
        s("rc_ia_correction", F, P, F, F, I, F, F)
        s("rc_ia_info", None, P, C.POINTER(IaInfo))
        s("rc_ia_size", I)
        s("rc_ia_export", None, P, C.c_void_p)
        s("rc_ia_import", I, P, C.c_void_p)
        s("rc_sizeof_inputs", I)
        s("rc_sizeof_env", I)
        s("rc_sizeof_plan", I)
        s("rc_sizeof_event", I)
        assert L.rc_sizeof_inputs() == C.sizeof(Inputs), (L.rc_sizeof_inputs(), C.sizeof(Inputs))
        assert L.rc_sizeof_env() == C.sizeof(Env)
        assert L.rc_sizeof_plan() == C.sizeof(Plan)
        assert L.rc_sizeof_event() == C.sizeof(Event)
        self.h = L.rc_new()
        self.params = []
        for i in range(L.rc_param_count()):
            k = C.create_string_buffer(40)
            t, r = C.c_int(), C.c_int()
            L.rc_param_info(i, k, 40, C.byref(t), C.byref(r))
            self.params.append((k.value.decode(), t.value, bool(r.value)))

    @staticmethod
    def s(b):
        return b.decode("utf-8", "replace") if isinstance(b, bytes) else b

    def name(self, fn, v):
        return self.s(getattr(self.L, fn)(int(v)))

    def state(self):
        st = State()
        self.L.rc_get_state(self.h, C.byref(st))
        return st

    def events(self):
        out = []
        ev = Event()
        while self.L.rc_pop_event(self.h, C.byref(ev)):
            out.append(Event.from_buffer_copy(ev))
        return out

    def config(self):
        d = {}
        for i, (k, t, _) in enumerate(self.params):
            buf = C.create_string_buffer(64)
            self.L.rc_param_format(self.h, i, buf, 64)
            v = buf.value.decode("utf-8", "replace")
            if t == 1:
                d[k] = v == "true"
            elif t in (2, 3):
                d[k] = v
            else:
                try:
                    d[k] = float(v) if "." in v else int(v)
                except ValueError:
                    d[k] = v
        return d

    def cfg(self, key):
        return self.L.rc_param_float(self.h, key.encode())

    def apply(self, params, version=None, remote_only=True):
        """Aplica varios parámetros de forma atómica (misma validación que el ESP32)."""
        msg = C.create_string_buffer(200)
        self.L.rc_cand_begin(self.h)
        for k, v in params.items():
            if isinstance(v, bool):
                v = "true" if v else "false"
            if self.L.rc_cand_set(self.h, str(k).encode(), str(v).encode(), 1 if remote_only else 0, msg, 200) != 0:
                return False, msg.value.decode("utf-8", "replace")
        if version is not None:
            self.L.rc_cand_set_version(self.h, int(version))
        if self.L.rc_cand_commit(self.h, msg, 200) != 0:
            return False, msg.value.decode("utf-8", "replace")
        return True, ""

    def cmd(self, fn, inp, *args):
        msg = C.create_string_buffer(220)
        r = getattr(self.L, fn)(self.h, C.byref(inp), *args, msg, 220)
        return {0: "OK", 1: "REJECTED", 2: "INVALID"}.get(r, "?"), msg.value.decode("utf-8", "replace")

    def ia_info(self):
        i = IaInfo()
        self.L.rc_ia_info(self.h, C.byref(i))
        return i

    def ia_export(self):
        n = self.L.rc_ia_size()
        buf = C.create_string_buffer(n)
        self.L.rc_ia_export(self.h, buf)
        return buf.raw

    def ia_import(self, raw):
        buf = C.create_string_buffer(raw, len(raw))
        return self.L.rc_ia_import(self.h, buf) == 0
