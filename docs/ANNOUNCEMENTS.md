# Qualification des annonces routees

Le script `script.muse_announce` est le seul chemin de lecture des annonces
Muse. Sa file est bornee a 25 appels. Une annonce normale attend au maximum dix
minutes la fin de la musique, d'une reponse Assist ou d'une conversation
continue; elle est abandonnee si l'enceinte reste occupee. Une annonce urgente
arrete la lecture en cours avant de parler.

Les volumes sont `0.60` le jour, `0.25` la nuit et `0.75` en urgence. Le volume
precedent est restaure apres chaque tentative, y compris si le carillon ou Piper
echoue. Le carillon est optionnel, mais lorsqu'il est demande il precede le TTS.

Le routage est volontairement ferme a
`media_player.raspiaudio_muse_luxe` tant qu'un second satellite n'est pas
qualifie. Le routage par piece, etage ou personne devra etendre simultanement le
package, le validateur et cette qualification; aucune destination externe n'est
autorisee implicitement.

## Protocole physique

Copier `docs/announcement-record.example.json` dans `release/`, puis observer
les quinze scenarios sans modifier leurs noms. Utiliser au moins dix livraisons
reussies, trois messages FIFO et trois attentes normales distinctes. Injecter
exactement une expiration occupee, une interruption urgente, une erreur Piper et
une erreur de carillon. Verifier le retour au volume precedent apres toutes les
livraisons et les deux erreurs.

Le dossier final doit montrer une file vide, le lecteur `idle`, la voix
`waiting/healthy` et la conversation continue fermee. Il doit etre date de moins
de trente jours et lie a la version, au SHA-256 OTA et au SHA-256 du package
`home-assistant/packages/muse_luxe.yaml` exacts.

```sh
version="REPLACE_WITH_VERSION"
python3 scripts/check_announcement_evidence.py \
  "release/announcement-$version.json" \
  --expected-version "$version" \
  --expected-firmware-sha256 "$(sha256sum "release/muse-luxe-$version.ota.bin" | cut -d' ' -f1)" \
  --expected-package-sha256 "$(sha256sum home-assistant/packages/muse_luxe.yaml | cut -d' ' -f1)"
```

Enfin, calculer le SHA-256 du dossier valide et le placer dans
`announcement_routing_queue.evidence` sous la forme
`sha256:DIGEST announcement-VERSION.json`. Cette documentation ne constitue pas
une preuve physique: la porte reste fermee jusqu'aux observations reelles.
