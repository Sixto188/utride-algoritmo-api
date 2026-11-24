import csv
import time
import requests
import numpy as np
import matplotlib.pyplot as plt

# ==============================================================================
# 1. NÚCLEO DEL MODELO (Mismas funciones productivas de main_api.py)
# ==============================================================================
def obtener_ruta_osrm(origen: tuple, destino: tuple) -> np.ndarray:
    coords_url = f"{origen[1]},{origen[0]};{destino[1]},{destino[0]}"
    url = f"http://router.project-osrm.org/route/v1/driving/{coords_url}?overview=full&geometries=geojson"
    datos = requests.get(url, timeout=15).json()
    if datos.get("code") != "Ok":
        raise RuntimeError("Error consultando ruta en OSRM.")
    puntos = datos["routes"][0]["geometry"]["coordinates"]
    return np.array([(lat, lon) for lon, lat in puntos])

def construir_matriz_distancias(ruta_nodos: np.ndarray, pasajeros_coords: np.ndarray) -> np.ndarray:
    R = 6371000.0
    ruta_rad = np.radians(ruta_nodos)[:, np.newaxis, :]
    pasajeros_rad = np.radians(pasajeros_coords)[np.newaxis, :, :]
    dlat = pasajeros_rad[:, :, 0] - ruta_rad[:, :, 0]
    dlon = pasajeros_rad[:, :, 1] - ruta_rad[:, :, 1]
    a = np.sin(dlat / 2.0)**2 + np.cos(ruta_rad[:, :, 0]) * np.cos(pasajeros_rad[:, :, 0]) * np.sin(dlon / 2.0)**2
    return 2 * R * np.arcsin(np.sqrt(a))

def de_optimizar_parada(matriz_distancias: np.ndarray, col_pasajero: int, tam_pob=20, gens=40, F=0.7, CR=0.8):
    num_nodos = matriz_distancias.shape[0]
    lim_inf, lim_sup = 0, num_nodos - 1

    def fitness_func(x):
        idx = int(np.clip(round(x), lim_inf, lim_sup))
        dist = matriz_distancias[idx, col_pasajero]
        return dist if dist <= 400.0 else dist + (dist - 400.0) * 10.0

    poblacion = np.random.uniform(lim_inf, lim_sup, tam_pob)
    fitness = np.array([fitness_func(ind) for ind in poblacion])

    for _ in range(gens):
        for i in range(tam_pob):
            candidatos = [idx for idx in range(tam_pob) if idx != i]
            r1, r2, r3 = np.random.choice(candidatos, 3, replace=False)
            mutante = np.clip(poblacion[r1] + F * (poblacion[r2] - poblacion[r3]), lim_inf, lim_sup)
            prueba = mutante if np.random.rand() < CR else poblacion[i]
            f_prueba = fitness_func(prueba)
            if f_prueba < fitness[i]:
                poblacion[i] = prueba
                fitness[i] = f_prueba

    mejor_idx_pob = np.argmin(fitness)
    nodo_optimo = int(np.clip(round(poblacion[mejor_idx_pob]), lim_inf, lim_sup))
    distancia_final = float(matriz_distancias[nodo_optimo, col_pasajero])
    return nodo_optimo, distancia_final

# ==============================================================================
# 2. DEFINICIÓN DE LOS 20 ESCENARIOS SIMULADOS HACIA LA UTR (Aguascalientes)
# ==============================================================================
# Destino base: Universidad Tecnológica El Retoño (El Llano, Ags.)
UTR_DESTINO = (21.8565, -102.1380)

# Corredores base de conductores
RUTA_NORTE = (21.9145, -102.2510)      # Salida Norte / Siglo XXI Oriente
RUTA_CENTRO = (21.8818, -102.2916)     # Zona Centro / Alameda -> Salida SLP
RUTA_SUR = (21.8420, -102.2650)        # Sur / Ciudad Industrial -> Retoño
RUTA_JESUS_MARIA = (21.9610, -102.3430)# Jesús María -> Tercer Anillo -> UTR

# Generamos 20 escenarios variando corredor y desplazamiento del pasajero respecto a la ruta
# (17 escenarios dentro de <=400m y 3 escenarios fuera de rango >400m para probar rechazo)
def generar_20_escenarios():
    rutas_base = [
        ("Corredor Norte - Siglo XXI", RUTA_NORTE, UTR_DESTINO),
        ("Corredor Centro - Alameda", RUTA_CENTRO, UTR_DESTINO),
        ("Corredor Sur - Cd. Industrial", RUTA_SUR, UTR_DESTINO),
        ("Corredor Jesús María - Tercer Anillo", RUTA_JESUS_MARIA, UTR_DESTINO),
    ]
    
    escenarios = []
    np.random.seed(42)  # Semilla fija para reproducibilidad científica en el informe
    
    # Cacheamos las 4 trayectorias OSRM base para elegir puntos reales a distancias controladas
    trayectorias = {}
    for nombre, orig, dest in rutas_base:
        trayectorias[nombre] = obtener_ruta_osrm(orig, dest)
    
    for i in range(1, 21):
        nombre_ruta, orig, dest = rutas_base[(i - 1) % 4]
        nodos = trayectorias[nombre_ruta]
        # Elegimos un nodo intermedio entre el 15% y el 80% de la ruta
        nodo_ref = nodos[int(len(nodos) * np.random.uniform(0.15, 0.80))]
        
        if i <= 17:
            # Escenarios 1..17: Pasajero a distancia peatonal real (entre 25m y 360m)
            desplazamiento_grados = np.random.uniform(0.0002, 0.0028)
            tipo = "Compatible esperado (<=400m)"
        else:
            # Escenarios 18..20: Pasajero alejado (entre 900m y 3500m) para validar rechazo
            desplazamiento_grados = np.random.uniform(0.010, 0.030)
            tipo = "Fuera de rango esperado (>400m)"
            
        angulo = np.random.uniform(0, 2 * np.pi)
        pasajero_lat = nodo_ref[0] + desplazamiento_grados * np.cos(angulo)
        pasajero_lon = nodo_ref[1] + desplazamiento_grados * np.sin(angulo)
        
        escenarios.append({
            "id": i,
            "corredor": nombre_ruta,
            "tipo": tipo,
            "origen": orig,
            "destino": dest,
            "pasajero": (round(float(pasajero_lat), 6), round(float(pasajero_lon), 6))
        })
    return escenarios

# ==============================================================================
# 3. EJECUCIÓN DE BENCHMARKING Y CÁLCULO DE KPIs
# ==============================================================================
def ejecutar_evaluacion():
    print("🚀 Iniciando Batería de Evaluación Fase 5 (CRISP-DM): 20 Escenarios UTRide...\n")
    escenarios = generar_20_escenarios()
    resultados_csv = []
    
    compatibles_count = 0
    precision_aciertos = 0
    latencias = []
    ejecuciones_exitosas = 0

    for esc in escenarios:
        inicio = time.perf_counter()
        try:
            ruta_matriz = obtener_ruta_osrm(esc["origen"], esc["destino"])
            pasajero_arr = np.array([[esc["pasajero"][0], esc["pasajero"][1]]])
            matriz_D = construir_matriz_distancias(ruta_matriz, pasajero_arr)
            
            # Ejecución del modelo (Evolución Diferencial)
            nodo_de, dist_de = de_optimizar_parada(matriz_D, col_pasajero=0)
            latencia = time.perf_counter() - inicio
            
            # Valor exacto de referencia (Ground Truth mínimo de la matriz Haversine)
            dist_exacta_min = float(np.min(matriz_D[:, 0]))
            error_metros = abs(dist_de - dist_exacta_min)
            
            # Consideramos precisión exacta si DE converge dentro de <= 15m del óptimo global
            es_preciso = error_metros <= 15.0
            es_compatible = dist_de <= 400.0
            
            if es_compatible:
                compatibles_count += 1
            if es_preciso:
                precision_aciertos += 1
            latencias.append(latencia)
            ejecuciones_exitosas += 1
            
            estado_txt = "APROBADO" if es_compatible else "RECHAZADO (>400m)"
            print(f"Escenario #{esc['id']:02d} | {esc['corredor']:<32} | Caminata: {dist_de:7.2f} m | "
                  f"Error DE: {error_metros:5.2f} m | Latencia: {latencia:.4f}s | {estado_txt}")
            
            resultados_csv.append({
                "Escenario": esc["id"],
                "Corredor": esc["corredor"],
                "Pasajero_Lat": esc["pasajero"][0],
                "Pasajero_Lon": esc["pasajero"][1],
                "Nodo_DE": nodo_de,
                "Lat_Encuentro": round(float(ruta_matriz[nodo_de][0]), 6),
                "Lon_Encuentro": round(float(ruta_matriz[nodo_de][1]), 6),
                "Distancia_DE_m": round(dist_de, 2),
                "Distancia_Optima_m": round(dist_exacta_min, 2),
                "Error_Convergencia_m": round(error_metros, 2),
                "Compatible_400m": es_compatible,
                "Latencia_s": round(latencia, 4)
            })
        except Exception as e:
            print(f"❌ Error en escenario #{esc['id']}: {e}")

    # Cálculo de los 4 KPIs Oficiales del Proyecto
    kpi_compatibilidad = (compatibles_count / len(escenarios)) * 100
    kpi_precision = (precision_aciertos / len(escenarios)) * 100
    kpi_latencia_media = float(np.mean(latencias))
    kpi_cobertura = (ejecuciones_exitosas / len(escenarios)) * 100

    print("\n" + "="*75)
    print("📊 RESUMEN EJECUTIVO DE KPIs - FASE 5 EVALUACIÓN (CRISP-DM)")
    print("="*75)
    print(f"1. Compatibilidad de rutas (<= 400m):   {kpi_compatibilidad:6.2f}%  (Meta: >= 85.00%)")
    print(f"2. Precisión puntos de encuentro:       {kpi_precision:6.2f}%  (Meta: >= 90.00%)")
    print(f"3. Latencia media de respuesta:         {kpi_latencia_media:6.4f} s (Meta: <  3.0000 s)")
    print(f"4. Cobertura de pruebas ejecutadas:     {kpi_cobertura:6.2f}%  (Meta: == 100.00%)")
    print("="*75)

    # Exportar CSV para anexos del informe
    archivo_csv = "resultados_fase5_crisp_dm.csv"
    with open(archivo_csv, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=resultados_csv[0].keys())
        writer.writeheader()
        writer.writerows(resultados_csv)
    print(f"\n💾 Tabla exportada exitosamente a: {archivo_csv}")

    # Generar gráfica de resultados para el informe técnico
    generar_graficas(resultados_csv, kpi_latencia_media)

def generar_graficas(datos, latencia_media):
    ids = [d["Escenario"] for d in datos]
    distancias = [d["Distancia_DE_m"] for d in datos]
    tiempos = [d["Latencia_s"] for d in datos]
    colores = ["#2ecc71" if d <= 400 else "#e74c3c" for d in distancias]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 8))
    plt.subplots_adjust(hspace=0.4)

    # Gráfica 1: Distancia de caminata por escenario vs Umbral 400m
    ax1.bar(ids, distancias, color=colores, edgecolor="black", alpha=0.85)
    ax1.axhline(400, color="#c0392b", linestyle="--", linewidth=1.8, label="Umbral Peatonal Máximo (400 m)")
    ax1.set_title("Evaluación de Distancia de Caminata al Punto de Encuentro (20 Escenarios)", fontweight="bold")
    ax1.set_ylabel("Distancia (metros)")
    ax1.set_xticks(ids)
    ax1.legend()
    ax1.grid(axis="y", linestyle=":", alpha=0.6)

    # Gráfica 2: Latencia por escenario vs Meta < 3.0s
    ax2.plot(ids, tiempos, marker="o", color="#2980b9", linewidth=2, label="Latencia por petición (OSRM + Matriz + DE)")
    ax2.axhline(3.0, color="#e67e22", linestyle="--", linewidth=1.8, label="Límite Máximo KPI (3.0 s)")
    ax2.axhline(latencia_media, color="#27ae60", linestyle="-.", linewidth=1.5, label=f"Latencia Media ({latencia_media:.3f} s)")
    ax2.set_title("Rendimiento Computacional y Latencia de Respuesta", fontweight="bold")
    ax2.set_xlabel("Número de Escenario Simulado")
    ax2.set_ylabel("Tiempo (segundos)")
    ax2.set_xticks(ids)
    ax2.set_ylim(0, 3.5)
    ax2.legend()
    ax2.grid(True, linestyle=":", alpha=0.6)

    archivo_img = "grafica_kpis_fase5.png"
    plt.savefig(archivo_img, dpi=300, bbox_inches="tight")
    print(f"📈 Gráfica de KPIs guardada exitosamente en: {archivo_img}")

if __name__ == "__main__":
    ejecutar_evaluacion()