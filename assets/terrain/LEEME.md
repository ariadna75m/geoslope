# Relieve integrado de Century Mine

Modelo de superficie Copernicus GLO-30, resolución aproximada de 30 m. Incluye la malla compacta `century_surface.npz`, el GeoTIFF original recortado, metadatos, XML de origen, huellas de adquisición y licencia. La malla compacta conserva las coordenadas publicadas en el CSV de la entrega de relieve, redondeadas a ocho decimales. No se interpola ni se altera la cota.

Usa Mostrar relieve de Century Mine en Vista espacial. El plano 2D conserva longitud/latitud WGS84; la vista 3D usa UTM 54S (EPSG:32754). Cotas en metros EGM2008 (EPSG:3855). La exageración 1×/3×/5× cambia únicamente la proporción visual.

La superficie no se presenta como un levantamiento fino del talud ni como una captura exacta de 2014. La referencia local de los prismas sigue sin validar: ambos conjuntos se muestran como vistas alternativas.

La malla se verifica mediante SHA-256 antes de cargar. `metadata.json` conserva las estadísticas de las máscaras originales EDM, FLM, WBM y HEM y los enlaces de origen. HEM representa error aleatorio estimado, no una validación topográfica de campo.

Fuente: https://registry.opendata.aws/copernicus-dem/
Documentación: https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM

produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved
