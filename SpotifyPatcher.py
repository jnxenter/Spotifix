import os
import re
import shutil
import struct
import subprocess
import sys
import zipfile
import zlib
import hashlib

FLAG_SECURE = 0x2000

CONST_RE = re.compile(
    r'^(?P<indent>\s*)(?P<instr>const(?:/16|/4|/high16)?|sget(?:-object|-wide)?)\s+(?P<reg>[vp]\d+),\s*(?P<value>[^\s#]+)'
)

COMMENT_STRIP_RE = re.compile(r'\s*#.*$')

SET_FLAGS_RE = re.compile(r'Landroid/view/Window;->(setFlags|addFlags)\(I+I\)V')
SGET_FLAG_SECURE_RE = re.compile(r'Landroid/view/WindowManager\$LayoutParams;->FLAG_SECURE:I')

DEST_RE = re.compile(
    r'^\s*(?:'
    r'const(?:/16|/4|/high16|/wide|/wide/16|/wide/32)?'
    r'|sget(?:-object|-wide|-boolean|-byte|-char|-short)?'
    r'|iget(?:-object|-wide|-boolean|-byte|-char|-short)?'
    r'|move-result(?:-object|-wide)?'
    r'|move(?:-object|-wide|-from16|-object/from16|-wide/from16|/16)?'
    r'|new-instance'
    r'|array-length'
    r'|instance-of'
    r'|aput(?:-object|-wide|-boolean|-byte|-char|-short)?'
    r'|add(?:-int|-long|-float|-double)?(?:/2addr|/lit16|/lit8)?'
    r'|sub(?:-int|-long|-float|-double)?(?:/2addr|/lit16|/lit8)?'
    r'|mul(?:-int|-long|-float|-double)?(?:/2addr|/lit16|/lit8)?'
    r'|div(?:-int|-long|-float|-double)?(?:/2addr|/lit16|/lit8)?'
    r'|rem(?:-int|-long|-float|-double)?(?:/2addr|/lit16|/lit8)?'
    r'|and(?:-int|-long)?(?:/2addr|/lit16|/lit8)?'
    r'|or(?:-int|-long)?(?:/2addr|/lit16|/lit8)?'
    r'|xor(?:-int|-long)?(?:/2addr|/lit16|/lit8)?'
    r'|shl(?:-int|-long)?(?:/2addr|/lit16|/lit8)?'
    r'|shr(?:-int|-long)?(?:/2addr|/lit16|/lit8)?'
    r'|ushr(?:-int|-long)?(?:/2addr|/lit16|/lit8)?'
    r'|neg(?:-int|-long|-float|-double)?'
    r'|not(?:-int|-long)?'
    r'|int-to(?:-long|-float|-double|-byte|-char|-short)?'
    r'|long-to(?:-int|-float|-double)?'
    r'|float-to(?:-int|-long|-double)?'
    r'|double-to(?:-int|-long|-float)?'
    r'|check-cast'
    r')\s+([vp]\d+),?'
)


def _strip_comment(line):
    return COMMENT_STRIP_RE.sub('', line).strip()


def _dest_register(line):
    """Return the destination register of an instruction line, or None."""
    m = DEST_RE.match(line)
    return m.group(1) if m else None


def _find_register_assignment(body, reg, before_index):
    """Look backwards from before_index for the latest assignment to `reg`.

    Returns (line_index, instr, value) or (None, None, None).
    """
    for idx in range(before_index - 1, -1, -1):
        line = body[idx]
        stripped = _strip_comment(line)
        if not stripped:
            continue
        if stripped == '.end method' or stripped.startswith('.method ') or stripped.startswith('.line '):
            continue
        if stripped.startswith('.locals') or stripped.startswith('.registers') or stripped.startswith('.param'):
            continue
        if stripped.startswith(':'):
            continue  # label
        dest = _dest_register(stripped)
        if dest is None:
            continue
        if dest != reg:
            continue
        # This line writes to `reg`: it is the latest assignment.
        m = CONST_RE.match(line)
        if m:
            return idx, m.group('instr'), m.group('value')
        return None, None, None
    return None, None, None


def _process_method(body):
    """Rewrite Window.setFlags/addFlags that apply FLAG_SECURE to a no-op."""
    changed = False
    for i, line in enumerate(body):
        stripped = _strip_comment(line)
        m = SET_FLAGS_RE.search(stripped)
        if not m:
            continue
        # Parse invoke-virtual {vA, vB, ...}, method
        arg_part = stripped.split('{', 1)
        if len(arg_part) < 2:
            continue
        regs = arg_part[1].split('}', 1)[0].split(',')
        regs = [r.strip() for r in regs if r.strip()]
        if len(regs) < 2:
            continue
        receiver = regs[0]
        is_add = m.group(1) == 'addFlags'
        # addFlags(I)V: regs[1] is the flags value.
        # setFlags(II)V: regs[1] is flags, regs[2] is the mask.
        # Only ever neutralize the *flags* value. The mask register is left
        # untouched: rcd0/uep (classes.dex) call setFlags(0xffffdfff, 0x2000)
        # to *clear* FLAG_SECURE, and zeroing that mask turns the clear into a
        # no-op, leaving the window secure (black screen / crash).
        check_regs = [regs[1]]
        for flags_reg in check_regs:
            idx, instr, value = _find_register_assignment(body, flags_reg, i)
            if idx is None:
                continue
            is_flag_secure = False
            if instr == 'sget' and SGET_FLAG_SECURE_RE.search(value or ''):
                is_flag_secure = True
            elif value is not None and value.startswith('0x'):
                try:
                    if int(value, 16) == FLAG_SECURE:
                        is_flag_secure = True
                except ValueError:
                    pass
            if not is_flag_secure:
                continue
            # Neutralize the flag assignment: set it to 0.
            indent = re.match(r'^\s*', body[idx]).group(0)
            body[idx] = f'{indent}const/16 {flags_reg}, 0x0\n'
            changed = True
            break
    return changed


LAST_CHANGED = []


def patch_smali_folder(apktool_out_dir):
    """Patch every smali file under the decoded APK folder. Returns count."""
    del LAST_CHANGED[:]
    candidates = _find_candidates(apktool_out_dir)
    total_changed = 0
    for path in candidates:
        try:
            with open(path, 'rb') as fh:
                data = fh.read()
        except OSError:
            continue
        if b'setFlags' not in data and b'addFlags' not in data:
            continue
        try:
            content = data.decode('utf-8', errors='replace')
        except Exception:
            continue
        lines = content.splitlines(keepends=True)
        new_lines = []
        i = 0
        changed_file = False
        while i < len(lines):
            if lines[i].lstrip().startswith('.method '):
                j = i
                while j < len(lines) and lines[j].strip() != '.end method':
                    j += 1
                if j >= len(lines):
                    new_lines.extend(lines[i:])
                    break
                body = lines[i:j + 1]
                if _process_method(body):
                    changed_file = True
                new_lines.extend(body)
                i = j + 1
            else:
                new_lines.append(lines[i])
                i += 1
        if changed_file:
            with open(path, 'w', encoding='utf-8') as fh:
                fh.writelines(new_lines)
            total_changed += 1
            LAST_CHANGED.append(path)
    return total_changed


def _find_candidates(apktool_out_dir):
    """Return smali files that reference android/view/Window methods.

    In-process scan only: `findstr /S /M` takes ~80s per dex directory on
    Windows (real-time antivirus + subprocess overhead), Python reads the
    same data in <1s.
    """
    results = []
    for root, _, files in os.walk(apktool_out_dir):
        for fname in files:
            if not fname.endswith('.smali'):
                continue
            path = os.path.join(root, fname)
            try:
                with open(path, 'rb') as fh:
                    data = fh.read()
            except OSError:
                continue
            if b'Landroid/view/Window;->' in data:
                results.append(path)
    return results


def run(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


def _resolve_java(tools_dir):
    """Prefer a bundled portable JRE inside Tools, then JAVA_HOME, then PATH."""
    bundled = os.path.join(tools_dir, 'jre', 'bin', 'java.exe')
    if os.path.isfile(bundled):
        return bundled
    java = os.environ.get('JAVA_HOME', 'java')
    java_bin = os.path.join(java, 'bin', 'java.exe') if os.path.isdir(java) else 'java'
    return java_bin if os.path.exists(java_bin) else 'java'


def patch_apk(apk_path, out_apk_path, tools_dir, work_dir, keep_intermediate=False):
    """Full pipeline: fast dex-only patch when possible, apktool fallback.

    Returns (ok, message).
    """
    fast = patch_apk_fast(apk_path, out_apk_path, tools_dir, work_dir, keep_intermediate)
    if fast[0] is not None:
        return fast
    return patch_apk_slow(apk_path, out_apk_path, tools_dir, work_dir, keep_intermediate, fast[1])


DEX_NAME_RE = re.compile(r'^classes(?:\d+)?\.dex$')


def _iter_dex(apk_path):
    import zipfile
    with zipfile.ZipFile(apk_path) as z:
        for info in z.infolist():
            if DEX_NAME_RE.match(info.filename):
                yield info.filename, z.read(info.filename)


def _dex_has_window_flag_methods(data):
    """Return True if a dex references Window.setFlags/addFlags.

    In a compiled dex the call `Window.setFlags` is NOT stored as one string:
    the class ('Landroid/view/Window;'), the method name ('setFlags') and the
    proto ('(II)V') live in separate pools linked by method_ids. This parses
    the dex headers/method_ids to check exactly.
    """
    import struct
    if len(data) < 112 or data[:4] != b'dex\n':
        return False
    string_ids_size = struct.unpack_from('<I', data, 56)[0]
    string_ids_off = struct.unpack_from('<I', data, 60)[0]
    type_ids_size = struct.unpack_from('<I', data, 64)[0]
    type_ids_off = struct.unpack_from('<I', data, 68)[0]
    method_ids_size = struct.unpack_from('<I', data, 88)[0]
    method_ids_off = struct.unpack_from('<I', data, 92)[0]

    string_cache = {}

    def read_string(idx):
        if idx in string_cache:
            return string_cache[idx]
        off = struct.unpack_from('<I', data, string_ids_off + idx * 4)[0]
        pos = off
        while data[pos] & 0x80:
            pos += 1
        pos += 1
        end = data.index(b'\x00', pos)
        s = data[pos:end].decode('utf-8', errors='replace')
        string_cache[idx] = s
        return s

    win_type = None
    for i in range(type_ids_size):
        sidx = struct.unpack_from('<I', data, type_ids_off + i * 4)[0]
        if read_string(sidx) == 'Landroid/view/Window;':
            win_type = i
            break
    if win_type is None:
        return False
    for i in range(method_ids_size):
        off = method_ids_off + i * 8
        class_idx = struct.unpack_from('<H', data, off)[0]
        if class_idx != win_type:
            continue
        name_idx = struct.unpack_from('<I', data, off + 4)[0]
        if read_string(name_idx) in ('setFlags', 'addFlags'):
            return True
    return False


def _read_entry_raw(zf, info):
    """Read an entry from an open ZipFile tolerating bad CRC-32 entries.

    Some Spotify/App-Cloner APKs ship entries with deliberately broken CRCs to
    break repackers. Android installs them fine; Python's strict zipfile does
    not, so read the compressed bytes straight from the local header.
    """
    try:
        return zf.read(info.filename)
    except zipfile.BadZipFile:
        pass
    import struct
    import zlib
    fp = zf.fp
    try:
        fp.seek(info.header_offset)
        fh = fp.read(30)
        if len(fh) < 30 or fh[:4] != b'PK\x03\x04':
            return b''
        name_len, extra_len = struct.unpack('<HH', fh[26:30])
        fp.seek(info.header_offset + 30 + name_len + extra_len)
        raw = fp.read(info.compress_size)
    except Exception:
        return b''
    if info.compress_type == zipfile.ZIP_STORED:
        return raw
    if info.compress_type == zipfile.ZIP_DEFLATED:
        try:
            return zlib.decompress(raw, -zlib.MAX_WBITS)
        except Exception:
            return b''
    return b''


def _java_cmd(java, jar, *args):
    """Build a capped-heap java -jar command (safe for parallel JVMs)."""
    return [java, '-Xmx1536m', '-jar', jar] + list(args)


# ---------------------------------------------------------------------------
# Pure in-memory DEX patcher (no baksmali/smali round-trip).
# Walks every code_item, finds `const/16 v?, 0x2000` (FLAG_SECURE) that is used
# as the *flags* argument of a `Window.setFlags(II)` call and zeroes it. This
# is a few tens of MB/s of pure Python — seconds instead of minutes.
# ---------------------------------------------------------------------------
_INSZ1 = {0x00, 0x01, 0x04, 0x07, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f, 0x10,
          0x11, 0x12, 0x1d, 0x1e, 0x21, 0x27, 0x28}
_INSZ1 |= set(range(0x7b, 0x90))
_INSZ1 |= set(range(0xb0, 0xd0))
_INSZ2 = {0x02, 0x03, 0x05, 0x06, 0x08, 0x09, 0x13, 0x15, 0x16, 0x19, 0x1a,
          0x1c, 0x1f, 0x20, 0x22, 0x23, 0x29, 0xfe, 0xff}
_INSZ2 |= set(range(0x2d, 0x3e))
_INSZ2 |= set(range(0x44, 0x6e))
_INSZ2 |= set(range(0xd0, 0xe3))
_INSZ3 = {0x14, 0x17, 0x1b, 0x24, 0x25, 0x26, 0x2a, 0x2b, 0x2c, 0x6e, 0x6f,
          0x70, 0x71, 0x72, 0x74, 0x75, 0x76, 0x77, 0x78, 0xfc, 0xfd}
_INSZ3 |= set(range(0x90, 0xb0))
_INS_SIZE = {}
for _op in _INSZ1:
    _INS_SIZE[_op] = 1
for _op in _INSZ2:
    _INS_SIZE[_op] = 2
for _op in _INSZ3:
    _INS_SIZE[_op] = 3
for _op in (0xfa, 0xfb):
    _INS_SIZE[_op] = 4
_INS_SIZE[0x18] = 5
del _op
_INVOKE35 = {0x6e, 0x6f, 0x70, 0x71, 0x72}
_INVOKE3R = {0x74, 0x75, 0x76, 0x77, 0x78}
_WRITES_DEST = {0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0a,
                0x0b, 0x0c, 0x0d, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18,
                0x19, 0x1a, 0x1b, 0x1c, 0x20, 0x21, 0x22, 0x23, 0x2d, 0x2e,
                0x2f, 0x30, 0x31}
_WRITES_DEST |= set(range(0x44, 0x59))
_WRITES_DEST |= set(range(0x60, 0x66))
_WRITES_DEST |= set(range(0x7b, 0xb0))


def _u16(d, o):
    return d[o] | (d[o + 1] << 8)


def _u32(d, o):
    return struct.unpack_from('<I', d, o)[0]


def _s16(d, o):
    v = _u16(d, o)
    return v - 0x10000 if v >= 0x8000 else v


def _uleb(d, o):
    r = 0
    s = 0
    while True:
        b = d[o]
        o += 1
        r |= (b & 0x7f) << s
        if (b & 0x80) == 0:
            break
        s += 7
    return r, o


class _Dex:
    """Minimal DEX reader able to walk method bytecode and find/patch consts."""

    def __init__(self, data):
        self.data = data
        self.soff = _u32(data, 60)
        self.ssz = _u32(data, 56)
        self.toff = _u32(data, 68)
        self.tsz = _u32(data, 64)
        self.moff = _u32(data, 92)
        self.msz = _u32(data, 88)
        self.coff = _u32(data, 100)
        self.csz = _u32(data, 96)
        self.strings = []
        for i in range(self.ssz):
            off = _u32(data, self.soff + 4 * i)
            _, p = _uleb(data, off)
            q = p
            while data[q] != 0:
                q += 1
            self.strings.append(data[p:q].decode('utf-8', 'replace'))
        self.types = [self.strings[_u32(data, self.toff + 4 * i)] for i in range(self.tsz)]
        self.methods = []
        for i in range(self.msz):
            o = self.moff + 8 * i
            self.methods.append((self.types[_u16(data, o)], self.strings[_u32(data, o + 4)]))

    def method_code_offsets(self, class_def_idx):
        d = self.data
        cdo = _u32(d, self.coff + 32 * class_def_idx + 24)
        if cdo == 0:
            return []
        p = cdo
        counts = []
        for _ in range(4):
            v, p = _uleb(d, p)
            counts.append(v)
        for _ in range(counts[0] + counts[1]):
            _, p = _uleb(d, p)
            _, p = _uleb(d, p)
        methods = []
        for _ in range(counts[2] + counts[3]):
            _, p = _uleb(d, p)
            _, p = _uleb(d, p)
            co, p = _uleb(d, p)
            methods.append(co)
        return methods

    def all_code_offsets(self):
        out = []
        for i in range(self.csz):
            for co in self.method_code_offsets(i):
                out.append((i, co))
        return out

    def walk(self, code_off):
        d = self.data
        insns_size = _u32(d, code_off + 12)
        base = code_off + 16
        i = 0
        out = []
        while i < insns_size:
            woff = base + 2 * i
            w0 = _u16(d, woff)
            op = w0 & 0xff
            if op == 0x00 and i + 1 < insns_size:
                w1 = _u16(d, woff + 2)
                if w1 == 0x0100:
                    i += 4 + 2 * _u16(d, woff + 4)
                    continue
                if w1 == 0x0200:
                    i += 2 + 4 * _u16(d, woff + 4)
                    continue
                if w1 == 0x0300:
                    ew = _u16(d, woff + 4)
                    n = _u32(d, woff + 6)
                    i += ((8 + ew * n + 3) & ~3) // 2
                    continue
            n = _INS_SIZE.get(op)
            if n is None:
                return None
            out.append((i, woff, op, w0, n))
            i += n
        return out

    def invoke_args(self, op, w0, woff):
        if op in _INVOKE35:
            A = (w0 >> 12) & 0xf
            G = (w0 >> 8) & 0xf
            w2 = _u16(self.data, woff + 4)
            regs = [w2 & 0xf, (w2 >> 4) & 0xf, (w2 >> 8) & 0xf, (w2 >> 12) & 0xf]
            if A == 5:
                regs.append(G)
            return regs[:A]
        if op in _INVOKE3R:
            A = (w0 >> 8) & 0xff
            C = _u16(self.data, woff + 4)
            return list(range(C, C + A))
        return []

    def scan_secure(self):
        setflags = [i for i, (c, n) in enumerate(self.methods)
                    if n == 'setFlags' and c == 'Landroid/view/Window;']
        if not setflags:
            return []
        found = []
        for cdi, co in self.all_code_offsets():
            insns = self.walk(co)
            if insns is None:
                continue
            pending = []
            for (idx, woff, op, w0, n) in insns:
                if op in (0x13, 0x14):
                    if op == 0x13:
                        lit = _s16(self.data, woff + 2)
                    else:
                        lit = (_u16(self.data, woff + 4) << 16) | _u16(self.data, woff + 2)
                        if lit >= 0x80000000:
                            lit -= 0x100000000
                    reg = (w0 >> 8) & 0xff
                    if lit == FLAG_SECURE:
                        pending.append((reg, idx, woff, op))
                    else:
                        pending = [p for p in pending if p[0] != reg]
                elif op in _WRITES_DEST:
                    reg = (w0 >> 8) & 0xff
                    pending = [p for p in pending if p[0] != reg]
                if op in _INVOKE35 or op in _INVOKE3R:
                    m = _u16(self.data, woff + 2)
                    if m in setflags:
                        args = self.invoke_args(op, w0, woff)
                        keep = []
                        for (reg, idx2, woff2, op2) in pending:
                            if len(args) >= 2 and reg == args[1] and idx - idx2 <= 64:
                                found.append((cdi, co, op2, woff2, reg, idx2))
                            else:
                                keep.append((reg, idx2, woff2, op2))
                        pending = keep
        return found

    def patch(self, woff, op):
        d = self.data
        d[woff + 2] = 0
        d[woff + 3] = 0
        if op == 0x14:
            d[woff + 4] = 0
            d[woff + 5] = 0

    def finalize(self):
        d = self.data
        sz = _u32(d, 32)
        d[12:32] = hashlib.sha1(bytes(d[32:sz])).digest()
        d[8:12] = struct.pack('<I', zlib.adler32(bytes(d[12:sz])) & 0xffffffff)


def _patch_in_memory(apk_path, out_apk_path, tools_dir, work_dir, keep_intermediate=False):
    """Patch FLAG_SECURE via pure in-memory DEX rewriting. No baksmali/smali.

    Returns (None, reason) if nothing to patch or the APK can't be handled,
    so the caller can fall back to the baksmali/smali path.
    """
    import zipfile
    if not os.path.exists(work_dir):
        os.makedirs(work_dir, exist_ok=True)
    try:
        zin = zipfile.ZipFile(apk_path)
    except Exception as e:
        return None, 'cannot open apk: %r' % (e,)
    patched = {}
    with zin:
        for info in zin.infolist():
            if not DEX_NAME_RE.match(info.filename):
                continue
            data = bytearray(_read_entry_raw(zin, info))
            if not data or data[:4] != b'dex\n':
                continue
            dex = _Dex(data)
            sites = dex.scan_secure()
            if not sites:
                continue
            for _s in sites:
                dex.patch(_s[3], _s[2])
            dex.finalize()
            patched[info.filename] = bytes(dex.data)
    if not patched:
        return False, 'No FLAG_SECURE usages found to patch (in-memory); the APK is already patched or has nothing to patch.'

    rebuilt_apk = os.path.join(work_dir, 'unsigned.apk')
    with zipfile.ZipFile(apk_path) as zin, zipfile.ZipFile(rebuilt_apk, 'w', allowZip64=True) as zout:
        for info in zin.infolist():
            data = _read_entry_raw(zin, info)
            if info.filename in patched:
                data = patched[info.filename]
            zinfo = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            zinfo.compress_type = info.compress_type
            zinfo.external_attr = info.external_attr
            zout.writestr(zinfo, data)

    zipalign = os.path.join(tools_dir, 'zipalign.exe')
    apksigner_jar = os.path.join(tools_dir, 'apksigner.jar')
    keystore = os.path.join(tools_dir, 'debug.keystore')
    java = _resolve_java(tools_dir)
    ok, msg = _align_sign_copy(rebuilt_apk, out_apk_path, work_dir, zipalign, apksigner_jar, keystore, java)
    if ok and not keep_intermediate:
        for p in os.listdir(work_dir):
            full = os.path.join(work_dir, p)
            if p != 'unsigned.apk':
                if os.path.isdir(full):
                    shutil.rmtree(full, ignore_errors=True)
                else:
                    try:
                        os.remove(full)
                    except OSError:
                        pass
    return ok, msg


def patch_apk_fast(apk_path, out_apk_path, tools_dir, work_dir, keep_intermediate=False):
    """Patch only the dex files that reference Window.setFlags/addFlags.

    Primary path rewrites the dex bytes in memory (no baksmali/smali, seconds).
    Falls back to baksmali/smali disassembly+reassembly if the in-memory scan
    finds nothing or fails, then swaps the dex back into the original APK.
    Resources and the remaining dex stay byte-identical.

    Returns (None, error_reason) when it can't run (missing jars / baksmali or
    smali fails) so the caller can fall back to the slow apktool path.
    """
    import zipfile
    from concurrent.futures import ThreadPoolExecutor, as_completed

    try:
        res = _patch_in_memory(apk_path, out_apk_path, tools_dir, work_dir, keep_intermediate)
    except Exception as e:
        res = (None, 'in-memory patch failed: %r' % (e,))
    if res[0] is True:
        return res
    if res[0] is False:
        # Clean scan found nothing to patch: the APK is already patched or has
        # no FLAG_SECURE usages. Do NOT fall back to the baksmali/smali
        # rebuild (its reassembly of the already-patched dex produced an APK
        # that crashed on open). Just re-package and sign it as-is.
        rebuilt_apk = os.path.join(work_dir, 'unsigned.apk')
        with zipfile.ZipFile(apk_path) as zin, zipfile.ZipFile(rebuilt_apk, 'w', allowZip64=True) as zout:
            for info in zin.infolist():
                data = _read_entry_raw(zin, info)
                zinfo = zipfile.ZipInfo(info.filename, date_time=info.date_time)
                zinfo.compress_type = info.compress_type
                zinfo.external_attr = info.external_attr
                zout.writestr(zinfo, data)
        java = _resolve_java(tools_dir)
        ok, msg = _align_sign_copy(
            rebuilt_apk, out_apk_path, work_dir,
            os.path.join(tools_dir, 'zipalign.exe'),
            os.path.join(tools_dir, 'apksigner.jar'),
            os.path.join(tools_dir, 'debug.keystore'), java)
        if ok:
            return True, 'APK already patched or without FLAG_SECURE usages; no changes applied.'
        return ok, msg
    baksmali = os.path.join(tools_dir, 'baksmali.jar')
    smali = os.path.join(tools_dir, 'smali.jar')
    if not (os.path.isfile(baksmali) and os.path.isfile(smali)):
        return None, 'baksmali/smali jars not found; falling back to apktool.'

    zipalign = os.path.join(tools_dir, 'zipalign.exe')
    apksigner_jar = os.path.join(tools_dir, 'apksigner.jar')
    keystore = os.path.join(tools_dir, 'debug.keystore')
    for f in (zipalign, apksigner_jar, keystore):
        if not os.path.isfile(f):
            return None, f'Missing tool: {f}'

    java = _resolve_java(tools_dir)

    if not os.path.exists(work_dir):
        os.makedirs(work_dir, exist_ok=True)

    api_level = 37
    os.environ['SMALI_API'] = str(api_level)

    # Collect candidate dex (those that reference Window.setFlags/addFlags).
    candidates = []
    with zipfile.ZipFile(apk_path) as z:
        for info in z.infolist():
            if not DEX_NAME_RE.match(info.filename):
                continue
            data = z.read(info.filename)
            if _dex_has_window_flag_methods(data):
                candidates.append((info.filename, data))

    def _disassemble_one(item):
        dex_name, data = item
        dex_path = os.path.join(work_dir, dex_name)
        with open(dex_path, 'wb') as fh:
            fh.write(data)
        smali_dir = os.path.join(work_dir, dex_name + '_smali')
        if os.path.exists(smali_dir):
            shutil.rmtree(smali_dir, ignore_errors=True)
        r = run(_java_cmd(java, baksmali, 'd', dex_path, '-o', smali_dir, '-a', str(api_level)))
        if r.returncode != 0:
            return dex_name, smali_dir, 0, (r.stdout or '')[-800:]
        changed = patch_smali_folder(smali_dir)
        return dex_name, smali_dir, changed, None

    smali_dirs = {}
    failed_reason = None
    workers = min(4, len(candidates)) or 1
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(_disassemble_one, item): item for item in candidates}
        for fut in as_completed(futures):
            dex_name, _smali_dir, changed, err = fut.result()
            if err:
                failed_reason = f'baksmali failed on {dex_name}: ' + err
                break
            if changed:
                smali_dirs[dex_name] = _smali_dir

    if failed_reason:
        return None, failed_reason
    if not smali_dirs:
        return False, 'No FLAG_SECURE usages found to patch.'

    # Reassemble the changed dex in parallel (usually just one).
    patched_dex = {}
    reassemble_fail = None
    with ThreadPoolExecutor(max_workers=min(2, len(smali_dirs)) or 1) as ex:
        def _assemble_one(item):
            dex_name, sdir = item
            new_dex_path = os.path.join(work_dir, 'new_' + dex_name)
            r = run(_java_cmd(java, smali, 'a', sdir, '-o', new_dex_path, '-a', str(api_level)))
            if r.returncode != 0:
                return dex_name, None, (r.stdout or '')[-800:]
            with open(new_dex_path, 'rb') as fh:
                return dex_name, fh.read(), None
        futures = {ex.submit(_assemble_one, item): item for item in smali_dirs.items()}
        for fut in as_completed(futures):
            dex_name, data, err = fut.result()
            if err:
                reassemble_fail = f'smali failed on {dex_name}: ' + err
                break
            patched_dex[dex_name] = data

    if reassemble_fail:
        return None, reassemble_fail

    # Rebuild the APK: original bytes for everything except the patched dex.
    rebuilt_apk = os.path.join(work_dir, 'unsigned.apk')
    with zipfile.ZipFile(apk_path) as zin, zipfile.ZipFile(rebuilt_apk, 'w', allowZip64=True) as zout:
        for info in zin.infolist():
            data = _read_entry_raw(zin, info)
            if info.filename in patched_dex:
                data = patched_dex[info.filename]
            zinfo = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            zinfo.compress_type = info.compress_type
            zinfo.external_attr = info.external_attr
            zout.writestr(zinfo, data)

    ok, msg = _align_sign_copy(rebuilt_apk, out_apk_path, work_dir, zipalign, apksigner_jar, keystore, java)
    if ok and not keep_intermediate:
        for p in os.listdir(work_dir):
            full = os.path.join(work_dir, p)
            if p != 'unsigned.apk':
                if os.path.isdir(full):
                    shutil.rmtree(full, ignore_errors=True)
                else:
                    try:
                        os.remove(full)
                    except OSError:
                        pass
    return ok, msg


def _align_sign_copy(rebuilt_apk, out_apk_path, work_dir, zipalign, apksigner_jar, keystore, java):
    aligned_apk = os.path.join(work_dir, 'aligned.apk')
    signed_apk = os.path.join(work_dir, 'signed.apk')
    if os.path.exists(aligned_apk):
        os.remove(aligned_apk)
    r = run([zipalign, '-f', '-p', '4', rebuilt_apk, aligned_apk])
    if r.returncode != 0:
        r = run([zipalign, '-f', '4', rebuilt_apk, aligned_apk])
        if r.returncode != 0:
            shutil.copy2(rebuilt_apk, aligned_apk)

    if os.path.exists(signed_apk):
        os.remove(signed_apk)
    r = run([
        java, '-jar', apksigner_jar, 'sign',
        '--ks', keystore,
        '--ks-key-alias', 'androiddebugkey',
        '--ks-pass', 'pass:android',
        '--key-pass', 'pass:android',
        '--out', signed_apk,
        aligned_apk,
    ])
    if r.returncode != 0:
        return False, 'apksigner failed:\n' + (r.stdout or '')[-1500:]

    r = run([java, '-jar', apksigner_jar, 'verify', signed_apk])
    if r.returncode != 0:
        return False, 'apksigner verify failed:\n' + (r.stdout or '')[-1500:]

    shutil.copy2(signed_apk, out_apk_path)
    return True, 'OK'


def merge_split_libs(base_apk, split_apk_paths, device_abi, out_apk_path, work_dir):
    """Merge native libs from split APKs (Play Store bundle installs) into the base.

    Play Store installs Spotify as several APKs: base.apk (code/resources) plus
    split_config.<abi>.apk (native libs). Pulling only the first `pm path`
    result produced an APK with no .so files, which crashed on open with
    'liborbit-jni-spotify.so not found'. This rebuilds a single APK with the
    native libs of the device ABI added back, stored uncompressed.

    out_apk_path is UNSIGNED; run patch_apk_fast (or patch_apk) afterwards,
    which re-packages, aligns (page alignment) and signs it.
    Returns (True, message) or (False, reason).
    """
    import zipfile
    if not os.path.exists(work_dir):
        os.makedirs(work_dir, exist_ok=True)
    if not split_apk_paths:
        shutil.copy2(base_apk, out_apk_path)
        return True, 'no splits to merge'
    pref = [device_abi] if device_abi else []
    for extra in ('arm64-v8a', 'armeabi-v7a', 'x86_64', 'x86'):
        if extra not in pref:
            pref.append(extra)
    libs = {}
    for sp in split_apk_paths:
        try:
            z = zipfile.ZipFile(sp)
        except Exception as e:
            return False, 'cannot open split %s: %r' % (os.path.basename(sp), e)
        with z:
            for info in z.infolist():
                name = info.filename
                if not name.startswith('lib/'):
                    continue
                parts = name.split('/')
                if len(parts) < 3 or parts[1] not in pref:
                    continue
                libs.setdefault(parts[1], []).append((name, _read_entry_raw(z, info)))
    chosen = next((abi for abi in pref if abi in libs), None)
    if chosen is None:
        return False, 'no native libs found in split APKs for ABI %r' % (device_abi,)
    out_tmp = os.path.join(work_dir, 'merged.apk')
    if os.path.exists(out_tmp):
        os.remove(out_tmp)
    with zipfile.ZipFile(base_apk) as zin, zipfile.ZipFile(out_tmp, 'w', allowZip64=True) as zout:
        for info in zin.infolist():
            zinfo = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            zinfo.compress_type = info.compress_type
            zinfo.external_attr = info.external_attr
            zout.writestr(zinfo, _read_entry_raw(zin, info))
        for name, data in libs[chosen]:
            if data is None:
                continue
            zinfo = zipfile.ZipInfo(name)
            zinfo.compress_type = zipfile.ZIP_STORED
            zinfo.external_attr = (0o100644 << 16)
            zout.writestr(zinfo, data)
    for _ in range(5):
        try:
            shutil.copy2(out_tmp, out_apk_path)
            break
        except OSError:
            import time
            time.sleep(1)
    else:
        return False, 'could not write merged APK (file locked)'
    return True, 'merged %d native libs (ABI %s)' % (len(libs[chosen]), chosen)


def resign_apk(apk_path, out_apk_path, tools_dir, work_dir):
    """Align and re-sign an APK with the debug.keystore (used for split config APKs).

    'adb install-multiple' requires every APK in the session to share the same
    signing certificate, so after the base is patched (and re-signed) each split
    must be re-signed with the same key too.
    Returns (True, message) or (False, reason).
    """
    zipalign = os.path.join(tools_dir, 'zipalign.exe')
    apksigner_jar = os.path.join(tools_dir, 'apksigner.jar')
    keystore = os.path.join(tools_dir, 'debug.keystore')
    for f in (zipalign, apksigner_jar, keystore):
        if not os.path.isfile(f):
            return False, 'Missing tool: %s' % (f,)
    java = _resolve_java(tools_dir)
    if not os.path.exists(work_dir):
        os.makedirs(work_dir, exist_ok=True)
    return _align_sign_copy(apk_path, out_apk_path, work_dir, zipalign, apksigner_jar, keystore, java)


def patch_apk_slow(apk_path, out_apk_path, tools_dir, work_dir, keep_intermediate=False, fallback_reason=None):
    """Fallback full apktool pipeline (decompile -> patch -> rebuild -> sign)."""
    apktool_jar = os.path.join(tools_dir, 'apktool.jar')
    apksigner_jar = os.path.join(tools_dir, 'apksigner.jar')
    zipalign = os.path.join(tools_dir, 'zipalign.exe')
    keystore = os.path.join(tools_dir, 'debug.keystore')
    java = _resolve_java(tools_dir)

    for f in (apktool_jar, apksigner_jar, zipalign, keystore):
        if not os.path.isfile(f):
            return False, f'Missing tool: {f}'

    decoded_dir = os.path.join(work_dir, 'decoded')
    rebuilt_apk = os.path.join(work_dir, 'unsigned.apk')
    aligned_apk = os.path.join(work_dir, 'aligned.apk')
    signed_apk = os.path.join(work_dir, 'signed.apk')

    if os.path.exists(decoded_dir):
        shutil.rmtree(decoded_dir, ignore_errors=True)

    # 1) Decompile. -r keeps the original resources.arsc (Spotify ships
    #    deliberately broken resource types that break aapt2 recompilation).
    r = run([java, '-jar', apktool_jar, 'd', apk_path, '-o', decoded_dir, '-f', '-r'])
    if r.returncode != 0:
        return False, 'apktool decode failed:\n' + (r.stdout or '')[-1500:]

    # 2) Patch
    try:
        changed = patch_smali_folder(decoded_dir)
    except Exception as e:
        return False, f'Patch error: {e}'
    if changed == 0:
        return False, 'No FLAG_SECURE usages found to patch.'

    # 3) Rebuild
    r = run([java, '-jar', apktool_jar, 'b', decoded_dir, '-o', rebuilt_apk])
    if r.returncode != 0:
        return False, 'apktool build failed:\n' + (r.stdout or '')[-1500:]

    ok, msg = _align_sign_copy(rebuilt_apk, out_apk_path, work_dir, zipalign, apksigner_jar, keystore, java)
    if ok and not keep_intermediate:
        shutil.rmtree(decoded_dir, ignore_errors=True)
        for p in (rebuilt_apk, aligned_apk, signed_apk):
            if os.path.exists(p):
                os.remove(p)
    return ok, msg


if __name__ == '__main__':
    apk = sys.argv[1]
    out = sys.argv[2]
    tools = sys.argv[3] if len(sys.argv) > 3 else 'Tools'
    work = sys.argv[4] if len(sys.argv) > 4 else 'patch_work'
    ok, msg = patch_apk(apk, out, tools, work)
    print(msg)
    sys.exit(0 if ok else 1)
