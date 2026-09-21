from __future__ import annotations

from app.omdb import fetch_omdb_fields


class FakeClient:
    def __init__(self, payload):
        self.payload = payload
        self.calls = 0

    def get_json(self, url, headers=None, params=None):
        self.calls += 1
        return self.payload


def test_missing_imdb_id_or_key_returns_empty():
    client = FakeClient({"Response": "True"})
    assert fetch_omdb_fields("", "key", client) == {}
    assert fetch_omdb_fields("tt1", "", client) == {}
    assert client.calls == 0


def test_omdb_not_found_returns_empty():
    client = FakeClient({"Response": "False", "Error": "Incorrect IMDb ID."})
    assert fetch_omdb_fields("tt0000000", "key", client) == {}


def test_maps_ratings_awards_and_box_office():
    client = FakeClient(
        {
            "Response": "True",
            "Ratings": [
                {"Source": "Internet Movie Database", "Value": "8.4/10"},
                {"Source": "Rotten Tomatoes", "Value": "92%"},
                {"Source": "Metacritic", "Value": "81/100"},
            ],
            "imdbRating": "8.4",
            "Awards": "Won 1 Oscar",
            "BoxOffice": "$100,000,000",
        }
    )
    fields = fetch_omdb_fields("tt1234567", "key", client)
    assert fields == {
        "rotten_tomatoes": 92,
        "metacritic": 81,
        "imdb_rating": 8.4,
        "awards": "Won 1 Oscar",
        "box_office": "$100,000,000",
    }


def test_na_fields_are_omitted():
    client = FakeClient(
        {
            "Response": "True",
            "Ratings": [],
            "imdbRating": "N/A",
            "Awards": "N/A",
            "BoxOffice": "N/A",
        }
    )
    assert fetch_omdb_fields("tt7654321", "key", client) == {}


def test_result_is_cached_and_does_not_refetch():
    client = FakeClient({"Response": "True", "imdbRating": "7.0"})
    first = fetch_omdb_fields("tt5555555", "key", client)
    second = fetch_omdb_fields("tt5555555", "key", client)
    assert first == second == {"imdb_rating": 7.0}
    assert client.calls == 1
