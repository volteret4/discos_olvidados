# discos_olvidados

## Arquitectura

- `normalize.py` — copia literal de `services/lastfm_explorer/normalize.py`
  (NFD sin acentos, minúsculas) — se aplica en Python a ambos lados del
  cruce en vez de fiarse del `name_normalized` ya precalculado en
  `lastfm_stats.db`, que usa una normalización distinta (sin quitar
  acentos) y por eso no sirve para cruzar con nombres de
  `musica_local.sqlite`.
- `db.py` — `get_lastfm_conn()`/`get_musica_local_conn()`/
  `get_trasvase_conn()`, mismo patrón `:ro` + `immutable=1` que
  `services/lastfm_explorer/db.py`.
- `staleness.py` — el cruce en sí. Sin base de datos propia: carga
  `lastfm_stats.db` (artistas + `MAX(ts)` por artista/álbum agregado con
  `GROUP BY`) y `music.db` de `services/trasvase` (`albums.collection=2`
  = `/ruta/al/nas/lidarr/torrents_backup` en pepecono, ya escaneado a diario
  por ese servicio) en diccionarios/sets de Python, recorre
  `musica_local.sqlite` y busca cada nombre propio normalizado en esos
  índices. Resultado cacheado en memoria de proceso (`_CACHE`),
  recalculado al arrancar y bajo demanda vía `POST /api/refresh` — no en
  cada petición de búsqueda/orden/filtro (evita recorrer ~90k filas en
  cada clic).
- **Por qué reutilizar `trasvase/music.db` en vez de consultar
  qBittorrent en vivo**: `trasvase` ya escanea a diario el directorio de
  backup de qBittorrent/Lidarr y lo indexa por artista+álbum — reusar esa
  tabla evita una segunda fuente de verdad (y una dependencia de red a
  la API de qBittorrent) para una pregunta que ya tiene respuesta ahí.
  Solo cuentan las filas con `collection=2` (backup) — `collection=1` es
  la biblioteca principal de `trasvase`, no qBittorrent.
- `server.py` — Flask; filtra/ordena/pagina en Python sobre las listas ya
  calculadas (no hay SQL en las rutas — los datos ya viven en memoria).
  Orden por defecto: `days_since` descendente, con "nunca escuchado"
  (`None`) tratado como infinito — sale siempre primero.

## Limitación conocida: falsos "nunca escuchado"

Si el nombre del artista/álbum en `musica_local.sqlite` no coincide
(tras normalizar) con ningún nombre de `lastfm_stats.db` -- typos,
"The Beatles" vs "Beatles", variantes de un álbum, etc. -- sale como
"nunca escuchado" aunque sí se haya escuchado bajo otro nombre. No se
intenta resolver con heurísticas adicionales (fuzzy matching, etc.) a
propósito -- si en la práctica hay muchos falsos positivos, mejor
revisarlo con el usuario antes de complicar el matching.

## Por qué no hace falta DB propia

A diferencia de `discos_pendientes`/`yt_clips` (que cachean resultados
de llamadas externas caras -- Airsonic/qBittorrent/Last.fm en vivo,
descargas de YouTube), aquí las dos fuentes ya son SQLite locales y el
cruce completo es barato (agregados `GROUP BY` + diccionarios en
Python, sin red) -- no hay nada que merezca persistirse en un archivo
propio, un caché en memoria de proceso basta.
