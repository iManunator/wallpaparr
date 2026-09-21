# Demo artwork attribution

Wallpaparr ships six 1920×1080 cinematic stills so first boot, CI, and `./scripts/verify.sh`
look like a real TV wallpaper suite **without Jellyfin** and **without scraping studio catalogs**.

Crops are 16:9 cover-crops of Wikimedia Commons originals. Re-vendor with
`scripts/vendor_demo_stills.py` if you need to refresh files.

| Demo title | File | Artwork | Creator / credit | License |
| --- | --- | --- | --- | --- |
| Northlight | `northlight.jpg` | [Aurora Australis From ISS](https://commons.wikimedia.org/wiki/File:Aurora_Australis_From_ISS.JPG) | ISS Expedition 23 crew / NASA | Public domain (US government work) |
| Harbor Season | `harbor-season.jpg` | [Copper Harbor Sunset, NARA 7717779](https://commons.wikimedia.org/wiki/File:Copper_Country_Trail_-_Copper_Harbor_Sunset_-_NARA_-_7717779.jpg) | U.S. National Archives (Tim Burke / finding aid) | Public domain |
| Glass Orchard | `glass-orchard.jpg` | [Kew Gardens Palm House, London — July 2009](https://commons.wikimedia.org/wiki/File:Kew_Gardens_Palm_House,_London_-_July_2009.jpg) | Diliff | [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0) |
| Signal Country | `signal-country.jpg` | [Sunset from Zabriskie Point, NARA 7717992](https://commons.wikimedia.org/wiki/File:Death_Valley_Scenic_Byway_-_Sunset_from_Zabriskie_Point_-_NARA_-_7717992.jpg) | U.S. National Archives / National Park Service | Public domain |
| Paper Atlas | `paper-atlas.jpg` | [Ortelius *Typus Orbis Terrarum*, 1570](https://commons.wikimedia.org/wiki/File:OrteliusWorldMap1570.jpg) | Abraham Ortelius; Library of Congress scan | Public domain |
| Night Relay | `night-relay.jpg` | [Black Marble Americas](https://commons.wikimedia.org/wiki/File:Black_Marble_Americas.jpg) | NASA Earth Observatory / Suomi NPP | Public domain (US government work) |

**Share-alike:** `glass-orchard.jpg` is a crop of Diliff’s photograph and remains **CC BY-SA 3.0**.
Keep this file, the Commons link, and the author name whenever you redistribute that still.

**Clearlogo:** `northlight-logo.png` is an original Wallpaparr demo wordmark (not a studio mark) so the
logo-vs-title path can be tested offline. Harbor Season, Glass Orchard, Signal Country, Paper Atlas,
and Night Relay have **no** logo file and fall back to title text.

Machine-readable copy: `catalog.json`. HTTP: `GET /api/demo/catalog`. `GET /api/media/logo/demo-jf-1`
serves the Northlight PNG; other demo ids 404 (text fallback).
