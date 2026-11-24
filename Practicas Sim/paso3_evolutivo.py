import math
import requests
import numpy as np

# --- FUNCIONES DE APOYO (PASOS 1 Y 2) ---
def distancia_haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

def obtener_ruta_osrm(origen, destino):
    coords_url = f"{origen[1]},{origen[0]};{destino[1]},{destino[0]}"
    url = f"http://router.project-osrm.org/route/v1/driving/{coords_url}?overview=full&geometries=geojson"
    datos = requests.get(url, timeout=10).json()
    puntos = datos["routes"][0]["geometry"]["coordinates"]
    return [(lat, lon) for lon, lat in puntos]

# --- PASO 3: ALGORITMO EVOLUTIVO DIFERENCIAL (DE) ---

# 1. Punto de encuentro mas optimo para el pasajero
def funcion_objetivo(indice_continuo, ruta_conductor, coord_pasajero):
    # Convertimos el número continuo a un índice entero válido dentro de la ruta
    idx = int(np.clip(round(indice_continuo), 0, len(ruta_conductor) - 1))
    lat_nodo, lon_nodo = ruta_conductor[idx] #obtiene las coordenadas del nodo en la ruta del conductor
    
    distancia = distancia_haversine(lat_nodo, lon_nodo, coord_pasajero[0], coord_pasajero[1]) #Mide que tan lejos esta el putno de encuentro
    
    # Penalización: si supera los 400m del KPI, sumamos un castigo fuerte
    penalizacion = 0 if distancia <= 400 else (distancia - 400) * 10
    return distancia + penalizacion

# 2. Motor principal de Evolución Diferencial
def evolucion_diferencial_parada(ruta_conductor, coord_pasajero, tam_poblacion=20, generaciones=40, F=0.7, CR=0.8):
    num_nodos = len(ruta_conductor)
    limite_inferior, limite_superior = 0, num_nodos - 1
    
    # Inicialización aleatoria de la población de índices candidatos
    poblacion = np.random.uniform(limite_inferior, limite_superior, tam_poblacion)
    fitness = np.array([funcion_objetivo(ind, ruta_conductor, coord_pasajero) for ind in poblacion])
    
    # Ciclo evolutivo
    for gen in range(generaciones):
        for i in range(tam_poblacion):
            # Selección de 3 individuos distintos al actual (r1, r2, r3)
            indices = [idx for idx in range(tam_poblacion) if idx != i]
            r1, r2, r3 = np.random.choice(indices, 3, replace=False)
            
            # Mutación: v = x_r1 + F * (x_r2 - x_r3)
            mutante = poblacion[r1] + F * (poblacion[r2] - poblacion[r3])
            mutante = np.clip(mutante, limite_inferior, limite_superior)
            
            # Cruza binomial
            prueba = mutante if np.random.rand() < CR else poblacion[i]
            
            # Selección (sobrevive el de menor costo)
            fitness_prueba = funcion_objetivo(prueba, ruta_conductor, coord_pasajero)
            if fitness_prueba < fitness[i]:
                poblacion[i] = prueba
                fitness[i] = fitness_prueba
                
    # Extraemos al mejor individuo de toda la evolución
    mejor_idx_pob = np.argmin(fitness)
    mejor_nodo_ruta = int(np.clip(round(poblacion[mejor_idx_pob]), 0, limite_superior))
    coord_optima = ruta_conductor[mejor_nodo_ruta]
    dist_final = distancia_haversine(coord_optima[0], coord_optima[1], coord_pasajero[0], coord_pasajero[1])
    
    return mejor_nodo_ruta, coord_optima, round(dist_final, 2)

# --- PRUEBA INTEGRADA ---
origen_conductor = (21.9145, -102.2510)   # Ruta fija de BD (VNSA)
destino_conductor = (21.8565, -102.1380)  # Destino (UTR)
pasajero_efimero = (21.8825, -102.2120)   # Petición temporal de Jony

ruta_fija = obtener_ruta_osrm(origen_conductor, destino_conductor)
nodo_ganador, punto_encuentro, metros_caminata = evolucion_diferencial_parada(ruta_fija, pasajero_efimero)

print(f"🛣️  Total de nodos analizados en la ruta fija: {len(ruta_fija)}")
print(f"🧬 Nodo óptimo encontrado por DE: #{nodo_ganador} -> {punto_encuentro}")
print(f"🚶 Distancia que caminará el pasajero: {metros_caminata} m")
print(f"📋 Estado KPI (<= 400m): {'✅ COMPATIBLE' if metros_caminata <= 400 else '❌ FUERA DE RANGO'}")