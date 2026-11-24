import requests

# 1. Simulamos la petición dinámica que enviará Jony desde la app móvil (ambos en formato Nominatim JSON)
peticion_app_jony = {
    "conductor_nominatim": {
        "display_name": "Fracc. Villas de Nuestra Señora de la Asunción, Ags.",
        "lat": "21.9145",
        "lon": "-102.2510"
    },
    "destino_nominatim": {
        "display_name": "Universidad Tecnológica El Retoño, El Llano, Ags.",
        "lat": "21.8565",
        "lon": "-102.1380"
    }
}

# Extraemos dinámicamente las coordenadas convirtiendo de texto a float
origen_conductor = (
    float(peticion_app_jony["conductor_nominatim"]["lat"]),
    float(peticion_app_jony["conductor_nominatim"]["lon"])
)
destino_viaje = (
    float(peticion_app_jony["destino_nominatim"]["lat"]),
    float(peticion_app_jony["destino_nominatim"]["lon"])
)
# 2. Función para consultar la API pública de OpenStreetMap (OSRM)
def obtener_ruta_osrm(origen, destino):
    # OSRM exige el orden: longitud,latitud (al revés de Google Maps / Nominatim)
    coords_url = f"{origen[1]},{origen[0]};{destino[1]},{destino[0]}"
    
    # Pedimos la ruta en coche ('driving') con geometría completa en formato GeoJSON
    url = f"http://router.project-osrm.org/route/v1/driving/{coords_url}?overview=full&geometries=geojson"
    
    respuesta = requests.get(url, timeout=10)
    datos = respuesta.json()
    
    if datos["code"] != "Ok":
        raise Exception("Error al calcular la ruta en OSRM")
    
    # Extraemos la lista de puntos [lon, lat] y los volteamos a (lat, lon) para mantener nuestro estándar
    puntos_geojson = datos["routes"][0]["geometry"]["coordinates"]
    ruta_limpia = [(lat, lon) for lon, lat in puntos_geojson]
    
    distancia_km = round(datos["routes"][0]["distance"] / 1000, 2)
    duracion_min = round(datos["routes"][0]["duration"] / 60, 1)
    
    return ruta_limpia, distancia_km, duracion_min

# 3. Ejecutamos la prueba

ruta_real, dist_km, tiempo_min = obtener_ruta_osrm(origen_conductor, destino_viaje)


print(f"✅ Ruta trazada con éxito desde OpenStreetMap!")
print(f"📏 Distancia total del trayecto: {dist_km} km")
print(f"⏱️ Tiempo estimado en auto: {tiempo_min} minutos")
print(f"📍 Total de nodos (puntos) generados en la ruta: {len(ruta_real)}")
print("\nPrimeros 5 nodos de la ruta real (lat, lon):")
for i, nodo in enumerate(ruta_real[:5]):
    print(f"  Nodo {i}: {nodo}")