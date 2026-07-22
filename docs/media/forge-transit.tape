# VHS tape — records the Forge Line demo transit as the README's hero GIF.
# Install vhs (https://github.com/charmbracelet/vhs):  scoop install vhs
# Then:  vhs docs/media/forge-transit.tape
# Output lands beside this file; reference it at the top of README.md.

Output docs/media/forge-transit.gif

Set FontSize 16
Set Width 1400
Set Height 800
Set Theme "Catppuccin Mocha"
Set Padding 12

Type "knivves vault"
Enter
Sleep 2.5s      # boot: the vault door holds the brand, bolts retract, leaves part
Type "2"
Sleep 1s        # arrival door into the Forge Line
Sleep 8.5s      # the demo transit: stamps, gates, filing
Type "4"
Sleep 2.5s      # the Ledger's instruments
Type "q"
