import math
import numpy as np

# 1. Función matemática para calcular distancia real en metros (Haversine)
def distancia_haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # Radio de la Tierra en metros
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# 2. Simulamos la ruta fija del conductor (Nodos de Aguascalientes hacia la UTR)
# Formato: lista de tuplas (latitud, longitud)
ruta_conductor = [
    (21.8850, -102.2600),  # Nodo 0: Punto de partida en Ags
    (21.8835, -102.2520),  # Nodo 1
    (21.8820, -102.2440),  # Nodo 2
    (21.8805, -102.2350),  # Nodo 3: Zona cercana al pasajero
    (21.8790, -102.2250),  # Nodo 4
    (21.8775, -102.2100),  # Nodo 5
    (21.8760, -102.1850)   # Nodo 6: Llegada cercana a UTR
]

# 3. Simulamos el JSON que enviará Jony desde Nominatim para el pasajero
json_nominatim_pasajero = {
    "display_name": "Parada solicitada por estudiante, Ags.",
    "lat": "21.8812",
    "lon": "-102.2345"
}

# Extraemos y convertimos a flotante
lat_pasajero = float(json_nominatim_pasajero["lat"])
lon_pasajero = float(json_nominatim_pasajero["lon"])

# 4. Construcción de la Matriz de Puntos / Distancias
# Filas = Nodos de la ruta del conductor | Columnas = Pasajeros (por ahora 1)
num_nodos = len(ruta_conductor)
matriz_distancias = np.zeros((num_nodos, 1))

for i, (lat_nodo, lon_nodo) in enumerate(ruta_conductor):
    dist = distancia_haversine(lat_nodo, lon_nodo, lat_pasajero, lon_pasajero)
    matriz_distancias[i, 0] = round(dist, 2)

# Mostramos resultados
print("Matriz de distancias (metros) del pasajero hacia cada nodo de la ruta:")
for i, fila in enumerate(matriz_distancias):
    estado = "✅ VÁLIDO (<= 400m)" if fila[0] <= 400 else "❌ MUY LEJOS"
    print(f"Nodo {i} {ruta_conductor[i]} -> {fila[0]} m | {estado}")