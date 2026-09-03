// 桌面收纳盒（四隔层）— OpenSCAD 参数化源文件
// 外廓 180 × 120 × 35 mm，壁厚 2.4 mm，2×2 十字隔层
// 单位: mm
// 用法: openscad -o desk_organizer_4comp.stl desk_organizer.scad

outer_length = 180;
outer_width  = 120;
outer_height = 35;
wall   = 2.4;
bottom = 2.4;
div    = 2.4;
nx = 2;
ny = 2;

$fn = 32;

difference() {
    // 外箱体
    translate([0, 0, outer_height/2])
        cube([outer_length, outer_width, outer_height], center=true);

    // 内腔（开口朝上，从顶面挖到底板上表面）
    translate([0, 0, (bottom + outer_height)/2])
        cube([outer_length - 2*wall, outer_width - 2*wall, outer_height - bottom], center=true);
}

// X 方向隔墙（分隔 Y），ny-1 道
inner_l = outer_length - 2*wall;
inner_w = outer_width - 2*wall;
inner_h = outer_height - bottom;
for (i = [1:ny-1])
    translate([
        0,
        -inner_w/2 + i*(inner_w/ny),
        (bottom + outer_height)/2
    ])
    cube([inner_l, div, inner_h], center=true);

// Y 方向隔墙（分隔 X），nx-1 道
for (i = [1:nx-1])
    translate([
        -inner_l/2 + i*(inner_l/nx),
        0,
        (bottom + outer_height)/2
    ])
    cube([div, inner_w, inner_h], center=true);
