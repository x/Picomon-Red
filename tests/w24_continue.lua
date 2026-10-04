-- run after w23: continue from the title loads the save
return {
 {"wait",60},{"press","x"},{"wait",20},{"shot","continue"},{"press","x"},{"wait",90},{"lua","printh('loaded map '..cm..' '..pl.x..','..pl.y..' party '..#P)"},{"shot","loaded"},
}
