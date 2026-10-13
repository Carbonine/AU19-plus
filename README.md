# AU19+

AU19+ is a modded, offline copy of **AmongUs 2019**, a fan-made Among Us–style web game by Moana Games (Unity 2019.4 WebGL). It is not the official Among Us and is not affiliated with Innersloth.

It is built on top of the unmodded offline copy in the sibling `AmongUs2019` folder and adds its own features on top.

## Running it

The game must be served from `localhost`. Opening `index.html` directly won't work, and the game only runs on its allowed hosts.

Run it manually:

```bash
python3 -m http.server 8124 --bind 127.0.0.1
```

then open <http://localhost:8124/>.

## New in AU19+

### Name tags
- Every player shows their colour name above their bean, in the lobby and in matches.
- Your own tag shows your colour (e.g. "Orange") instead of "You".
- Tags hide when a player is dead, in a vent, or outside your vision, so they don't give away hidden players.
- **Impostor colouring:** in a match, impostors' names are red only if you are an impostor too, so impostors can see each other. As a crewmate, every name is white.
- In the lobby, all names are white.

### Keybinds
Matching regular Among Us, alongside the original keys:

| Action | Keys |
| --- | --- |
| Kill | E or **Q** |
| Vent | Space or **V** |
| Report | R |
| Sabotage map | **Tab** (press again to close) |
| Close sabotage map | **Esc** |

### Kill cooldown down to 0
- In Customize, the kill cooldown can now go down to **0** (in steps of 5; the original minimum was 20).
- Round starts and the time after meetings always use your full setting, instead of a fixed 10 seconds.
- With a 0 cooldown, no number shows on the kill button.

### Bug fixes
- **Vents:** you can now keep moving between connected vents. In the original game the arrows only appeared at the first vent, so you could move once and then got stuck.
- **Saved hat:** if your saved hat doesn't exist, it resets to no hat instead of breaking the game.

## Offline changes (shared with AmongUs2019)

- All files are served locally; no requests go to the original site.
- Unity analytics/telemetry requests are blocked.
- The "SendTraffic" redirect to other game sites is removed.
- The ad hooks are removed (interstitial and rewarded-video stubs).

## How the mods are applied

The game ships as compiled WebAssembly, so features are added by patching it:

- `tools/patch_code.py` rebuilds `Build/AmongUs2019_WebGL.wasm.code.unityweb` from the unmodified copy in `../AmongUs2019/Build/`, applying every AU19+ patch.
- `Build/AmongUs2019_WebGL.wasm.framework.unityweb` contains the telemetry, SendTraffic and ad changes.

To rebuild after changing the patcher:

```bash
python3 tools/patch_code.py
```

It needs Python 3 and the `AmongUs2019` folder next to `AU19+`.
