local L=dofile("../tests/lib.lua")
return {
 L.start("Gym1",4,6,{},"mk(7,60,split'55,0,0,0')"), {"wait",3}, {"lua","P[1].n='sq'"},
 {"hold","left",3}, {"press","x"}, {"until","bat","x",600}, {"lua","printh('FIGHT1 '..tostr(bat))"},
 {"until","not bat and not busy","x",20000}, {"lua","local e=E[2] printh('TF '..e.tf..' '..tostr(F[e.tf]))"},
 {"press","x"}, {"wait",30}, {"lua","printh('FIGHT2 '..tostr(bat))"},
}
