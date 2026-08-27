import pytest

import server as server_mod


@pytest.fixture
def client(patched_staleness):
    server_mod.app.config["TESTING"] = True
    with server_mod.app.test_client() as c:
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json() == {"ok": True}


def test_albums_default_sort_never_listened_first(client):
    r = client.get("/api/albums")
    data = r.get_json()
    assert data["total"] == 3
    # días_since desc por defecto -- "nunca" (None) cuenta como infinito,
    # así que debe salir primero.
    assert data["items"][0]["album"] == "Nunca Escuchado"
    assert data["items"][0]["days_since"] is None


def test_albums_filter_by_genre(client):
    r = client.get("/api/albums?genre=IDM")
    data = r.get_json()
    assert data["total"] == 1
    assert data["items"][0]["album"] == "Geogaddi"


def test_albums_filter_never_listened_yes(client):
    r = client.get("/api/albums?never_listened=yes")
    data = r.get_json()
    assert data["total"] == 1
    assert data["items"][0]["album"] == "Nunca Escuchado"


def test_albums_filter_qbittorrent_yes(client):
    r = client.get("/api/albums?qbittorrent=yes")
    data = r.get_json()
    assert data["total"] == 1
    assert data["items"][0]["album"] == "Homogenic"


def test_albums_filter_qbittorrent_no(client):
    r = client.get("/api/albums?qbittorrent=no")
    data = r.get_json()
    assert data["total"] == 2
    assert {it["album"] for it in data["items"]} == {"Geogaddi", "Nunca Escuchado"}


def test_artists_backed_up_count(client):
    r = client.get("/api/artists?artist=Björk")
    data = r.get_json()
    assert data["items"][0]["backed_up_count"] == 1
    assert data["items"][0]["album_count"] == 1


def test_albums_filter_never_listened_no(client):
    r = client.get("/api/albums?never_listened=no")
    data = r.get_json()
    assert data["total"] == 2
    assert all(it["days_since"] is not None for it in data["items"])


def test_albums_sort_by_artist_asc(client):
    r = client.get("/api/albums?sort=artist&dir=asc")
    data = r.get_json()
    artists = [it["artist"] for it in data["items"]]
    assert artists == sorted(artists, key=str.lower)


def test_albums_click_to_filter_by_label(client):
    r = client.get("/api/albums?label=Warp Records")
    data = r.get_json()
    assert data["total"] == 1
    assert data["items"][0]["label"] == "Warp Records"


def test_artists_default_sort(client):
    r = client.get("/api/artists")
    data = r.get_json()
    assert data["total"] == 3
    assert data["items"][0]["artist"] == "Artista Sin Escuchas"
    assert data["items"][0]["days_since"] is None


def test_filters_meta(client):
    r = client.get("/api/filters/meta")
    data = r.get_json()
    assert "IDM" in data["genres"]
    assert "Warp Records" in data["labels"]


def test_refresh_endpoint(client):
    r = client.post("/api/refresh")
    data = r.get_json()
    assert data["ok"] is True
    assert data["computed_at"] is not None

    status = client.get("/api/status").get_json()
    assert status["computed_at"] == data["computed_at"]


def test_pagination(client):
    r = client.get("/api/albums?per_page=2&page=1")
    data = r.get_json()
    assert len(data["items"]) == 2
    assert data["total"] == 3
    assert data["per_page"] == 2

    r2 = client.get("/api/albums?per_page=2&page=2")
    data2 = r2.get_json()
    assert len(data2["items"]) == 1
