
// WeldGuard - editable conceptual 3D CAD model
// Units: millimetres. Open with OpenSCAD; use F5 to preview, F6 to render.
// Dimensions are illustrative starting dimensions, NOT fabrication-approved.

$fn = 48;

// Main reference dimensions
bench_w = 1500;
bench_d = 750;
bench_h = 850;
booth_w = 1500;
booth_d = 750;
booth_h = 1500;

// ---------- Reusable parts ----------
module tube_between(p1, p2, r=22) {
    v = [p2[0]-p1[0], p2[1]-p1[1], p2[2]-p1[2]];
    len = norm(v);
    translate(p1)
        rotate(a=acos(v[2]/len), v=[-v[1],v[0],0])
            cylinder(h=len, r=r);
}

module post(x,y,z0,z1,sz=35) {
    translate([x,y,z0]) cube([sz,sz,z1-z0]);
}

module panel(x,y,z,w,h,t=18) {
    translate([x,y,z]) cube([w,t,h]);
}

module hood() {
    // Capture canopy with tapered sides and short neck
    color([0.12,0.30,0.55]) {
        translate([-250,-80,1450])
            hull() {
                translate([0,0,0]) cube([500,160,8]);
                translate([110,45,145]) cube([280,70,8]);
            }
        translate([-70,-35,1585]) cube([140,70,80]);
    }
}

module duct_and_fan() {
    color([0.68,0.73,0.78]) {
        // vertical riser and overhead extraction duct
        translate([-70,0,1660]) cylinder(h=170,r=55);
        translate([-70,0,1830]) rotate([0,90,0]) cylinder(h=720,r=55);
        translate([650,0,1830]) rotate([0,90,0]) cylinder(h=180,r=55);
    }
    // fan housing at duct end
    color([0.10,0.28,0.52]) {
        translate([820,-100,1740]) cube([210,200,180]);
        translate([1025,0,1830]) rotate([0,90,0]) cylinder(h=70,r=75);
        translate([1095,-115,1715]) cube([35,230,230]);
    }
    // fan support stand
    color([0.20,0.23,0.27]) {
        post(850,-115,0,1715,35);
        post(1010,80,0,1715,35);
        translate([825,-135,0]) cube([245,250,35]);
    }
}

module workbench() {
    color([0.35,0.40,0.45]) {
        translate([-750,-375,bench_h-45]) cube([bench_w,bench_d,45]);
        post(-720,-345,0,bench_h-45,35);
        post(685,-345,0,bench_h-45,35);
        post(-720,310,0,bench_h-45,35);
        post(685,310,0,bench_h-45,35);
        translate([-750,-375,bench_h-100]) cube([bench_w,35,35]);
        translate([-750,340,bench_h-100]) cube([bench_w,35,35]);
    }
    // workpiece and vise
    color([0.68,0.72,0.76]) {
        translate([-160,-100,bench_h]) cube([320,200,18]);
        translate([300,-160,bench_h]) cube([180,90,65]);
        translate([330,-70,bench_h+25]) cube([120,25,18]);
    }
}

module booth_panels() {
    color([0.30,0.36,0.42,0.55]) {
        // back and side splash panels
        panel(-750,350,bench_h,1500,booth_h-bench_h,22);
        translate([-750,-375,bench_h]) cube([22,725,booth_h-bench_h]);
        translate([728,-375,bench_h]) cube([22,725,booth_h-bench_h]);
    }
    color([0.20,0.24,0.29]) {
        // booth frame
        post(-750,330,0,booth_h,30);
        post(720,330,0,booth_h,30);
        post(-750,-375,0,booth_h,30);
        post(720,-375,0,booth_h,30);
        translate([-750,330,booth_h-30]) cube([1500,30,30]);
    }
}

module controller_box() {
    // mounted operator controller at front-right
    color([0.78,0.81,0.84]) {
        translate([520,-405,1050]) cube([250,85,300]);
    }
    color([0.04,0.08,0.13]) {
        translate([565,-414,1220]) cube([160,8,75]); // display
    }
    // status lamps: green, amber, red
    color([0.05,0.85,0.35]) translate([575,-420,1150]) sphere(r=18);
    color([1.0,0.65,0.05]) translate([635,-420,1150]) sphere(r=18);
    color([0.95,0.12,0.12]) translate([695,-420,1150]) sphere(r=18);
    // buzzer grille
    color([0.10,0.12,0.15])
        translate([730,-420,1080]) cylinder(h=8,r=22);
}

module particulate_sensor() {
    // small sensor enclosure mounted near the breathing-zone / source area
    color([0.82,0.84,0.86]) {
        translate([410,-300,1050]) cube([110,75,100]);
    }
    color([0.12,0.15,0.18]) {
        for (i=[0:4])
            translate([425+i*16,-306,1100]) cube([5,5,32]);
    }
}

module warning_stack() {
    translate([670,-365,1400]) {
        color([0.12,0.14,0.16]) cylinder(h=180,r=18);
        color([0.05,0.8,0.25]) translate([0,0,25]) cylinder(h=38,r=22);
        color([1.0,0.65,0.05]) translate([0,0,68]) cylinder(h=38,r=22);
        color([0.9,0.08,0.08]) translate([0,0,111]) cylinder(h=38,r=22);
    }
}

module airflow_arrows() {
    // Stylized airflow direction markers inside duct (visual aid only)
    color([0.10,0.65,0.95,0.8]) {
        for (x=[-10,230,470]) {
            translate([x,0,1830]) rotate([0,90,0]) cylinder(h=75,r1=8,r2=2);
            translate([x+75,0,1830]) rotate([0,90,0]) cylinder(h=25,r1=18,r2=0);
        }
    }
}

// ---------- Full assembly ----------
module weldguard_assembly() {
    workbench();
    booth_panels();
    hood();
    duct_and_fan();
    controller_box();
    particulate_sensor();
    warning_stack();
    airflow_arrows();
}

weldguard_assembly();
