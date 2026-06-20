# Simulación DBR — Flow Shop 4 Estaciones

**Paper:** Relación entre Tanda de Transferencia y Buffer de Restricción  
**Curso:** Ingeniería de Operaciones II-0703, Universidad de Costa Rica, 2026  

## Descripción
Este proyecto implementa una simulación en **Python (SimPy + NumPy + Pandas)** para analizar la interacción entre el tamaño de la **tanda de transferencia (TT)** y el **buffer de restricción** en sistemas controlados por **Drum-Buffer-Rope (DBR)**.  

El objetivo es evaluar cómo la reducción de la tanda de transferencia impacta el dimensionamiento del buffer y las métricas de desempeño del sistema (WIP, lead time, utilización del cuello de botella, cumplimiento de entregas).

---

## Metodología
- **Modelo:** Flow Shop de 4 estaciones (M1–M4), con M3 como **cuello de botella (CB)**.
- **Parámetros base:**  
  - Orden = 3000 unidades  
  - Interarribo medio = 7.5 h  
  - 150 órdenes por réplica  
  - 30 réplicas por escenario  
- **Control DBR:**  
  - Rope limita las transferencias en tránsito antes del CB.  
  - Buffer dimensionado en horas de capacidad del CB.  

---

## Escenarios simulados
1. **E1:** TT=1000, Buffer=4h (Base)  
2. **E2:** TT=500, Buffer=4h (Buffer fijo)  
3. **E3:** TT=500, Buffer=2h (Proporcional)  
4. **E4:** TT=250, Buffer=2h (Buffer medio)  
5. **E5:** TT=250, Buffer=1h (Proporcional)  
6. **E6:** TT=1000, Buffer=2h (Buffer bajo)  

---

## Métricas calculadas
- **Lead Time (h)**: tiempo promedio de ciclo por transferencia.  
- **OTD (%)**: porcentaje de entregas a tiempo.  
- **WIP promedio**: inventario en proceso.  
- **Utilización CB (%)**: porcentaje de ocupación del cuello de botella.  
- **Tiempo ocioso CB (%)**: tiempo de inactividad del cuello de botella.  
- **Espera en buffer (h)**: tiempo promedio de espera antes del CB.  

---

## Resultados
La simulación genera dos archivos CSV:
- `resultados_resumen.csv` → métricas promedio por escenario.  
- `resultados_detalle.csv` → resultados por réplica.  

Estos archivos permiten análisis estadístico y comparación entre escenarios.

---

## Ejecución
1. Instalar dependencias:
   ```bash
   pip install simpy numpy pandas
