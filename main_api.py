import os
import time
import requests
import numpy as np
from dotenv import load_dotenv
from supabase import create_client, Client
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

# 1. Cargamos credenciales de Supabase desde .env
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 2. Inicialización de FastAPI + Configuración CORS para Jony (App) y Dani (Web)
app = FastAPI(
    title="UTRide - Microservicio Espacial y Métricas de Ruta",
    description="Algoritmo Evolutivo Diferencial + OSRM + Supabase para puntos de encuentro (<= 400m) y distancias de tarifa",
    version="1.2.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite peticiones desde la App móvil y la Web
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Contratos de entrada (Pydantic)
class CoordenadaNominatim(BaseModel):
    lat: str
    lon: str

class SolicitudConBD(BaseModel):
    ruta_id: int
    pasajeros: List[CoordenadaNominatim]

# 4. Consulta de ruta fija en Supabase
def obtener_ruta_desde_supabase(ruta_id: int):
    respuesta = (
        supabase.table("rutas_conductores")
        .select("id, origen_lat, origen_lon, destino_lat, destino_lon, distancia_total_km")
        .eq("id", ruta_id)
        .execute()
    )
    if not respuesta.data:
        raise HTTPException(status_code=404, detail=f"Ruta con ID {ruta_id} no encontrada en Supabase.")
    
    registro = respuesta.data[0]
    origen = (float(registro["origen_lat"]), float(registro["origen_lon"]))
    destino = (float(registro["destino_lat"]), float(registro["destino_lon"]))
    distancia_guardada = registro.get("distancia_total_km")
    return origen, destino, distancia_guardada

# 5. Funciones geoespaciales, cálculo de kilometraje y Evolución Diferencial
def obtener_ruta_osrm(origen: tuple, destino: tuple) -> np.ndarray:
    coords_url = f"{origen[1]},{origen[0]};{destino[1]},{destino[0]}"
    url = f"http://router.project-osrm.org/route/v1/driving/{coords_url}?overview=full&geometries=geojson"
    datos = requests.get(url, timeout=10).json()
    if datos.get("code") != "Ok":
        raise HTTPException(status_code=400, detail="Error al trazar la ruta en OpenStreetMap.")
    puntos = datos["routes"][0]["geometry"]["coordinates"]
    return np.array([(lat, lon) for lon, lat in puntos])

def calcular_distancias_acumuladas_km(ruta_nodos: np.ndarray) -> np.ndarray:
    """Calcula vectorizadamente los km acumulados en cada nodo de la trayectoria OSRM."""
    if len(ruta_nodos) < 2:
        return np.zeros(len(ruta_nodos))
    R_km = 6371.0
    rad = np.radians(ruta_nodos)
    dlat = rad[1:, 0] - rad[:-1, 0]
    dlon = rad[1:, 1] - rad[:-1, 1]
    a = np.sin(dlat / 2.0)**2 + np.cos(rad[:-1, 0]) * np.cos(rad[1:, 0]) * np.sin(dlon / 2.0)**2
    segmentos_km = 2 * R_km * np.arcsin(np.sqrt(a))
    return np.concatenate(([0.0], np.cumsum(segmentos_km)))

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
    distancia_final = round(float(matriz_distancias[nodo_optimo, col_pasajero]), 2)
    return nodo_optimo, distancia_final

# 6. Endpoint productivo para Jony (App Móvil) y Jorge (Módulo de Tarifas)
@app.post("/api/v1/recomendar-parada-bd")
def recomendar_desde_supabase(solicitud: SolicitudConBD):
    inicio = time.perf_counter()

    origen, destino, distancia_guardada = obtener_ruta_desde_supabase(solicitud.ruta_id)
    coords_pasajeros = np.array([[float(p.lat), float(p.lon)] for p in solicitud.pasajeros])

    ruta_matriz = obtener_ruta_osrm(origen, destino)
    dist_acumulada_km = calcular_distancias_acumuladas_km(ruta_matriz)
    
    # Si aún no estaba guardada en Supabase, la calculamos y la guardamos automáticamente
    if distancia_guardada is None:
        distancia_total_km = round(float(dist_acumulada_km[-1]), 2)
        supabase.table("rutas_conductores").update(
            {"distancia_total_km": distancia_total_km}
        ).eq("id", solicitud.ruta_id).execute()
    else:
        distancia_total_km = round(float(distancia_guardada), 2)

    matriz_D = construir_matriz_distancias(ruta_matriz, coords_pasajeros)

    resultados = []
    for idx_p in range(len(solicitud.pasajeros)):
        nodo, dist_m = de_optimizar_parada(matriz_D, col_pasajero=idx_p)
        km_a_bordo = round(float(dist_acumulada_km[-1] - dist_acumulada_km[nodo]), 2)

        resultados.append({
            "pasajero_index": idx_p,
            "compatible": bool(dist_m <= 400.0),
            "punto_encuentro": {
                "lat": round(float(ruta_matriz[nodo][0]), 6),
                "lon": round(float(ruta_matriz[nodo][1]), 6)
            },
            "distancia_caminata_metros": dist_m,
            "distancia_viaje_pasajero_km": km_a_bordo,
            "nodo_ruta": nodo
        })

    latencia = round(time.perf_counter() - inicio, 4)
    return {
        "status": "ok",
        "ruta_id": solicitud.ruta_id,
        "distancia_total_ruta_km": distancia_total_km,
        "latencia_segundos": latencia,
        "resultados": resultados
    }