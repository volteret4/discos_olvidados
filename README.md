# discos_olvidados

Muestra los álbumes y artistas de la colección propia
(`musica_local.sqlite`) ordenados por cuánto hace que no se escuchan
según Last.fm (`lastfm_stats.db`), y si además están respaldados en
qBittorrent (vía `music.db` de `services/trasvase`) — para decidir qué
borrar con más confianza. Parte de
[repeat-one](https://github.com/volteret4/repeat-one).

## Cómo funciona

- **Álbumes** / **Artistas**: dos pestañas, cada una con una tabla
  ordenable (por defecto, lo más olvidado primero) y filtros por
  artista/álbum/género/sello, "nunca escuchado / alguna vez" y "en
  qBittorrent / no" (álbumes; en artistas se muestra el recuento
  respaldados/total).
- "En qBittorrent" se resuelve contra `music.db` de `services/trasvase`
  (`albums.collection=2`, la carpeta de backup en
  la carpeta de descargas de qBittorrent, ya escaneada a diario por ese
  servicio) — no consulta la API de qBittorrent en vivo.
- El cruce se calcula al arrancar el contenedor y se cachea en memoria —
  botón "Actualizar" para recalcular bajo demanda (por ejemplo, tras
  escuchar algo hoy mismo).
- Sin base de datos propia ni secretos — solo lee las tres SQLite que ya
  usan otros servicios del repo.

## Variables de entorno

```bash
LASTFM_DB=/data/lastfm_stats.db
MUSICA_LOCAL_DB=/musica_local.sqlite
TRASVASE_DB=/trasvase.db
PORT=5000
```

## Uso

```bash
pip install -r requirements.txt
python3 server.py          # web en 0.0.0.0:5000
```

## Tests

```bash
pip install -r requirements.txt pytest
pytest tests/ -v
```

Fixtures sintéticas de ambas bases (con un caso de acentos distintos
entre las dos y un álbum propio sin ningún scrobble, para probar el caso
"nunca escuchado").
