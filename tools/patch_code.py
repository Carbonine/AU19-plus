import os
import struct
import sys
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME = "AmongUs2019_WebGL.wasm.code.unityweb"
SRC = os.path.join(os.path.dirname(ROOT), "AmongUs2019", "Build", NAME)
DST = os.path.join(ROOT, "Build", NAME)

F_STOP_COROUTINE = 51306
F_KILL_TIMER_MOVE_NEXT = 30861
OFF_KILL_COOLDOWN_TEXT = 72
OFF_KILL_COOLDOWN = 520
F_START_NEW_ROUND = 30672
F_START_KILL_TIMER = 30673
F_PREFS_GET_KILL_COOLDOWN = 30674
ROUND_START_KILL_COOLDOWN = 10
F_ON_CHANGE_KILL_COOLDOWN = 33508
KILL_COOLDOWN_OLD_MIN = 20
KILL_COOLDOWN_MIN = 0
F_GAME_UPDATE = 30680
F_CLOSE_SABOTAGE = 30694
F_SHOW_SABOTAGE = 30793
F_GET_ACTIVE_SELF = 48892
F_GET_KEY_DOWN = 64927
OFF_SABOTAGE_DIALOG = 376
KEY_TAB = 9
KEY_ESCAPE = 27
KEY_SPACE = 32
KEY_E = 101
KEY_Q = 113
KEY_V = 118
F_ARROW_ON_MOUSE_DOWN = 30917
F_SHOW_VENT_DIRECTIONS = 40773
F_START_COROUTINE = 51301
F_REMOVE_DIRECTIONS = 40774
F_SHOW_VENT_DIRECTIONS_MOVE_NEXT = 40776
OFF_ARROW_FROM_VENT = 12
OFF_ARROW_TO_VENT = 16
OFF_ENTERING_VENT = 206
OFF_COROUTINE_STATE = 8
F_SET_TEXT = 29821
F_SET_COLOR = 29837
F_UPDATE = 30941
F_GET_RENDERER = 32277
F_GET_GAMEOBJECT = 48641
F_SET_ACTIVE = 48891
F_GET_ENABLED = 51756
F_SET_ENABLED = 51757
F_SPRITE_GET_COLOR = 52491

OFF_USERNAME_TEXT = 36
OFF_SRENDERER = 32
OFF_GAME_CONTROLLER = 52
OFF_IS_DEAD = 56
OFF_IS_IMPOSTOR = 80
OFF_COLOR_NAME = 148
OFF_VENTING = 152
OFF_INSIDE_VENT = 153
OFF_STATIC_FIELDS = 92
PLAYER_TYPEINFO = 3617732
STACK_PTR = 7


def uleb(n):
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def sleb(n):
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if (n == 0 and not b & 0x40) or (n == -1 and b & 0x40):
            out.append(b)
            return bytes(out)
        out.append(b | 0x80)


def read_uleb(b, p):
    r = s = 0
    while True:
        x = b[p]
        p += 1
        r |= (x & 0x7F) << s
        s += 7
        if x < 0x80:
            return r, p


def local_get(i): return b"\x20" + uleb(i)
def local_set(i): return b"\x21" + uleb(i)
def global_get(i): return b"\x23" + uleb(i)
def global_set(i): return b"\x24" + uleb(i)
def i32_const(v): return b"\x41" + sleb(v)
def f32_const(v): return b"\x43" + struct.pack("<f", v)
def i32_load(off): return b"\x28\x02" + uleb(off)
def i32_load8_u(off): return b"\x2d\x00" + uleb(off)
def f32_store(off): return b"\x38\x02" + uleb(off)
def call(f): return b"\x10" + uleb(f)


I32_ADD = b"\x6a"
I32_AND = b"\x71"
I32_OR = b"\x72"
I32_EQZ = b"\x45"
I32_NE = b"\x47"
I32_EQ = b"\x46"
I32_LT_S = b"\x48"
I32_GT_S = b"\x4a"
IF_I32 = b"\x04\x7f"
ELSE = b"\x05"
RETURN = b"\x0f"


def load_local_player(dst):
    return (
        i32_const(0) + i32_load(PLAYER_TYPEINFO) + local_set(dst)
        + local_get(dst) + IF_VOID + local_get(dst) + i32_load(OFF_STATIC_FIELDS) + local_set(dst) + END
        + local_get(dst) + IF_VOID + local_get(dst) + i32_load(0) + local_set(dst) + END
    )


def arrow_guard(nparams, first_local):
    player = first_local
    return (
        load_local_player(player)
        + local_get(player) + IF_VOID
        + local_get(player) + i32_load8_u(OFF_INSIDE_VENT) + local_set(player)
        + END
        + local_get(player) + I32_EQZ + IF_VOID
        + local_get(0) + i32_load(OFF_ARROW_FROM_VENT) + i32_const(0) + call(F_REMOVE_DIRECTIONS)
        + RETURN
        + END
    )


def vent_directions_guard(nparams, first_local):
    player = first_local
    return (
        local_get(0) + i32_load(OFF_COROUTINE_STATE) + i32_const(1) + I32_EQ + IF_VOID
        + load_local_player(player)
        + local_get(player) + IF_VOID
        + local_get(player) + i32_load8_u(OFF_VENTING)
        + local_get(player) + i32_load8_u(OFF_INSIDE_VENT)
        + local_get(player) + i32_load8_u(OFF_ENTERING_VENT) + I32_OR
        + I32_AND + local_set(player)
        + END
        + local_get(player) + I32_EQZ + IF_VOID
        + local_get(0) + i32_const(-1) + b"\x36\x02" + uleb(OFF_COROUTINE_STATE)
        + i32_const(0) + RETURN
        + END
        + END
    )
SELECT = b"\x1b"
IF_VOID = b"\x04\x40"
END = b"\x0b"


def name_tags(nparams, first_local):
    this = local_get(0)
    lbl = first_local
    sp = first_local + 1
    red = first_local + 2
    local_impostor = (
        i32_const(0) + i32_load(PLAYER_TYPEINFO) + local_set(red)
        + local_get(red) + IF_VOID + local_get(red) + i32_load(OFF_STATIC_FIELDS) + local_set(red) + END
        + local_get(red) + IF_VOID + local_get(red) + i32_load(0) + local_set(red) + END
        + local_get(red) + IF_VOID + local_get(red) + i32_load8_u(OFF_IS_IMPOSTOR) + local_set(red) + END
    )
    show_red = (
        local_impostor
        + local_get(red)
        + this + i32_load8_u(OFF_IS_IMPOSTOR) + I32_AND
        + this + i32_load(OFF_GAME_CONTROLLER) + i32_const(0) + I32_NE + I32_AND
        + local_set(red)
    )
    green_blue = f32_const(0.0) + f32_const(1.0) + local_get(red) + SELECT
    set_name = (
        this + i32_load(OFF_COLOR_NAME) + IF_VOID
        + local_get(lbl) + this + i32_load(OFF_COLOR_NAME) + i32_const(0) + call(F_SET_TEXT)
        + END
    )
    hidden = (
        this + i32_load8_u(OFF_IS_DEAD)
        + this + i32_load8_u(OFF_VENTING) + I32_OR
        + this + i32_load8_u(OFF_INSIDE_VENT) + I32_OR
    )
    code = (
        this + i32_load(OFF_USERNAME_TEXT) + local_set(lbl)
        + local_get(lbl) + IF_VOID
        + local_get(lbl) + i32_const(0) + call(F_GET_GAMEOBJECT)
        + hidden + I32_EQZ + i32_const(0) + call(F_SET_ACTIVE)
        + local_get(lbl) + i32_const(0) + call(F_GET_RENDERER)
        + this + i32_load(OFF_SRENDERER) + i32_const(0) + call(F_GET_ENABLED)
        + i32_const(0) + call(F_SET_ENABLED)
        + set_name
        + show_red
        + global_get(STACK_PTR) + local_set(sp)
        + global_get(STACK_PTR) + i32_const(16) + I32_ADD + global_set(STACK_PTR)
        + local_get(sp) + this + i32_load(OFF_SRENDERER) + i32_const(0) + call(F_SPRITE_GET_COLOR)
        + local_get(sp) + f32_const(1.0) + f32_store(0)
        + local_get(sp) + green_blue + f32_store(4)
        + local_get(sp) + green_blue + f32_store(8)
        + local_get(lbl) + local_get(sp) + i32_const(0) + call(F_SET_COLOR)
        + local_get(sp) + global_set(STACK_PTR)
        + END
    )
    return code


def vent_arrows(body):
    to_vent = local_get(0) + i32_load(OFF_ARROW_TO_VENT)
    old = to_vent + i32_const(0) + call(F_SHOW_VENT_DIRECTIONS) + b"\x1a"
    new = to_vent + to_vent + i32_const(0) + call(F_SHOW_VENT_DIRECTIONS) + i32_const(0) + call(F_START_COROUTINE) + b"\x1a"
    if body.count(old) != 1:
        sys.exit("vent arrow pattern not found exactly once")
    return body.replace(old, new)


def key_down(key):
    return i32_const(key) + i32_const(0) + call(F_GET_KEY_DOWN)


def replace_once(body, old, new, what):
    if body.count(old) != 1:
        sys.exit(what + " pattern not found exactly once")
    return body.replace(old, new)


def keybinds_top(nparams, first_local):
    this = local_get(0)
    closed = first_local
    return (
        this + i32_load(OFF_SABOTAGE_DIALOG) + i32_const(0) + call(F_GET_ACTIVE_SELF) + IF_VOID
        + key_down(KEY_ESCAPE) + key_down(KEY_TAB) + I32_OR + IF_VOID
        + this + i32_const(0) + call(F_CLOSE_SABOTAGE)
        + i32_const(1) + local_set(closed)
        + END
        + END
    )


def keybinds_body(body, closed):
    this = local_get(0)
    open_sabotage = (
        key_down(KEY_TAB) + local_get(closed) + I32_EQZ + I32_AND + IF_VOID
        + this + i32_const(0) + call(F_SHOW_SABOTAGE)
        + END
    )
    body = replace_once(body, key_down(KEY_E), key_down(KEY_E) + key_down(KEY_Q) + I32_OR, "kill key")
    body = replace_once(body, key_down(KEY_SPACE), open_sabotage + key_down(KEY_SPACE) + key_down(KEY_V) + I32_OR, "vent key")
    return body


def kill_cooldown_min(body):
    old = i32_const(KILL_COOLDOWN_OLD_MIN) + I32_LT_S + IF_I32 + i32_const(KILL_COOLDOWN_OLD_MIN) + ELSE
    new = i32_const(KILL_COOLDOWN_MIN) + I32_LT_S + IF_I32 + i32_const(KILL_COOLDOWN_MIN) + ELSE
    return replace_once(body, old, new, "kill cooldown clamp")


def stop_coroutine_null_guard(nparams, first_local):
    return local_get(1) + I32_EQZ + IF_VOID + RETURN + END


def kill_timer_text(body):
    head = local_get(1) + i32_load(OFF_KILL_COOLDOWN_TEXT) + i32_const(0) + call(F_GET_GAMEOBJECT)
    tail = i32_const(0) + call(F_SET_ACTIVE)
    old = head + i32_const(1) + tail
    new = head + local_get(1) + i32_load(OFF_KILL_COOLDOWN) + i32_const(0) + I32_NE + tail
    return replace_once(body, old, new, "kill timer text")


def round_start_kill_cooldown(body):
    setting = i32_const(0) + call(F_PREFS_GET_KILL_COOLDOWN)
    tail = i32_const(0) + call(F_START_KILL_TIMER)
    old = local_get(0) + i32_const(ROUND_START_KILL_COOLDOWN) + tail
    new = (
        local_get(0)
        + i32_const(ROUND_START_KILL_COOLDOWN) + setting
        + setting + i32_const(ROUND_START_KILL_COOLDOWN) + I32_GT_S + SELECT
        + tail
    )
    return replace_once(body, old, new, "round start kill cooldown")


def sections(b):
    p = 8
    out = []
    while p < len(b):
        sid = b[p]
        size, q = read_uleb(b, p + 1)
        out.append((sid, p, q, q + size))
        p = q + size
    return out


def count_imported_funcs(b, start):
    p = start
    n, p = read_uleb(b, p)
    funcs = 0
    for _ in range(n):
        l, p = read_uleb(b, p)
        p += l
        l, p = read_uleb(b, p)
        p += l
        kind = b[p]
        p += 1
        if kind == 0:
            _, p = read_uleb(b, p)
            funcs += 1
        elif kind in (1, 2):
            if kind == 1:
                p += 1
            flags, p = read_uleb(b, p)
            _, p = read_uleb(b, p)
            if flags & 1:
                _, p = read_uleb(b, p)
        elif kind == 3:
            p += 2
    return funcs


def patch_function(body, nparams, make_code, extra_i32_locals):
    p = 0
    ngroups, p = read_uleb(body, p)
    groups = []
    nlocals = 0
    for _ in range(ngroups):
        cnt, p = read_uleb(body, p)
        typ = body[p]
        p += 1
        groups.append((cnt, typ))
        nlocals += cnt
    first = nparams + nlocals
    if extra_i32_locals:
        groups.append((extra_i32_locals, 0x7F))
    head = uleb(len(groups)) + b"".join(uleb(c) + bytes([t]) for c, t in groups)
    return head + make_code(nparams, first) + body[p:]


def main():
    raw = open(SRC, "rb").read()
    flags = raw[3]
    pos = 10
    if flags & 4:
        pos += 2 + raw[pos] + (raw[pos + 1] << 8)
    if flags & 8:
        pos = raw.index(b"\0", pos) + 1
    if flags & 16:
        pos = raw.index(b"\0", pos) + 1
    if flags & 2:
        pos += 2
    header = raw[:pos]
    wasm = zlib.decompressobj(-15).decompress(raw[pos:])

    secs = sections(wasm)
    imp = next(s for s in secs if s[0] == 2)
    nimp = count_imported_funcs(wasm, imp[2])
    code = next(s for s in secs if s[0] == 10)

    patches = {
        F_UPDATE: (2, name_tags, 3),
        F_GAME_UPDATE: (2, keybinds_top, 1),
        F_ARROW_ON_MOUSE_DOWN: (2, arrow_guard, 1),
        F_SHOW_VENT_DIRECTIONS_MOVE_NEXT: (2, vent_directions_guard, 1),
        F_STOP_COROUTINE: (3, stop_coroutine_null_guard, 0),
    }
    replacements = {
        F_ARROW_ON_MOUSE_DOWN: vent_arrows,
        F_GAME_UPDATE: lambda body: keybinds_body(body, 3),
        F_ON_CHANGE_KILL_COOLDOWN: kill_cooldown_min,
        F_KILL_TIMER_MOVE_NEXT: kill_timer_text,
        F_START_NEW_ROUND: round_start_kill_cooldown,
    }

    p = code[2]
    n, p = read_uleb(wasm, p)
    bodies = bytearray(uleb(n))
    for i in range(n):
        size, q = read_uleb(wasm, p)
        body = wasm[q:q + size]
        f = i + nimp
        if f in patches:
            nparams, maker, extra = patches[f]
            body = patch_function(body, nparams, maker, extra)
        if f in replacements:
            body = replacements[f](body)
        bodies += uleb(len(body)) + body
        p = q + size

    out = wasm[:code[1]] + b"\x0a" + uleb(len(bodies)) + bytes(bodies) + wasm[code[3]:]

    if len(sys.argv) > 1:
        open(sys.argv[1], "wb").write(out)

    c = zlib.compressobj(9, zlib.DEFLATED, -15)
    gz = c.compress(out) + c.flush()
    open(DST, "wb").write(header + gz + struct.pack("<II", zlib.crc32(out) & 0xFFFFFFFF, len(out) & 0xFFFFFFFF))
    print("patched", len(set(patches) | set(replacements)), "function(s) ->", DST)


if __name__ == "__main__":
    main()
