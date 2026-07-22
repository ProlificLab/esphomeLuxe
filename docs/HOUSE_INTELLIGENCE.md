# Qualification du narrateur de la maison

Le narrateur construit un texte deterministe depuis quatre domaines normalises:
Victron, Proxmox, OPNsense et Frigate. Le modele conversationnel ne produit pas
les faits et ne recoit aucun outil d'infrastructure. Les seules actions du
package sont les deux scripts d'annonce bornes.

## Fraicheur fermee

- Frigate: 30 secondes sur les trois cameras sentinelles.
- OPNsense: 120 secondes depuis `generated_at` du endpoint GET.
- Proxmox: 300 secondes sur chacune des quatre metriques requises.
- Victron: 300 secondes sur chacune des quatre metriques requises.

Pour Victron, Proxmox et Frigate, l'age expose est celui de la source requise la
plus ancienne. Une seule metrique active ne peut donc plus masquer ses pairs
figes. Une source absente ou trop vieille active son garde `stale`; le narrateur
dit alors que les donnees sont perimees sans lire leurs valeurs.

## Protocole physique

Copier `docs/house-intelligence-record.example.json` dans `release/`. Commencer
par les quatre sources reelles fraiches, verifier les comptes camera et
multi-WAN, puis ecouter une narration combinee. Mesurer le temps jusqu'au retour
du lecteur a `idle`.

Dans une fenetre de maintenance, rendre indisponible une seule source de
telemetrie a la fois, sans appeler de service de controle. Verifier son seuil,
le refus vocal de citer les anciennes valeurs, puis sa recuperation. Pour
Victron, Proxmox et Frigate, figer aussi une seule metrique requise pendant que
les autres continuent afin de prouver que la plus ancienne gagne. Restaurer et
revalider toutes les sources avant de passer a la suivante.

Verifier separement que l'identite OPNsense accepte le GET ferme, refuse une API
interdite en `403` et le POST en `405`; que Proxmox ne possede que les privileges
Audit; que Frigate utilise le role `viewer` avec ses controles desactives; et
qu'Assist n'expose que les faits normalises et le narrateur. Ne placer aucun
secret, jeton, URL signee ou sortie brute dans le dossier de preuve.

## Validation

Le dossier doit contenir les 23 scenarios, au moins cinq narrations, les quatre
cas frais, perimes et recuperes, les trois tests de source la plus ancienne et
les deux refus OPNsense. L'etat final exige les quatre gardes `off`, le lecteur
`idle`, la voix `waiting/healthy` et une file vide.

```sh
version="REPLACE_WITH_VERSION"
record="release/house-intelligence-$version.json"
python3 scripts/check_house_intelligence_evidence.py "$record" \
  --expected-version "$version" \
  --expected-firmware-sha256 "$(sha256sum "release/muse-luxe-$version.ota.bin" | cut -d' ' -f1)" \
  --expected-package-sha256 "$(sha256sum home-assistant/packages/muse_house_intelligence.yaml | cut -d' ' -f1)" \
  --expected-opnsense-controller-sha256 "$(sha256sum opnsense/muse-readonly/controllers/OPNsense/Muse/Api/StatusController.php | cut -d' ' -f1)" \
  --expected-opnsense-acl-sha256 "$(sha256sum opnsense/muse-readonly/models/OPNsense/Muse/ACL/ACL.xml | cut -d' ' -f1)" \
  --expected-proxmox-policy-sha256 "$(sha256sum scripts/check_proxmox_permissions.py | cut -d' ' -f1)" \
  --expected-frigate-policy-sha256 "$(sha256sum scripts/check_frigate_readonly.py | cut -d' ' -f1)"
```

Lier ensuite le hash du dossier valide dans
`house_intelligence_freshness.evidence` sous la forme
`sha256:DIGEST house-intelligence-VERSION.json`. Ce guide et son exemple ne
constituent pas une preuve physique.
