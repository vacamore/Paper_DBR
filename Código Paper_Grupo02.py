#!/usr/bin/env python
# coding: utf-8

# In[6]:


get_ipython().system('pip install simpy')


# In[11]:


"""
Simulación DBR — Flow Shop 4 estaciones
Paper: Relación entre Tanda de Transferencia y Buffer de Restricción
Curso: Ingeniería de Operaciones II-0703, UCR, 2026
"""

import simpy
import numpy as np
import pandas as pd

# ============================================================
# PARÁMETROS BASE
# ============================================================
BASE_TIMES = {
    'M1': 0.5,    # horas de proceso por cada TT=1000 unidades
    'M2': 1.0,
    'M3': 2.0,    # Cuello de Botella (CB) — tiempo más largo
    'M4': 0.5,
}
ORDER_QTY         = 3000   # unidades por orden
MEAN_INTERARRIVAL = 7.5    # horas entre órdenes → CB ~80% utilizado
NUM_ORDERS        = 150    # órdenes por réplica (más = más estable)
N_REPLICAS        = 30     # réplicas por escenario


# ============================================================
# SIMULACIÓN DE UN ESCENARIO
# ============================================================
def simulate_dbr(TT, buffer_hours, seed=42):
    rng   = np.random.default_rng(seed)
    env   = simpy.Environment()

    scale = TT / 1000.0
    proc  = {m: BASE_TIMES[m] * scale for m in BASE_TIMES}
    n_tf  = ORDER_QTY // TT   # transferencias por orden

    # Recursos
    machines = {m: simpy.Resource(env, capacity=1) for m in BASE_TIMES}

    # Cuerda (Rope): limita cuántas transferencias están en tránsito antes del CB.
    # Capacidad = cuántas transferencias caben en el tiempo de buffer.
    rope_cap = max(1, int(buffer_hours / proc['M3']))
    rope     = simpy.Container(env, capacity=rope_cap, init=rope_cap)

    # Métricas
    records      = []
    m3_busy      = [0.0]
    wip          = [0]
    wip_log      = []
    t_first      = [None]    # primer evento de llegada
    t_last       = [0.0]     # última salida del sistema

    def log_wip():
        wip_log.append((env.now, wip[0]))

    def transfer_proc(tid, oid, due_date):
        t_arrive = env.now
        if t_first[0] is None:
            t_first[0] = t_arrive
        wip[0] += 1
        log_wip()

        # ROPE: esperar si el buffer ya está lleno
        yield rope.get(1)

        # M1
        with machines['M1'].request() as req:
            yield req
            yield env.timeout(rng.exponential(proc['M1']))

        # M2
        with machines['M2'].request() as req:
            yield req
            yield env.timeout(rng.exponential(proc['M2']))

        t_buf_enter = env.now

        # CB (M3) — Cuello de Botella
        with machines['M3'].request() as req:
            yield req
            t_m3_start = env.now
            pt = rng.exponential(proc['M3'])
            yield env.timeout(pt)
            m3_busy[0] += pt

        yield rope.put(1)   # liberar token al terminar CB

        # M4
        with machines['M4'].request() as req:
            yield req
            yield env.timeout(rng.exponential(proc['M4']))

        t_done = env.now
        wip[0] -= 1
        log_wip()
        if t_done > t_last[0]:
            t_last[0] = t_done

        records.append({
            'oid'       : oid,
            'lead_time' : t_done - t_arrive,
            'buf_wait'  : t_m3_start - t_buf_enter,
            'on_time'   : int(t_done <= due_date),
        })

    def order_generator():
        for oid in range(NUM_ORDERS):
            if oid > 0:
                yield env.timeout(rng.exponential(MEAN_INTERARRIVAL))

            # Fecha límite = llegada + 3× el tiempo total que toma
            # completar todas las transferencias en secuencia en el CB
            # (n_tf × proc_CB) × factor 3 para absorber variabilidad
            due_date = env.now + n_tf * proc['M3'] * 3.0

            for i in range(n_tf):
                env.process(transfer_proc(oid * n_tf + i, oid, due_date))
                if i < n_tf - 1:
                    yield env.timeout(0.001)

    env.process(order_generator())
    env.run()   # corre hasta que no haya más eventos

    if not records or t_first[0] is None:
        return None

    df           = pd.DataFrame(records)
    active_time  = t_last[0] - t_first[0]   # tiempo real de operación

    # WIP promedio (área bajo la curva / tiempo activo)
    if len(wip_log) > 1:
        ts, ws  = zip(*wip_log)
        avg_wip = np.trapz(ws, ts) / max(active_time, 1.0)
    else:
        avg_wip = 0

    cb_util = (m3_busy[0] / active_time) * 100 if active_time > 0 else 0

    return {
        'TT'          : TT,
        'buffer_h'    : buffer_hours,
        'rope_cap'    : rope_cap,
        'n_tf_orden'  : n_tf,
        'lead_time'   : df['lead_time'].mean(),
        'lead_time_sd': df['lead_time'].std(),
        'OTD'         : df['on_time'].mean() * 100,
        'avg_wip'     : avg_wip,
        'cb_util'     : cb_util,
        'cb_starv'    : 100 - cb_util,
        'buf_wait'    : df['buf_wait'].mean(),
    }


# ============================================================
# ESCENARIOS
# ============================================================
SCENARIOS = [
    {'label': 'E1 - TT=1000 Buffer=4h (Base)',         'TT': 1000, 'buffer_hours': 4.0},
    {'label': 'E2 - TT=500 Buffer=4h (Buffer fijo)',   'TT':  500, 'buffer_hours': 4.0},
    {'label': 'E3 - TT=500 Buffer=2h (Proporcional)',  'TT':  500, 'buffer_hours': 2.0},
    {'label': 'E4 - TT=250 Buffer=2h (Buffer medio)',  'TT':  250, 'buffer_hours': 2.0},
    {'label': 'E5 - TT=250 Buffer=1h (Proporcional)',  'TT':  250, 'buffer_hours': 1.0},
    {'label': 'E6 - TT=1000 Buffer=2h (Buffer bajo)',  'TT': 1000, 'buffer_hours': 2.0},
]


# ============================================================
# EJECUTAR TODOS LOS ESCENARIOS
# ============================================================
if __name__ == '__main__':
    print("=" * 68)
    print("  SIMULACIÓN DBR — Tanda de Transferencia vs Buffer")
    print(f"  {N_REPLICAS} réplicas × {NUM_ORDERS} órdenes × {len(SCENARIOS)} escenarios")
    print("=" * 68)

    summary_rows = []
    raw_rows     = []

    for sc in SCENARIOS:
        TT, buf = sc['TT'], sc['buffer_hours']
        label   = sc['label']
        print(f"\n{label}  (TT={TT}, Buffer={buf}h)")

        reps = []
        for seed in range(N_REPLICAS):
            res = simulate_dbr(TT, buf, seed=seed)
            if res:
                res['replica'] = seed
                reps.append(res)
                raw_rows.append(res)

        if not reps:
            continue

        df_r = pd.DataFrame(reps)

        row = {
            'Escenario'      : label,
            'TT'             : TT,
            'Buffer (h)'     : buf,
            'TF/Orden'       : ORDER_QTY // TT,
            'Lead Time (h)'  : round(df_r['lead_time'].mean(), 2),
            'SD Lead Time'   : round(df_r['lead_time'].std(), 2),
            'OTD (%)'        : round(df_r['OTD'].mean(), 1),
            'WIP Prom.'      : round(df_r['avg_wip'].mean(), 1),
            'Util. CB (%)'   : round(df_r['cb_util'].mean(), 1),
            'Tiempo ocioso CB (%)'  : round(df_r['cb_starv'].mean(), 1),
            'Espera Buffer(h)': round(df_r['buf_wait'].mean(), 2),
        }
        summary_rows.append(row)

        print(f"  Lead Time : {row['Lead Time (h)']} ± {row['SD Lead Time']} h")
        print(f"  OTD       : {row['OTD (%)']}%")
        print(f"  WIP       : {row['WIP Prom.']}")
        print(f"  Util. CB  : {row['Util. CB (%)']}%")
        print(f"  Tiempo ocioso CB : {row['Tiempo ocioso CB (%)']  }%")

    df_summary = pd.DataFrame(summary_rows)
    df_raw     = pd.DataFrame(raw_rows)
    
    df_summary.to_csv(r'C:\Users\Valerie Campos\OneDrive - Universidad de Costa Rica\Universidad\5to año\Ingeniería de Operaciones\Paper\resultados_resumen.csv', index=False)
    df_raw.to_csv(r'C:\Users\Valerie Campos\OneDrive - Universidad de Costa Rica\Universidad\5to año\Ingeniería de Operaciones\Paper\resultados_detalle.csv', index=False)
    

    print("\n" + "=" * 68)
    print("RESUMEN FINAL")
    print("=" * 68)
    print(df_summary.to_string(index=False))
    print("\nArchivos guardados: resultados_resumen.csv  /  resultados_detalle.csv")


# In[ ]:




