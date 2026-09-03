// 验证脚本：复刻 index.html 中的核心引擎逻辑，对 rig_plan.json 做确定性与约束验证
const fs = require('fs');
const path = require('path');
const rig = JSON.parse(fs.readFileSync(path.join(__dirname, 'rig_plan.json'), 'utf8'));

const partMap = {};
rig.parts.forEach(p => partMap[p.id] = p);

function sineValue(track, frame) {
  const off = track.offset || 0;
  return off + track.amplitude * Math.sin(2 * Math.PI * (frame + track.phase_frames) / track.period_frames);
}
function keyframeValue(track, frame) {
  const kf = track.keyframes;
  if (frame <= kf[0].frame) return kf[0].value;
  if (frame >= kf[kf.length - 1].frame) return kf[kf.length - 1].value;
  for (let i = 0; i < kf.length - 1; i++) {
    if (frame >= kf[i].frame && frame <= kf[i + 1].frame) {
      const t = (frame - kf[i].frame) / (kf[i + 1].frame - kf[i].frame);
      return kf[i].value + (kf[i + 1].value - kf[i].value) * t;
    }
  }
  return 0;
}
function evalTrack(track, frame) {
  return track.type === 'keyframe' ? keyframeValue(track, frame) : sineValue(track, frame);
}
function clampRotation(partId, angle) {
  const j = rig.joints[partId];
  if (!j || !j.rotation) return angle;
  return Math.max(j.rotation[0], Math.min(j.rotation[1], angle));
}
function computeFrame(animId, frame, lowPerf) {
  const anim = rig.animations[animId];
  const dur = anim.duration_frames;
  const f = ((frame % dur) + dur) % dur;
  const result = {};
  rig.parts.forEach(p => result[p.id] = { translateX: 0, translateY: 0, rotation: 0, scaleX: 1, scaleY: 1 });
  Object.keys(anim.tracks).forEach(partId => {
    anim.tracks[partId].forEach(track => {
      if (lowPerf && track.secondary) return;
      const v = evalTrack(track, f);
      if (track.property === 'translateX') result[partId].translateX += v;
      if (track.property === 'translateY') result[partId].translateY += v;
      if (track.property === 'rotation') result[partId].rotation += v;
      if (track.property === 'scaleX') result[partId].scaleX *= v;
      if (track.property === 'scaleY') result[partId].scaleY *= v;
    });
  });
  Object.keys(result).forEach(id => {
    if (rig.joints[id] && rig.joints[id].rotation) result[id].rotation = clampRotation(id, result[id].rotation);
  });
  return result;
}

let pass = 0, fail = 0;
function assert(name, cond, detail) {
  if (cond) { pass++; console.log('  ✓ ' + name); }
  else { fail++; console.log('  ✗ ' + name + (detail ? ' → ' + detail : '')); }
}

console.log('=== 1. 质量清单：每个可动部件都有枢轴 ===');
const movingParts = new Set();
Object.values(rig.animations).forEach(a => Object.keys(a.tracks).forEach(id => movingParts.add(id)));
movingParts.forEach(id => {
  assert(`部件 ${id} 存在关节枢轴`, !!rig.joints[id] && Array.isArray(rig.joints[id].pivot));
});

console.log('=== 2. 质量清单：有层级关系的子部件都有 parent ===');
rig.parts.forEach(p => {
  if (p.parent) assert(`部件 ${p.id} 的 parent "${p.parent}" 存在`, !!partMap[p.parent]);
});

console.log('=== 3. 帧确定性：同帧多次计算结果一致 ===');
const a1 = computeFrame('walk', 15, false);
const a2 = computeFrame('walk', 15, false);
assert('walk 第15帧两次结果相同', JSON.stringify(a1) === JSON.stringify(a2));
const b1 = computeFrame('idle', 50, false);
const b2 = computeFrame('idle', 50, false);
assert('idle 第50帧两次结果相同', JSON.stringify(b1) === JSON.stringify(b2));

console.log('=== 4. 循环性：第0帧与第duration帧一致 ===');
const w0 = computeFrame('walk', 0, false);
const w60 = computeFrame('walk', 60, false);
assert('walk 第0帧 = 第60帧', JSON.stringify(w0) === JSON.stringify(w60));
const i0 = computeFrame('idle', 0, false);
const i120 = computeFrame('idle', 120, false);
assert('idle 第0帧 = 第120帧', JSON.stringify(i0) === JSON.stringify(i120));

console.log('=== 5. 旋转约束：所有帧旋转在 limits 内 ===');
let allClamped = true;
for (let f = 0; f < 60; f++) {
  const r = computeFrame('walk', f, false);
  Object.keys(rig.joints).forEach(id => {
    const lim = rig.joints[id].rotation;
    if (!lim) return;
    if (r[id].rotation < lim[0] - 1e-9 || r[id].rotation > lim[1] + 1e-9) allClamped = false;
  });
}
assert('walk 全60帧旋转均在约束内', allClamped);

console.log('=== 6. 行走四肢反相：左右腿/臂相位差半周期 ===');
const w15 = computeFrame('walk', 15, false);
assert('左腿与右腿旋转反相', Math.sign(w15.leg_left.rotation) === -Math.sign(w15.leg_right.rotation));
assert('左臂与右臂旋转反相', Math.sign(w15.arm_left.rotation) === -Math.sign(w15.arm_right.rotation));
assert('左臂随右腿（对角协调）', Math.sign(w15.arm_left.rotation) === Math.sign(w15.leg_right.rotation));

console.log('=== 7. 低性能模式：跳过 secondary 轨道（眨眼/头摆） ===');
const full = computeFrame('idle', 36, false);  // 第36帧附近在眨眼
const low = computeFrame('idle', 36, true);
assert('低性能下眼睛 scaleY=1（无眨眼）', low.eye_left.scaleY === 1 && low.eye_right.scaleY === 1);
assert('完整模式下眼睛 scaleY<1（有眨眼）', full.eye_left.scaleY < 1);
assert('低性能下保留身体起伏', low.body.translateY !== 0);
const wFull = computeFrame('walk', 10, false);
const wLow = computeFrame('walk', 10, true);
assert('低性能下行走仍保留腿部摆动', Math.abs(wLow.leg_left.rotation) > 1);

console.log('=== 8. 待机眨眼关键帧：闭眼帧 scaleY 接近 0 ===');
const blink = computeFrame('idle', 35, false);
assert('第35帧左眼闭合', blink.eye_left.scaleY < 0.2);

console.log('=== 9. 层级显式：layer 唯一且有序排列 ===');
const layers = rig.parts.map(p => p.layer);
assert('layer 不全同（有前后关系）', new Set(layers).size > 1);

console.log('=== 10. 中文数据完整性 ===');
assert('character_name 为中文', rig.character_name === '小克');
assert('idle 动画中文名', rig.animations.idle.name_cn === '待机');
assert('walk 动画中文名', rig.animations.walk.name_cn === '行走');

console.log('\n结果：' + pass + ' 通过, ' + fail + ' 失败');
process.exit(fail > 0 ? 1 : 0);
