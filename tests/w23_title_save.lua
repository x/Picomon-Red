-- title, new game, step, save from the start menu (any old save is cleared first)
return {
 {"lua","poke(0x5e00,0)"},
 {"wait",100},{"shot","title1"},{"wait",130},{"shot","title2"},
 {"press","x"},{"wait",90},{"lua","printh('newgame map '..cm..' '..pl.x..','..pl.y..' party '..#P)"},
 {"hold","left",8},{"wait",30},{"lua","printh('moved map '..cm..' '..pl.x..','..pl.y..' party '..#P)"},
 {"press","z"},{"wait",10},{"shot","startmenu"},{"press","down"},{"wait",4},{"press","x"},{"wait",40},{"shot","saved"},
 {"press","x"},{"wait",20},{"lua","printh('save byte '..peek(0x5e00))"},
}
