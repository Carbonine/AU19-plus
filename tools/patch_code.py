import os
import struct
import sys
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME = "AmongUs2019_WebGL.wasm.code.unityweb"
SRC = os.path.join(os.path.dirname(ROOT), "AmongUs2019", "Build", NAME)
DST = os.path.join(ROOT, "Build", NAME)

F_SET_COLOR = 29837
F_UPDATE = 30941
F_GET_RENDERER = 32277
F_GET_GAMEOBJECT = 48641
F_SET_ACTIVE = 48891
F_GET_ENABLED = 51756
F_SET_ENABLED = 51757

OFF_USERNAME_TEXT = 36
OFF_SRENDERER = 32
OFF_IS_DEAD = 56
OFF_IS_IMPOSTOR = 80
OFF_VENTING = 152
OFF_INSIDE_VENT = 153
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
I32_OR = b"\x72"
I32_EQZ = b"\x45"
SELECT = b"\x1b"
IF_VOID = b"\x04\x40"
END = b"\x0b"


def name_tags(nparams, first_local):
    this = local_get(0)
    lbl = first_local
    sp = first_local + 1
    impostor = this + i32_load8_u(OFF_IS_IMPOSTOR)
    green_blue = f32_const(0.0) + f32_const(1.0) + impostor + SELECT
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
        + global_get(STACK_PTR) + local_set(sp)
        + global_get(STACK_PTR) + i32_const(16) + I32_ADD + global_set(STACK_PTR)
        + local_get(sp) + f32_const(1.0) + f32_store(0)
        + local_get(sp) + green_blue + f32_store(4)
        + local_get(sp) + green_blue + f32_store(8)
        + local_get(sp) + f32_const(1.0) + f32_store(12)
        + local_get(lbl) + local_get(sp) + i32_const(0) + call(F_SET_COLOR)
        + local_get(sp) + global_set(STACK_PTR)
        + END
    )
    return code


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

    patches = {F_UPDATE: (2, name_tags, 2)}

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
        bodies += uleb(len(body)) + body
        p = q + size

    out = wasm[:code[1]] + b"\x0a" + uleb(len(bodies)) + bytes(bodies) + wasm[code[3]:]

    if len(sys.argv) > 1:
        open(sys.argv[1], "wb").write(out)

    c = zlib.compressobj(9, zlib.DEFLATED, -15)
    gz = c.compress(out) + c.flush()
    open(DST, "wb").write(header + gz + struct.pack("<II", zlib.crc32(out) & 0xFFFFFFFF, len(out) & 0xFFFFFFFF))
    print("patched", len(patches), "function(s) ->", DST)


if __name__ == "__main__":
    main()
