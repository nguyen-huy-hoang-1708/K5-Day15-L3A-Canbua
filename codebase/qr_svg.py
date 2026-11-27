"""Pure-Python ISO/IEC 18004 QR Code SVG generator (Byte mode, ECC Level L, Versions 1..8).

Không cần thư viện ngoài (zero dependencies), hỗ trợ URL tới 192 byte UTF-8.
"""
import html

# Galois Field GF(256) với đa thức nguyên thuỷ 0x11d
_EXP = [0] * 512
_LOG = [0] * 256
_x = 1
for _i in range(255):
    _EXP[_i] = _x
    _LOG[_x] = _i
    _x <<= 1
    if _x & 0x100:
        _x ^= 0x11D
for _i in range(255, 512):
    _EXP[_i] = _EXP[_i - 255]


def _gf_mul(a: int, b: int) -> int:
    if a == 0 or b == 0:
        return 0
    return _EXP[_LOG[a] + _LOG[b]]


def _rs_gen_poly(degree: int) -> list:
    poly = [1]
    for i in range(degree):
        # nhân với (x - alpha^i) == (x + alpha^i) trong GF(256)
        nxt = [0] * (len(poly) + 1)
        root = _EXP[i]
        for j, c in enumerate(poly):
            nxt[j] ^= c
            nxt[j + 1] ^= _gf_mul(c, root)
        poly = nxt
    return poly


def _rs_remainder(data: list, ec_len: int) -> list:
    gen = _rs_gen_poly(ec_len)
    res = list(data) + [0] * ec_len
    for i in range(len(data)):
        coef = res[i]
        if coef != 0:
            for j in range(1, len(gen)):
                res[i + j] ^= _gf_mul(gen[j], coef)
    return res[len(data):]


# (version, blocks, data_per_block, ec_per_block, alignment_coords, remainder_bits) — ECC Level L
_VERSIONS_L = [
    (1, 1, 19, 7, [], 0),
    (2, 1, 34, 10, [6, 18], 7),
    (3, 1, 55, 15, [6, 22], 7),
    (4, 1, 80, 20, [6, 26], 7),
    (5, 1, 108, 26, [6, 30], 7),
    (6, 2, 68, 18, [6, 34], 7),
    (7, 2, 78, 20, [6, 22, 38], 0),
    (8, 2, 97, 24, [6, 24, 42], 0),
]


def _encode_data_bits(payload: bytes) -> tuple:
    # Byte mode (4 bits = 0100) + length (8 bits cho version 1..9) + data
    need_bytes = len(payload) + 2  # 4 + 8 bits header + 4 bits terminator ~ 2 bytes
    chosen = None
    for spec in _VERSIONS_L:
        ver, blocks, dpb, ec, align, rem = spec
        total_data = blocks * dpb
        if total_data >= need_bytes:
            chosen = spec
            break
    if chosen is None:
        raise ValueError("Nội dung QR quá dài (tối đa 192 byte).")

    ver, blocks, dpb, ec, align, rem = chosen
    total_data = blocks * dpb

    bits = [0, 1, 0, 0]  # Byte mode
    for b in range(7, -1, -1):
        bits.append((len(payload) >> b) & 1)
    for byte in payload:
        for b in range(7, -1, -1):
            bits.append((byte >> b) & 1)

    max_bits = total_data * 8
    term = min(4, max_bits - len(bits))
    bits.extend([0] * term)
    while len(bits) % 8 != 0:
        bits.append(0)

    data_cw = []
    for i in range(0, len(bits), 8):
        val = 0
        for b in range(8):
            val = (val << 1) | bits[i + b]
        data_cw.append(val)

    pad_bytes = (0xEC, 0x11)
    pi = 0
    while len(data_cw) < total_data:
        data_cw.append(pad_bytes[pi % 2])
        pi += 1

    # Chia block & tạo mã sửa lỗi Reed-Solomon
    d_blocks = [data_cw[i * dpb:(i + 1) * dpb] for i in range(blocks)]
    e_blocks = [_rs_remainder(blk, ec) for blk in d_blocks]

    interleaved = []
    for col in range(dpb):
        for blk in d_blocks:
            interleaved.append(blk[col])
    for col in range(ec):
        for blk in e_blocks:
            interleaved.append(blk[col])

    out_bits = []
    for cw in interleaved:
        for b in range(7, -1, -1):
            out_bits.append((cw >> b) & 1)
    out_bits.extend([0] * rem)
    return chosen, out_bits


def _format_bits(mask: int) -> int:
    # ECC Level L = 01 (2 bits) + mask (3 bits)
    data = (0b01 << 3) | (mask & 0b111)
    d = data << 10
    gen = 0b10100110111
    for i in range(14, 9, -1):
        if (d >> i) & 1:
            d ^= gen << (i - 10)
    return ((data << 10) | d) ^ 0b101010000010010


def _version_bits(ver: int) -> int:
    d = ver << 12
    gen = 0b1111100100101
    for i in range(17, 11, -1):
        if (d >> i) & 1:
            d ^= gen << (i - 12)
    return (ver << 12) | d


def _build_matrix(text: str) -> list:
    payload = text.encode("utf-8")
    (ver, _, _, _, align, _), stream = _encode_data_bits(payload)
    size = ver * 4 + 17
    grid = [[None] * size for _ in range(size)]
    func = [[False] * size for _ in range(size)]

    def set_fn(r: int, c: int, val: bool):
        if 0 <= r < size and 0 <= c < size:
            grid[r][c] = bool(val)
            func[r][c] = True

    def place_finder(r0: int, c0: int):
        for dr in range(-1, 8):
            for dc in range(-1, 8):
                r, c = r0 + dr, c0 + dc
                if not (0 <= r < size and 0 <= c < size):
                    continue
                if dr in (-1, 7) or dc in (-1, 7):
                    set_fn(r, c, False)
                elif dr in (0, 6) or dc in (0, 6) or (2 <= dr <= 4 and 2 <= dc <= 4):
                    set_fn(r, c, True)
                else:
                    set_fn(r, c, False)

    place_finder(0, 0)
    place_finder(0, size - 7)
    place_finder(size - 7, 0)

    # Alignment patterns
    for r0 in align:
        for c0 in align:
            if (r0 <= 8 and c0 <= 8) or (r0 <= 8 and c0 >= size - 9) or (r0 >= size - 9 and c0 <= 8):
                continue
            for dr in range(-2, 3):
                for dc in range(-2, 3):
                    is_dark = (max(abs(dr), abs(dc)) in (0, 2))
                    set_fn(r0 + dr, c0 + dc, is_dark)

    # Timing patterns
    for i in range(8, size - 8):
        val = (i % 2 == 0)
        if not func[6][i]:
            set_fn(6, i, val)
        if not func[i][6]:
            set_fn(i, 6, val)

    # Dark module
    set_fn(4 * ver + 9, 8, True)

    # Reserve format info cells
    for i in range(9):
        if not func[8][i]:
            set_fn(8, i, False)
        if not func[i][8]:
            set_fn(i, 8, False)
    for i in range(8):
        set_fn(8, size - 1 - i, False)
        if i < 7:
            set_fn(size - 1 - i, 8, False)

    # Version info (>= 7)
    if ver >= 7:
        vb = _version_bits(ver)
        for i in range(18):
            bit = bool((vb >> i) & 1)
            a, b = size - 11 + (i % 3), i // 3
            set_fn(a, b, bit)
            set_fn(b, a, bit)

    # Place data bits zig-zag
    idx = 0
    col = size - 1
    up = True
    while col > 0:
        if col == 6:
            col -= 1
        rows = range(size - 1, -1, -1) if up else range(size)
        for r in rows:
            for dc in (0, -1):
                c = col + dc
                if not func[r][c]:
                    grid[r][c] = bool(stream[idx]) if idx < len(stream) else False
                    idx += 1
        col -= 2
        up = not up

    def apply_mask(m: int) -> list:
        res = [row[:] for row in grid]
        for r in range(size):
            for c in range(size):
                if func[r][c]:
                    continue
                if m == 0:
                    inv = (r + c) % 2 == 0
                elif m == 1:
                    inv = r % 2 == 0
                elif m == 2:
                    inv = c % 3 == 0
                elif m == 3:
                    inv = (r + c) % 3 == 0
                elif m == 4:
                    inv = ((r // 2) + (c // 3)) % 2 == 0
                elif m == 5:
                    inv = ((r * c) % 2 + (r * c) % 3) == 0
                elif m == 6:
                    inv = (((r * c) % 2 + (r * c) % 3) % 2) == 0
                else:
                    inv = (((r + c) % 2 + (r * c) % 3) % 2) == 0
                if inv:
                    res[r][c] = not res[r][c]
        fmt = _format_bits(m)
        # Đặt 15 bit format theo chuẩn ISO 18004 (bit 14 là MSB ở (8,0) & (size-1,8), bit 0 là LSB ở (0,8) & (8,size-1))
        for i in range(15):
            bit = bool((fmt >> i) & 1)
            if i < 6:
                res[i][8] = bit
            elif i == 6:
                res[7][8] = bit
            elif i == 7:
                res[8][8] = bit
            elif i == 8:
                res[8][7] = bit
            else:
                res[8][14 - i] = bit

            if i < 8:
                res[8][size - 1 - i] = bit
            else:
                res[size - 15 + i][8] = bit
        return res

    def penalty(mat: list) -> int:
        p = 0
        for r in range(size):
            run = 1
            for c in range(1, size):
                if mat[r][c] == mat[r][c - 1]:
                    run += 1
                    if run == 5:
                        p += 3
                    elif run > 5:
                        p += 1
                else:
                    run = 1
        for c in range(size):
            run = 1
            for r in range(1, size):
                if mat[r][c] == mat[r - 1][c]:
                    run += 1
                    if run == 5:
                        p += 3
                    elif run > 5:
                        p += 1
                else:
                    run = 1
        for r in range(size - 1):
            for c in range(size - 1):
                v = mat[r][c]
                if mat[r][c + 1] == v and mat[r + 1][c] == v and mat[r + 1][c + 1] == v:
                    p += 3
        return p

    best = None
    best_score = None
    for m in range(8):
        cand = apply_mask(m)
        sc = penalty(cand)
        if best_score is None or sc < best_score:
            best_score = sc
            best = cand
    return best


def render_qr_svg(text: str, module_px: int = 4, quiet: int = 2) -> str:
    mat = _build_matrix(text)
    size = len(mat)
    total = size + quiet * 2
    paths = []
    for r in range(size):
        c = 0
        y = r + quiet
        while c < size:
            if mat[r][c]:
                start = c
                while c < size and mat[r][c]:
                    c += 1
                w = c - start
                paths.append(f"M{start + quiet},{y}h{w}v1h-{w}z")
            else:
                c += 1
    title = html.escape(text, quote=True)
    px = total * module_px
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total} {total}" '
        f'width="{px}" height="{px}" shape-rendering="crispEdges" role="img" aria-label="QR {title}">'
        f'<rect width="{total}" height="{total}" fill="#ffffff"/>'
        f'<path fill="#0f172a" d="{"".join(paths)}"/>'
        f'</svg>'
    )
