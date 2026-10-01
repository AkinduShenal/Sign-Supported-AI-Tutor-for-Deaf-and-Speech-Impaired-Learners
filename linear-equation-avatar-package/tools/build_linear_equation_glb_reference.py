from __future__ import annotations

import json
import math
import struct
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation as R

SOURCE = Path('/mnt/data/avatar_sources/louise_tutor.glb')
OUT = Path('/mnt/data/linear-equation-avatar-package/frontend/public/models/louise_signs_master.glb')

COMP = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
NCOMP = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}


def load_glb(path: Path):
    with path.open('rb') as f:
        magic, version, length = struct.unpack('<4sII', f.read(12))
        if magic != b'glTF' or version != 2:
            raise ValueError('Expected glTF 2.0 binary file')
        gltf = None
        binary = None
        while f.tell() < length:
            chunk_len, chunk_type = struct.unpack('<II', f.read(8))
            data = f.read(chunk_len)
            if chunk_type == 0x4E4F534A:
                gltf = json.loads(data.decode('utf-8'))
            elif chunk_type == 0x004E4942:
                binary = data
    if gltf is None or binary is None:
        raise ValueError('Missing GLB JSON or BIN chunk')
    return gltf, bytearray(binary)


gltf, binary = load_glb(SOURCE)
names = {n.get('name', ''): i for i, n in enumerate(gltf['nodes'])}
parents: dict[int, int] = {}
for i, node in enumerate(gltf['nodes']):
    for child in node.get('children', []):
        parents[child] = i


def accessor(index: int) -> np.ndarray:
    a = gltf['accessors'][index]
    bv = gltf['bufferViews'][a['bufferView']]
    off = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
    count = a['count']
    ncomp = NCOMP[a['type']]
    dtype = np.dtype(COMP[a['componentType']]).newbyteorder('<')
    stride = bv.get('byteStride', ncomp * dtype.itemsize)
    if stride == ncomp * dtype.itemsize:
        return np.frombuffer(binary, dtype=dtype, count=count * ncomp, offset=off).reshape(count, ncomp).copy()
    out = np.empty((count, ncomp), dtype=dtype)
    for j in range(count):
        out[j] = np.frombuffer(binary, dtype=dtype, count=ncomp, offset=off + j * stride)
    return out


def interp_channel(times: np.ndarray, values: np.ndarray, t: float, path: str, interpolation: str) -> np.ndarray:
    if len(times) == 1 or t <= float(times[0]):
        return values[0].copy()
    if t >= float(times[-1]):
        return values[-1].copy()
    idx = int(np.searchsorted(times, t) - 1)
    idx = max(0, min(idx, len(times) - 2))
    if interpolation == 'STEP':
        return values[idx].copy()
    t0, t1 = float(times[idx]), float(times[idx + 1])
    alpha = (t - t0) / max(t1 - t0, 1e-8)
    if path == 'rotation':
        r = R.from_quat([values[idx], values[idx + 1]])
        # Small two-keyframe slerp implemented through relative rotation.
        q0 = r[0]
        rel = q0.inv() * r[1]
        return (q0 * R.from_rotvec(rel.as_rotvec() * alpha)).as_quat().astype(np.float32)
    return ((1 - alpha) * values[idx] + alpha * values[idx + 1]).astype(np.float32)


def sample_animation(name: str, t: float) -> dict[int, dict[str, np.ndarray]]:
    anim = next(a for a in gltf['animations'] if a.get('name') == name)
    result: dict[int, dict[str, np.ndarray]] = {}
    for ch in anim['channels']:
        node = ch['target']['node']
        path = ch['target']['path']
        samp = anim['samplers'][ch['sampler']]
        times = accessor(samp['input']).reshape(-1)
        values = accessor(samp['output'])
        result.setdefault(node, {})[path] = interp_channel(
            times, values, t, path, samp.get('interpolation', 'LINEAR')
        )
    return result


def trs_matrix(t: np.ndarray, q: np.ndarray, s: np.ndarray) -> np.ndarray:
    m = np.eye(4)
    m[:3, :3] = R.from_quat(q).as_matrix() @ np.diag(s)
    m[:3, 3] = t
    return m


IDLE_SAMPLE_T = 1.0 / 30.0
idle_sample = sample_animation('IDLE', IDLE_SAMPLE_T)

# Use IDLE as the neutral body pose. Static node translations/scales remain from the model.
base_rot: dict[int, np.ndarray] = {}
for i, node in enumerate(gltf['nodes']):
    q = idle_sample.get(i, {}).get('rotation', np.array(node.get('rotation', [0, 0, 0, 1]), dtype=np.float32))
    q = np.asarray(q, dtype=float)
    q /= np.linalg.norm(q)
    base_rot[i] = q


def node_trs(i: int, rotations: dict[int, np.ndarray] | None = None):
    n = gltf['nodes'][i]
    t = np.array(n.get('translation', [0, 0, 0]), dtype=float)
    s = np.array(n.get('scale', [1, 1, 1]), dtype=float)
    q = (rotations or base_rot).get(i, base_rot[i])
    return t, np.array(q, dtype=float), s


def world_matrices(rotations: dict[int, np.ndarray] | None = None) -> list[np.ndarray]:
    local = []
    rots = rotations or base_rot
    for i, n in enumerate(gltf['nodes']):
        if 'matrix' in n:
            m = np.array(n['matrix'], dtype=float).reshape(4, 4).T
        else:
            t, q, s = node_trs(i, rots)
            m = trs_matrix(t, q, s)
        local.append(m)
    world: list[np.ndarray | None] = [None] * len(local)
    def calc(i: int):
        if world[i] is not None:
            return world[i]
        p = parents.get(i)
        world[i] = local[i] if p is None else calc(p) @ local[i]
        return world[i]
    for i in range(len(local)):
        calc(i)
    return [x for x in world if x is not None]


base_world = world_matrices()


def solve_arm(side: str, elbow_target, wrist_target) -> tuple[np.ndarray, np.ndarray]:
    arm = names[f'mixamorig8:{side}Arm']
    fore = names[f'mixamorig8:{side}ForeArm']
    hand = names[f'mixamorig8:{side}Hand']
    parent = parents[arm]

    parent_world = base_world[parent]
    ta, qa, sa = node_trs(arm)
    tf, qf, sf = node_trs(fore)
    th, qh, sh = node_trs(hand)
    qa0 = R.from_quat(qa)
    qf0 = R.from_quat(qf)
    et = np.array(elbow_target, dtype=float)
    wt = np.array(wrist_target, dtype=float)

    def evaluate(x):
        qa2 = (qa0 * R.from_rotvec(x[:3])).as_quat()
        qf2 = (qf0 * R.from_rotvec(x[3:])).as_quat()
        wa = parent_world @ trs_matrix(ta, qa2, sa)
        wf = wa @ trs_matrix(tf, qf2, sf)
        wh = wf @ trs_matrix(th, qh, sh)
        return wf[:3, 3], wh[:3, 3], qa2, qf2

    def residual(x):
        elbow, wrist, _, _ = evaluate(x)
        # Strong position fit with a small penalty against extreme rotations.
        return np.r_[10.0 * (elbow - et), 12.0 * (wrist - wt), 0.025 * x]

    fit = least_squares(
        residual,
        np.zeros(6),
        bounds=(-math.pi, math.pi),
        max_nfev=1500,
        ftol=1e-12,
        xtol=1e-12,
        gtol=1e-12,
    )
    elbow, wrist, qa2, qf2 = evaluate(fit.x)
    shoulder = base_world[arm][:3, 3]
    wrist_error = np.linalg.norm(wrist - wt)
    outward_margin = abs(elbow[0]) - abs(shoulder[0])
    if wrist_error > 0.05 or outward_margin < 0.10:
        raise RuntimeError(
            f'{side} arm solve failed natural-pose checks: '
            f'elbow={elbow}, wrist={wrist}, wrist_error={wrist_error:.3f}, '
            f'outward_margin={outward_margin:.3f}'
        )
    return qa2.astype(np.float32), qf2.astype(np.float32)


def normalized(q):
    q = np.asarray(q, dtype=float)
    return (q / np.linalg.norm(q)).astype(np.float32)


def source_rotations(anim: str, t: float) -> dict[int, np.ndarray]:
    s = sample_animation(anim, t)
    return {i: normalized(v['rotation']) for i, v in s.items() if 'rotation' in v}


src_num3 = source_rotations('NUMBER_3', 38 / 30)
src_num4 = source_rotations('NUMBER_4', 38 / 30)
src_num5 = source_rotations('NUMBER_5', 38 / 30)
src_num7 = source_rotations('NUMBER_7', 38 / 30)
src_sub = source_rotations('SUBTRACTION', 38 / 30)
src_add = source_rotations('ADDITION', 38 / 30)
src_eq = source_rotations('EQUATION', 38 / 30)
src_balance = source_rotations('BALANCE', 38 / 30)
src_subst = source_rotations('SUBSTITUTION', 38 / 30)

# Hand/finger node groups.
def finger_nodes(side: str):
    prefix = f'mixamorig8:{side}Hand'
    return [i for name, i in names.items() if name.startswith(prefix) and name != f'mixamorig8:{side}Hand']

finger_group = {side: finger_nodes(side) for side in ('Left', 'Right')}
hand_node = {side: names[f'mixamorig8:{side}Hand'] for side in ('Left', 'Right')}
arm_node = {side: names[f'mixamorig8:{side}Arm'] for side in ('Left', 'Right')}
fore_node = {side: names[f'mixamorig8:{side}ForeArm'] for side in ('Left', 'Right')}


def copy_hand_template(pose: dict[int, np.ndarray], side: str, template: dict[int, np.ndarray]):
    hn = hand_node[side]
    if hn in template:
        pose[hn] = template[hn].copy()
    for ni in finger_group[side]:
        if ni in template:
            pose[ni] = template[ni].copy()


def copy_fingers(pose: dict[int, np.ndarray], side: str, template: dict[int, np.ndarray]):
    for ni in finger_group[side]:
        if ni in template:
            pose[ni] = template[ni].copy()


def finger_shape_template(side: str, extended: set[str]) -> dict[int, np.ndarray]:
    # Build finger shapes from proven open/closed rotations already present in the source GLB.
    open_template = src_num5 if side == 'Right' else src_num7
    closed_template = src_sub
    result = {}
    for finger in ('Thumb', 'Index', 'Middle', 'Ring', 'Pinky'):
        prefix = f'mixamorig8:{side}Hand{finger}'
        for name, ni in names.items():
            if name.startswith(prefix):
                source = open_template if finger in extended else closed_template
                if ni in source:
                    result[ni] = source[ni].copy()
    return result


def arm_pose(pose: dict[int, np.ndarray], side: str, elbow, wrist, hand_template=None):
    qa, qf = solve_arm(side, elbow, wrist)
    pose[arm_node[side]] = qa
    pose[fore_node[side]] = qf
    if hand_template is not None and hand_node[side] in hand_template:
        pose[hand_node[side]] = hand_template[hand_node[side]].copy()


def make_pose() -> dict[int, np.ndarray]:
    return {i: q.copy() for i, q in base_rot.items()}


def mirror_x(x):
    return -x

# Shared natural signing-space targets. Elbows are explicitly farther outward than wrists.
L_OUT = (0.37, 1.24, 0.07)
R_OUT = (-0.37, 1.24, 0.07)
L_CHEST = (0.22, 1.18, 0.22)
R_CHEST = (-0.22, 1.18, 0.22)
L_WIDE = (0.34, 1.18, 0.21)
R_WIDE = (-0.34, 1.18, 0.21)
L_CENTER = (0.14, 1.18, 0.23)
R_CENTER = (-0.14, 1.18, 0.23)


def equation_pose(wide=False):
    p = make_pose()
    arm_pose(p, 'Left', L_OUT, L_WIDE if wide else L_CHEST, src_eq)
    arm_pose(p, 'Right', R_OUT, R_WIDE if wide else R_CHEST, src_eq)
    copy_fingers(p, 'Left', src_eq)
    copy_fingers(p, 'Right', src_eq)
    return p


def both_sides_pose(wide=True):
    p = make_pose()
    left_wrist = (0.38 if wide else 0.20, 1.16, 0.22)
    right_wrist = (-0.38 if wide else -0.20, 1.16, 0.22)
    arm_pose(p, 'Left', (0.43, 1.23, 0.06), left_wrist, src_num5)
    arm_pose(p, 'Right', (-0.43, 1.23, 0.06), right_wrist, src_num5)
    copy_fingers(p, 'Left', finger_shape_template('Left', set(('Thumb','Index','Middle','Ring','Pinky'))))
    copy_fingers(p, 'Right', finger_shape_template('Right', set(('Thumb','Index','Middle','Ring','Pinky'))))
    return p


def variable_pose(high=False):
    p = make_pose()
    y = 1.28 if high else 1.20
    arm_pose(p, 'Right', (-0.38, 1.24, 0.07), (-0.20, y, 0.23), src_add)
    copy_fingers(p, 'Right', finger_shape_template('Right', {'Index'}))
    return p


def addition_pose(inward=False):
    p = make_pose()
    arm_pose(p, 'Left', (0.38, 1.23, 0.07), (0.22, 1.16, 0.22), src_num5)
    right_wrist = (-0.08 if inward else -0.25, 1.22, 0.24)
    arm_pose(p, 'Right', (-0.39, 1.26, 0.07), right_wrist, src_add)
    copy_fingers(p, 'Left', finger_shape_template('Left', set(('Thumb','Index','Middle','Ring','Pinky'))))
    copy_fingers(p, 'Right', finger_shape_template('Right', {'Index'}))
    return p


def subtraction_pose(outward=False):
    p = make_pose()
    arm_pose(p, 'Left', (0.38, 1.23, 0.07), (0.20, 1.15, 0.22), src_num5)
    right_wrist = (-0.36 if outward else -0.12, 1.18, 0.24)
    arm_pose(p, 'Right', (-0.43, 1.24, 0.08), right_wrist, src_sub)
    copy_fingers(p, 'Left', finger_shape_template('Left', set(('Thumb','Index','Middle','Ring','Pinky'))))
    copy_fingers(p, 'Right', finger_shape_template('Right', set()))
    return p


def substitution_pose(close=True):
    p = make_pose()
    left_wrist = (0.18, 1.17, 0.22)
    right_wrist = (-0.10 if close else -0.30, 1.20, 0.24)
    arm_pose(p, 'Left', (0.39, 1.23, 0.06), left_wrist, src_subst)
    arm_pose(p, 'Right', (-0.40, 1.24, 0.07), right_wrist, src_subst)
    copy_fingers(p, 'Left', finger_shape_template('Left', {'Index','Middle','Ring','Pinky'}))
    copy_fingers(p, 'Right', finger_shape_template('Right', {'Index'}))
    return p


def multiply_pose(cross=False):
    p = make_pose()
    lw = (0.07 if cross else 0.20, 1.20, 0.24)
    rw = (-0.07 if cross else -0.20, 1.20, 0.24)
    arm_pose(p, 'Left', (0.39, 1.25, 0.07), lw, src_add)
    arm_pose(p, 'Right', (-0.39, 1.25, 0.07), rw, src_add)
    copy_fingers(p, 'Left', finger_shape_template('Left', {'Index'}))
    copy_fingers(p, 'Right', finger_shape_template('Right', {'Index'}))
    return p


def division_pose(low=False):
    p = make_pose()
    arm_pose(p, 'Left', (0.38, 1.23, 0.07), (0.20, 1.18, 0.22), src_num5)
    y = 1.10 if low else 1.30
    arm_pose(p, 'Right', (-0.39, 1.25, 0.07), (-0.18, y, 0.24), src_add)
    copy_fingers(p, 'Left', finger_shape_template('Left', set(('Thumb','Index','Middle','Ring','Pinky'))))
    copy_fingers(p, 'Right', finger_shape_template('Right', {'Index'}))
    return p


def solve_pose(opened=False):
    p = make_pose()
    x = 0.34 if opened else 0.16
    arm_pose(p, 'Left', (0.40, 1.22, 0.06), (x, 1.12, 0.22), src_num5)
    arm_pose(p, 'Right', (-0.40, 1.22, 0.06), (-x, 1.12, 0.22), src_num5)
    copy_fingers(p, 'Left', finger_shape_template('Left', set(('Thumb','Index','Middle','Ring','Pinky'))))
    copy_fingers(p, 'Right', finger_shape_template('Right', set(('Thumb','Index','Middle','Ring','Pinky'))))
    return p


def answer_pose(forward=False):
    p = make_pose()
    z = 0.30 if forward else 0.20
    arm_pose(p, 'Right', (-0.38, 1.24, 0.07), (-0.20, 1.20, z), src_num5)
    copy_fingers(p, 'Right', finger_shape_template('Right', set(('Thumb','Index','Middle','Ring','Pinky'))))
    return p


def number_pose(value: int):
    p = make_pose()
    if value <= 5:
        right_count = value
        left_count = 0
    else:
        left_count = 5
        right_count = value - 5

    if right_count >= 0:
        arm_pose(p, 'Right', (-0.39, 1.23, 0.06), (-0.27, 1.20, 0.20), src_num5)
        if right_count == 0:
            ext = set()
        else:
            order = ['Index', 'Middle', 'Ring', 'Pinky', 'Thumb']
            ext = set(order[:right_count])
        copy_fingers(p, 'Right', finger_shape_template('Right', ext))

    if left_count:
        arm_pose(p, 'Left', (0.39, 1.23, 0.06), (0.27, 1.20, 0.20), src_num7)
        copy_fingers(p, 'Left', finger_shape_template('Left', set(('Thumb','Index','Middle','Ring','Pinky'))))
    return p


def sequence(*poses):
    neutral = make_pose()
    # 2-second-ish clip: neutral -> pose(s) -> short hold -> neutral.
    if len(poses) == 1:
        return [
            (0.00, neutral),
            (0.28, neutral),
            (0.62, poses[0]),
            (1.15, poses[0]),
            (1.50, neutral),
            (1.80, neutral),
        ]
    if len(poses) == 2:
        return [
            (0.00, neutral),
            (0.24, neutral),
            (0.58, poses[0]),
            (0.95, poses[1]),
            (1.25, poses[1]),
            (1.58, neutral),
            (1.85, neutral),
        ]
    raise ValueError('sequence expects one or two sign poses')


clips: dict[str, list[tuple[float, dict[int, np.ndarray]]]] = {
    'IDLE': [(0.0, make_pose()), (1.5, make_pose())],
    'EQUATION': sequence(equation_pose(False), equation_pose(True)),
    'BALANCE': sequence(both_sides_pose(False), both_sides_pose(True)),
    'BOTH_SIDES': sequence(both_sides_pose(False), both_sides_pose(True)),
    'VARIABLE': sequence(variable_pose(False), variable_pose(True)),
    'ADDITION': sequence(addition_pose(False), addition_pose(True)),
    'SUBTRACTION': sequence(subtraction_pose(False), subtraction_pose(True)),
    'MULTIPLICATION': sequence(multiply_pose(False), multiply_pose(True)),
    'DIVISION': sequence(division_pose(False), division_pose(True)),
    'SUBSTITUTION': sequence(substitution_pose(False), substitution_pose(True)),
    'SOLVE': sequence(solve_pose(False), solve_pose(True)),
    'ANSWER': sequence(answer_pose(False), answer_pose(True)),
}
for n in range(10):
    clips[f'NUMBER_{n}'] = sequence(number_pose(n))

# Only nodes with a useful rotation channel need animation. This includes all bones
# represented by the neutral IDLE action, so each clip begins from the same body pose.
rotation_nodes = sorted(i for i, v in idle_sample.items() if 'rotation' in v)


def pad4(buf: bytearray):
    while len(buf) % 4:
        buf.append(0)


def add_float_accessor(arr: np.ndarray, gltf_type: str, include_minmax=False) -> int:
    global binary
    arr = np.asarray(arr, dtype='<f4')
    pad4(binary)
    offset = len(binary)
    raw = arr.tobytes(order='C')
    binary.extend(raw)
    bv_index = len(gltf.setdefault('bufferViews', []))
    gltf['bufferViews'].append({'buffer': 0, 'byteOffset': offset, 'byteLength': len(raw)})
    acc = {
        'bufferView': bv_index,
        'byteOffset': 0,
        'componentType': 5126,
        'count': int(arr.shape[0]),
        'type': gltf_type,
    }
    if include_minmax:
        vals = arr.reshape(arr.shape[0], -1)
        acc['min'] = vals.min(axis=0).astype(float).tolist()
        acc['max'] = vals.max(axis=0).astype(float).tolist()
    ai = len(gltf.setdefault('accessors', []))
    gltf['accessors'].append(acc)
    return ai


def q_continuous(values):
    out = []
    prev = None
    for q in values:
        q = normalized(q)
        if prev is not None and np.dot(prev, q) < 0:
            q = -q
        out.append(q)
        prev = q
    return np.asarray(out, dtype=np.float32)


new_anims = []
for clip_name, keys in clips.items():
    times = np.array([t for t, _ in keys], dtype=np.float32).reshape(-1, 1)
    input_accessor = add_float_accessor(times, 'SCALAR', include_minmax=True)
    channels = []
    samplers = []
    for node in rotation_nodes:
        values = q_continuous([pose[node] for _, pose in keys])
        output_accessor = add_float_accessor(values, 'VEC4')
        samp_index = len(samplers)
        samplers.append({
            'input': input_accessor,
            'output': output_accessor,
            'interpolation': 'LINEAR',
        })
        channels.append({
            'sampler': samp_index,
            'target': {'node': node, 'path': 'rotation'},
        })
    new_anims.append({'name': clip_name, 'channels': channels, 'samplers': samplers})

# Replace the old procedural animation set entirely.
gltf['animations'] = new_anims
gltf['buffers'][0]['byteLength'] = len(binary)

OUT.parent.mkdir(parents=True, exist_ok=True)
json_raw = json.dumps(gltf, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
while len(json_raw) % 4:
    json_raw += b' '
pad4(binary)
length = 12 + 8 + len(json_raw) + 8 + len(binary)
with OUT.open('wb') as f:
    f.write(struct.pack('<4sII', b'glTF', 2, length))
    f.write(struct.pack('<II', len(json_raw), 0x4E4F534A))
    f.write(json_raw)
    f.write(struct.pack('<II', len(binary), 0x004E4942))
    f.write(binary)

print('Created:', OUT)
print('Animations:', ', '.join(a['name'] for a in new_anims))
print('Animation count:', len(new_anims))
print('Size:', OUT.stat().st_size)

# Save a machine-readable report of elbow/wrist positions at representative mid poses.
report = {}
for name, keys in clips.items():
    pose = keys[len(keys)//2][1]
    w = world_matrices(pose)
    report[name] = {}
    for side in ('Left', 'Right'):
        elbow = w[fore_node[side]][:3, 3]
        wrist = w[hand_node[side]][:3, 3]
        shoulder = w[arm_node[side]][:3, 3]
        report[name][side] = {
            'shoulder': [round(float(x), 4) for x in shoulder],
            'elbow': [round(float(x), 4) for x in elbow],
            'wrist': [round(float(x), 4) for x in wrist],
            'elbow_outward_from_shoulder': bool(abs(elbow[0]) > abs(shoulder[0]) + 0.05),
        }
report_path = OUT.parents[3] / 'pose_report.json'
report_path.write_text(json.dumps(report, indent=2))
print('Pose report:', report_path)
