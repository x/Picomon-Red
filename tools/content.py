"""Event scripts for the Pallet -> Brock slice, in a tiny DSL compiled by build.py.

ops (args comma separated, labels 'name:' and '@name'):
 t TEXT            show text (pokered label `_Foo` or literal `=...`)
 f OBJ,DIR         face (OBJ 0 = player, DIR down/up/left/right/player)
 m OBJ,DIR,N       walk N steps
 X OBJ,TX,FOLLOW   walk horizontally to x=TX (FOLLOW 1: player follows)
 Y OBJ,TY,FOLLOW   walk vertically to y=TY
 a OBJ             walk up to the player
 s FLAG / c FLAG   set / clear flag
 j FLAG,@L         jump if flag set (!FLAG: if clear)
 q AXIS,V,@L       jump if player x (0) / y (1) == V
 g @L              goto
 y @L              yes/no box, jump if NO
 b PARTY,WIN,LOSE  trainer battle (LOSE text => losing is allowed)
 i ITEM,N,FOUND    give item
 p MON,LV          give pokemon      v MON  set text var to mon name
 P MON             show mon pic (P 0 hides)
 h                 heal party        l MAP,X,Y  set blackout point
 r ITEMS...        pokemart           w MAP,X,Y  warp
 e OBJ             '!' bubble         d N        delay frames
 u SONG            music (0 = map default)
 z N               special: 1 nurse, 2 the end, 3 rival walks out of lab
 x                 end
"""

FLAGS = {k: i for i, k in enumerate(
    'WON GOT_STARTER FOLLOWED_OAK BATTLED_RIVAL_LAB GOT_PARCEL GOT_POKEDEX GOT_POTION_SAMPLE GOT_TOWN_MAP '
    'BEAT_ROUTE22_RIVAL BEAT_BROCK GOT_TM34 BALL1 BALL2 BALL3 CHOSE_CHARMANDER CHOSE_SQUIRTLE CHOSE_BULBASAUR '
    'OAK_IN_PALLET OAK_IN_LAB RIVAL_GONE GOT_POKEBALLS RIVAL22_OUT NEVER PEWTER_GUIDED RIVAL_DEX'.split())}
FLAGS['NEVER'] = 22


MAPS = {
    'PalletTown': dict(
        obj={1: dict(cond='OAK_IN_PALLET', script='t _PalletTownOakItsUnsafeText')},
        trig=[(255, 1, '!FOLLOWED_OAK', '''
            u 13
            t =OAK: Hey! Wait!\\nDon't go out!
            e 0
            f 0,down
            s OAK_IN_PALLET
            a 1
            t _PalletTownOakItsUnsafeText
            X 1,9,1
            Y 1,12,1
            X 1,12,1
            Y 1,11,1
            c OAK_IN_PALLET
            m 0,up,1
            w OaksLab,5,11
            s OAK_IN_LAB
            m 0,up,8
            f 1,up
            t _OaksLabRivalFedUpWithWaitingText
            t _OaksLabOakChooseMonText
            t _OaksLabRivalWhatAboutMeText
            t _OaksLabOakBePatientText
            s FOLLOWED_OAK
            u 0
        ''')]),
    'OaksLab': dict(
        obj={
            1: dict(cond='!RIVAL_GONE', script='''
                j GOT_STARTER,@got
                t _OaksLabRivalGrampsIsntAroundText
                x
                got:
                t _OaksLabRivalMyPokemonLooksStrongerText
            '''),
            2: dict(cond='!BALL1', script='''
                j !FOLLOWED_OAK,@balls
                j GOT_STARTER,@last
                P CHARMANDER
                t _OaksLabYouWantCharmanderText
                y @no
                P 0
                v CHARMANDER
                t _OaksLabMonEnergeticText
                p CHARMANDER,5
                t _OaksLabReceivedMonText
                s BALL1
                s CHOSE_CHARMANDER
                s GOT_STARTER
                q 1,4,@below
                m 1,down,1
                g @r
                below:
                m 1,down,2
                m 1,right,3
                m 1,up,1
                r:
                X 1,7,0
                f 1,up
                t _OaksLabRivalIllTakeThisOneText
                s BALL2
                v SQUIRTLE
                t _OaksLabRivalReceivedMonText
                x
                no:
                P 0
                x
                last:
                t _OaksLabLastMonText
                x
                balls:
                t _OaksLabThoseArePokeBallsText
            '''),
            3: dict(cond='!BALL2', script='''
                j !FOLLOWED_OAK,@balls
                j GOT_STARTER,@last
                P SQUIRTLE
                t _OaksLabYouWantSquirtleText
                y @no
                P 0
                v SQUIRTLE
                t _OaksLabMonEnergeticText
                p SQUIRTLE,5
                t _OaksLabReceivedMonText
                s BALL2
                s CHOSE_SQUIRTLE
                s GOT_STARTER
                q 1,4,@below
                m 1,down,1
                g @r
                below:
                m 1,down,2
                m 1,right,4
                m 1,up,1
                r:
                X 1,8,0
                f 1,up
                t _OaksLabRivalIllTakeThisOneText
                s BALL3
                v BULBASAUR
                t _OaksLabRivalReceivedMonText
                x
                no:
                P 0
                x
                last:
                t _OaksLabLastMonText
                x
                balls:
                t _OaksLabThoseArePokeBallsText
            '''),
            4: dict(cond='!BALL3', script='''
                j !FOLLOWED_OAK,@balls
                j GOT_STARTER,@last
                P BULBASAUR
                t _OaksLabYouWantBulbasaurText
                y @no
                P 0
                v BULBASAUR
                t _OaksLabMonEnergeticText
                p BULBASAUR,5
                t _OaksLabReceivedMonText
                s BALL3
                s CHOSE_BULBASAUR
                s GOT_STARTER
                q 0,9,@right
                m 1,down,1
                right:
                m 1,right,2
                X 1,6,0
                Y 1,4,0
                f 1,up
                t _OaksLabRivalIllTakeThisOneText
                s BALL1
                v CHARMANDER
                t _OaksLabRivalReceivedMonText
                x
                no:
                P 0
                x
                last:
                t _OaksLabLastMonText
                x
                balls:
                t _OaksLabThoseArePokeBallsText
            '''),
            5: dict(cond='OAK_IN_LAB', script='''
                j BATTLED_RIVAL_LAB,@raise
                j GOT_STARTER,@fight
                t _OaksLabOak1WhichPokemonDoYouWantText
                x
                fight:
                t _OaksLabOak1YourPokemonCanFightText
                x
                raise:
                t _OaksLabOak1RaiseYourYoungPokemonText
            '''),
            6: dict(cond='!GOT_POKEDEX', script='t _OaksLabPokedexText'),
            7: dict(cond='!GOT_POKEDEX', script='t _OaksLabPokedexText'),
            8: dict(cond='NEVER'),
            9: dict(script='t ~_OaksLabGirlText'),
            10: dict(script='t ~_OaksLabScientistText'),
            11: dict(script='t ~_OaksLabScientistText'),
        },
        trig=[(255, 6, '!BATTLED_RIVAL_LAB', '''
            j GOT_STARTER,@fight
            j !FOLLOWED_OAK,@end
            f 5,down
            t _OaksLabOakDontGoAwayYetText
            m 0,up,1
            x
            fight:
            u 14
            f 1,down
            t _OaksLabRivalIllTakeYouOnText
            a 1
            j CHOSE_SQUIRTLE,@s
            j CHOSE_BULBASAUR,@b
            b party:Rival1/0,_OaksLabRivalIPickedTheWrongPokemonText,_OaksLabRivalAmIGreatOrWhatText
            g @done
            s:
            b party:Rival1/1,_OaksLabRivalIPickedTheWrongPokemonText,_OaksLabRivalAmIGreatOrWhatText
            g @done
            b:
            b party:Rival1/2,_OaksLabRivalIPickedTheWrongPokemonText,_OaksLabRivalAmIGreatOrWhatText
            done:
            h
            s BATTLED_RIVAL_LAB
            t _OaksLabRivalSmellYouLaterText
            m 1,down,5
            s RIVAL_GONE
            u 0
            end:
        ''')]),
}
