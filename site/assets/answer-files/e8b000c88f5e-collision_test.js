function V(x,y,z){var o={x:x||0,y:y||0,z:z||0}; o.set=function(a,b,c){o.x=a;o.y=b;o.z=c;return o;}; return o;}
// 与 index.html 中一致的实现（含 eps 余量）
function sphereAabb(center, radius, boxPos, half, outPen) {
  var cx = Math.max(boxPos.x - half.x, Math.min(center.x, boxPos.x + half.x));
  var cz = Math.max(boxPos.z - half.z, Math.min(center.z, boxPos.z + half.z));
  var dx = center.x - cx, dz = center.z - cz;
  var distSq = dx*dx + dz*dz;
  if (distSq < radius*radius) {
    var dist = Math.sqrt(distSq) || 0.0001;
    var eps = 1e-3;
    if (distSq < 1e-6) {
      var ox = half.x - Math.abs(center.x - boxPos.x);
      var oz = half.z - Math.abs(center.z - boxPos.z);
      if (ox < oz) outPen.set((center.x<boxPos.x?-1:1)*(radius+ox+eps),0,0);
      else outPen.set(0,0,(center.z<boxPos.z?-1:1)*(radius+oz+eps));
    } else {
      var push = radius - dist + eps;
      outPen.set(dx/dist*push, 0, dz/dist*push);
    }
    return true;
  }
  return false;
}
var pass=0,fail=0;
function ok(n,c){if(c){pass++;console.log('PASS',n);}else{fail++;console.log('FAIL',n);}}
ok('球在箱子外不碰撞', sphereAabb(V(10,0,0),0.9,V(0,1.5,0),V(1.5,1.5,1.5),V())===false);
ok('球心投影在箱子内时碰撞', sphereAabb(V(0,0,0),0.9,V(0,1.5,0),V(1.5,1.5,1.5),V())===true);
var pen=V(); sphereAabb(V(2.0,0,0),0.9,V(0,1.5,0),V(1.5,1.5,1.5),pen);
ok('右侧贴近时推出方向+x', pen.x>0 && Math.abs(pen.z)<1e-6);
pen=V(); sphereAabb(V(-2.0,0,0),0.9,V(0,1.5,0),V(1.5,1.5,1.5),pen);
ok('左侧贴近时推出方向-x', pen.x<0);
pen=V(); var c=V(2.0,0,0); sphereAabb(c,0.9,V(0,1.5,0),V(1.5,1.5,1.5),pen);
c.x+=pen.x; c.z+=pen.z;
ok('推出后不再相交（含eps）', sphereAabb(c,0.9,V(0,1.5,0),V(1.5,1.5,1.5),V())===false);
function ss(a,r1,b,r2){var dx=a.x-b.x,dz=a.z-b.z;return dx*dx+dz*dz<(r1+r2)*(r1+r2);}
ok('金币在拾取范围内', ss(V(0,0,0),0.9,V(1.0,0,0),0.7)===true);
ok('金币在拾取范围外', ss(V(0,0,0),0.9,V(3.0,0,0),0.7)===false);
var limit=40-0.9-0.5, px=50; if(px>limit)px=limit;
ok('边界钳制生效', px===limit);
pen=V(); sphereAabb(V(2.0,0,2.0),0.9,V(0,1.5,0),V(1.5,1.5,1.5),pen);
ok('角部碰撞推出同时含x/z分量', pen.x>0 && pen.z>0);
// 连续多帧模拟：把球从箱子正右方持续向左推，验证不会穿透到左侧
var sim=V(2.0,0,0); var stuck=0;
for(var f=0;f<120;f++){
  sim.x -= 0.05; // 向左移动
  var p=V();
  if(sphereAabb(sim,0.9,V(0,1.5,0),V(1.5,1.5,1.5),p)){ sim.x+=p.x; sim.z+=p.z; stuck++; }
}
ok('120帧挤压后球仍在箱子右侧(未穿透)', sim.x >= 1.5);
console.log('---'); console.log('通过 '+pass+' / '+(pass+fail));
if(fail>0) process.exit(1);
