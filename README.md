# Plexamp Speed Dial — Home Assistant

HACS custom integration for [plexamp-speed-dial](https://github.com/pcatlin/plexamp-speed-dial).  
Lists your speed-dial favorites by **label** (with player/speaker/volume **description**) and plays them from Home Assistant.

## Requirements

- Home Assistant 2024.1+
- A running Plexamp Speed Dial instance reachable from HA (LAN URL)
- Plex linked in Speed Dial Setup (the API uses the server-stored token)

## Install (HACS)

1. HACS → Integrations → ⋮ → **Custom repositories**
2. URL: `https://github.com/pcatlin/plexamp-speed-dial-home-assistant`
3. Category: **Integration**
4. Download **Plexamp Speed Dial**, then restart Home Assistant
5. Settings → Devices & services → **Add integration** → **Plexamp Speed Dial**
6. Enter the base URL of your Speed Dial UI/API host, e.g. `http://192.168.1.50:3322`  
   (no trailing path; the integration calls `/api/v1/...`)

## What you get

- One **button** entity per speed dial (`button.plexamp_speed_dial_<label>`)
- Entity name = favorite **label**
- Entity extra attributes include `description` (player · speakers/AVR · volumes) and `favorite_id`
- Service `plexamp_speed_dial.play` with optional `label` or `favorite_id`

### Example service call

```yaml
service: plexamp_speed_dial.play
data:
  label: Evening jazz
```

Or by id:

```yaml
service: plexamp_speed_dial.play
data:
  favorite_id: 7
```

## API used

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/v1/speed-dial` | List favorites (`id`, `label`, `description`, …) |
| `POST` | `/api/v1/speed-dial/{id}/play` | Start that favorite |

Ensure your Speed Dial image includes the `description` field on list responses (recent builds).

## Manual install

Copy `custom_components/plexamp_speed_dial` into your HA `config/custom_components/` folder and restart.

## License

MIT
