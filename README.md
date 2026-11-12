# Motor Geoespacial y Algoritmo de Sugerencia de Puntos de Encuentro — UTRide 🚗📍

Prototipo algorítmico y microservicio API REST desarrollado para el proyecto de estadías del programa de **Ingeniería en Ciencia de Datos** de la **Universidad Tecnológica El Retoño (UTR)**.

Este componente procesa el vector de puntos (polilínea) que define la ruta fija preestablecida de un vehículo conductor y proyecta ortogonalmente la posición de un estudiante pasajero, sugiriendo los **puntos de encuentro más viables** priorizando la menor distancia a pie y manteniendo una **tolerancia de desvío nula (0 metros)** para el vehículo.

---

## 🛠️ Tecnologías y Librerías

* **Lenguaje:** Python 3.10+
* **Procesamiento Geoespacial:** `Shapely`, `NumPy` (100% código abierto / Open Source)
* **Framework Web / API:** `FastAPI`, `Uvicorn`
* **Benchmarking & Visualización:** `Matplotlib`

---

## 📁 Estructura del Proyecto

```text
Estadias Algoritmo/
├── main.py                     # Microservicio API REST (Endpoints con FastAPI)
├── route_geometry.py           # Núcleo matemático (Haversine y proyección ortogonal)
├── ranking_engine.py           # Motor de ranking multicriterio (Match Score %)
├── generate_test_scenarios.py  # Generador del dataset sintético (20 escenarios)
├── evaluate_scenarios.py       # Script de benchmarking y generación de gráficas/CSV
├── scenarios_dataset.json      # Dataset de 20 escenarios de prueba geoespaciales
├── requirements.txt            # Dependencias del proyecto
└── README.md                   # Documentación principal del repositorio