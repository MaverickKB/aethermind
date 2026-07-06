"""Pure-Python Ed25519 (RFC 8032) for layer-provenance signing/verification.

Vendored reference implementation (public-domain construction from RFC 8032
section 6). Used because the coordinator ships with zero third-party dependencies.
It backs optional layer provenance (see provenance.py): an author key signs a
canonical digest of a layer's identity, and ``verify`` checks it with public
material only. Performance is adequate for per-layer signing (a few ms-scale
operations, not bulk traffic).
"""

from __future__ import annotations

import hashlib

_P = 2 ** 255 - 19
_L = 2 ** 252 + 27742317777372353535851937790883648493
_D = -121665 * pow(121666, _P - 2, _P) % _P
_I = pow(2, (_P - 1) // 4, _P)


def _sha512(data: bytes) -> bytes:
    return hashlib.sha512(data).digest()


def _inv(x: int) -> int:
    return pow(x, _P - 2, _P)


def _recover_x(y: int, sign: int) -> int:
    if y >= _P:
        raise ValueError("invalid point encoding")
    x2 = (y * y - 1) * _inv(_D * y * y + 1) % _P
    if x2 == 0:
        if sign:
            raise ValueError("invalid point encoding")
        return 0
    x = pow(x2, (_P + 3) // 8, _P)
    if (x * x - x2) % _P != 0:
        x = x * _I % _P
    if (x * x - x2) % _P != 0:
        raise ValueError("invalid point encoding")
    if (x & 1) != sign:
        x = _P - x
    return x


_BY = 4 * _inv(5) % _P
_BX = _recover_x(_BY, 0)
_B = (_BX % _P, _BY % _P, 1, _BX * _BY % _P)


def _point_add(p, q):
    a = (p[1] - p[0]) * (q[1] - q[0]) % _P
    b = (p[1] + p[0]) * (q[1] + q[0]) % _P
    c = 2 * p[3] * q[3] * _D % _P
    d = 2 * p[2] * q[2] % _P
    e, f, g, h = b - a, d - c, d + c, b + a
    return (e * f % _P, g * h % _P, f * g % _P, e * h % _P)


def _point_mul(s: int, p):
    q = (0, 1, 1, 0)
    while s > 0:
        if s & 1:
            q = _point_add(q, p)
        p = _point_add(p, p)
        s >>= 1
    return q


def _point_equal(p, q) -> bool:
    if (p[0] * q[2] - q[0] * p[2]) % _P != 0:
        return False
    if (p[1] * q[2] - q[1] * p[2]) % _P != 0:
        return False
    return True


def _point_compress(p) -> bytes:
    zinv = _inv(p[2])
    x = p[0] * zinv % _P
    y = p[1] * zinv % _P
    return int.to_bytes(y | ((x & 1) << 255), 32, "little")


def _point_decompress(s: bytes):
    if len(s) != 32:
        raise ValueError("invalid point encoding")
    y = int.from_bytes(s, "little")
    sign = y >> 255
    y &= (1 << 255) - 1
    x = _recover_x(y, sign)
    return (x, y, 1, x * y % _P)


def _secret_expand(secret: bytes):
    if len(secret) != 32:
        raise ValueError("secret key must be 32 bytes")
    h = _sha512(secret)
    a = int.from_bytes(h[:32], "little")
    a &= (1 << 254) - 8
    a |= 1 << 254
    return a, h[32:]


def public_key(secret: bytes) -> bytes:
    a, _ = _secret_expand(secret)
    return _point_compress(_point_mul(a, _B))


def sign(secret: bytes, message: bytes) -> bytes:
    a, prefix = _secret_expand(secret)
    pub = _point_compress(_point_mul(a, _B))
    r = int.from_bytes(_sha512(prefix + message), "little") % _L
    rs = _point_compress(_point_mul(r, _B))
    h = int.from_bytes(_sha512(rs + pub + message), "little") % _L
    s = (r + h * a) % _L
    return rs + int.to_bytes(s, 32, "little")


def _is_small_order(p) -> bool:
    q = _point_add(p, p)
    q = _point_add(q, q)
    q = _point_add(q, q)
    return _point_equal(q, (0, 1, 1, 0))


def verify(pub: bytes, message: bytes, signature: bytes) -> bool:
    if len(pub) != 32 or len(signature) != 64:
        return False
    try:
        a = _point_decompress(pub)
        rs = signature[:32]
        r = _point_decompress(rs)
    except ValueError:
        return False
    # Reject small-order/degenerate keys and nonces (e.g. all-zero material).
    if _is_small_order(a) or _is_small_order(r):
        return False
    s = int.from_bytes(signature[32:], "little")
    if s >= _L:
        return False
    h = int.from_bytes(_sha512(rs + pub + message), "little") % _L
    left = _point_mul(s, _B)
    right = _point_add(r, _point_mul(h, a))
    return _point_equal(left, right)
