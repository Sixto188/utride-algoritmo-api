import time
import requests
import numpy as np

# 1. Trazado automático de ruta fija del conductor (OSRM)
def obtener_ruta_osrm(origen, destino):
    coords_url = f"{origen[1]},{origen[0]};{destino[1]},{destino[0]}"
    url = f"http://router.project-osrm.org/route/v1/driving/{coords_url}?overview=full&geometries=geojson"
    datos = requests.get(url, timeout=10).json()
    puntos = datos["routes"][0]["geometry"]["coordinates"]
    return np.array([(lat, lon) for lon, lat in puntos])  # Lo devolvemos como matriz NumPy (N, 2)

# 2. Construcción vectorizada de la Matriz de Distancias (N nodos x M pasajeros)
def construir_matriz_distancias(ruta_nodos, pasajeros_coords):
    R = 6371000.0  # Radio de la Tierra en metros
    
    # Convertimos grados a radianes y damos forma para broadcasting matricial:
    # ruta_rad tendrá forma (N, 1, 2) y pasajeros_rad tendrá forma (1, M, 2)
    ruta_rad = np.radians(ruta_nodos)[:, np.newaxis, :]
    pasajeros_rad = np.radians(pasajeros_coords)[np.newaxis, :, :]
    
    dlat = pasajeros_rad[:, :, 0] - ruta_rad[:, :, 0]
    dlon = pasajeros_rad[:, :, 1] - ruta_rad[:, :, 1]
    
    lat1 = ruta_rad[:, :, 0]
    lat2 = pasajeros_rad[:, :, 0]
    
    a = np.sin(dlat / 2.0)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0)**2
    matriz_metros = 2 * R * np.arcsin(np.sqrt(a))
    
    return matriz_metros  # Matriz de tamaño (N nodos, M pasajeros)

# 3. Algoritmo Evolutivo Diferencial operando sobre una columna de la Matriz
def de_optimizar_parada(matriz_distancias, col_pasajero, tam_pob=20, gens=40, F=0.7, CR=0.8):
    num_nodos = matriz_distancias.shape[0]
    lim_inf, lim_sup = 0, num_nodos - 1
    
    # Función objetivo ultrarrápida: solo lee la distancia precalculada en la matriz
    def fitness_func(x):
        idx = int(np.clip(round(x), lim_inf, lim_sup))
        dist = matriz_distancias[idx, col_pasajero]
        penalizacion = 0.0 if dist <= 400.0 else (dist - 400.0) * 10.0
        return dist + penalizacion

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
    distancia_final = round(float(matriz_distancias[nodo_optimo, col_pasajero]), 2)
    
    return nodo_optimo, distancia_final

# --- SIMULACIÓN DE ESCENARIO MULTI-PASAJERO ---
inicio_tiempo = time.perf_counter()

# Ruta fija guardada en BD (Origen -> UTR)
origen_chofer = (21.9145, -102.2510)
destino_utr = (21.8565, -102.1380)
ruta_matriz = obtener_ruta_osrm(origen_chofer, destino_utr)

# 3 pasajeros enviando su ubicación desde Nominatim al mismo tiempo
pasajeros_solicitudes = np.array([
    [21.8980, -102.2380],  # Pasajero 1: cerca de la ruta
    [21.8740, -102.1950],  # Pasajero 2: cerca de la ruta
    [21.8200, -102.2900]   # Pasajero 3: muy lejos (debe marcar NO compatible)
])

# Construimos la Matriz de Puntos (N nodos x 3 pasajeros)
matriz_D = construir_matriz_distancias(ruta_matriz, pasajeros_solicitudes)

print(f"📊 Dimensión de la Matriz de Puntos: {matriz_D.shape[0]} nodos x {matriz_D.shape[1]} pasajeros\n")

# Ejecutamos DE para cada pasajero
for p in range(pasajeros_solicitudes.shape[0]):
    nodo, dist = de_optimizar_parada(matriz_D, col_pasajero=p)
    coord = tuple(np.round(ruta_matriz[nodo], 6))
    compatible = dist <= 400.0
    estado = "✅ COMPATIBLE" if compatible else "❌ RECHAZADO (>400m)"
    print(f"Pasajero {p+1}: Nodo #{nodo} {coord} | Caminata: {dist} m | {estado}")

latencia_total = round(time.perf_counter() - inicio_tiempo, 4)
print(f"\n⏱️ Latencia total (OSRM + Matriz + DE para 3 pasajeros): {latencia_total} s (Meta KPI: < 3.0 s)")