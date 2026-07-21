# Programme Muse Luxe / Okay Hal

Feuille de route du fork ProlificLab de Raspiaudio esphomeLuxe. L'objectif est
de transformer la Muse Luxe en terminal vocal et audio familial fiable, local
et recuperable, sans demander a l'ESP32 de porter les traitements lourds.

## Etat d'implementation

| Etape | Etat |
| --- | --- |
| Reference `hal.6` | Archivee et conservee comme rollback publie |
| Resilience `hal.7` | `hal.7-alpha.3` sur l'enceinte canari |
| Reproductibilite | Build, budget flash, hashes et manifeste automatises |
| Observabilite `hal.8` | `hal.8-alpha.2`: endurance et calibration Hal/Nabu isolee |
| Fonctions `hal.9` | Planifiees, non implementees |
| Distribution `hal.10` | CI epinglee; canaux et documentation a poursuivre |

L'image principale a partir de `hal.7-alpha.3` n'embarque que le modele Okay
Hal. Okay Nabu sera compile comme variante de calibration afin de ne pas payer
en permanence le cout flash de deux modeles.

## Principes

- `hal.6` reste l'image de secours jusqu'a la validation de sa remplacante.
- L'ESP32 gere le materiel, le wake word, l'audio, les boutons, les LED et la
  recuperation locale.
- Home Assistant gere zones, presences, intentions, permissions et scenarios.
- Le Chuwi execute STT, TTS, LLM, traduction et analyse acoustique.
- Music Assistant gere musique et groupes; Frigate fournit les evenements video.
- Une fonction critique ne depend jamais d'une decision libre du LLM.
- Aucun secret ni firmware de production n'est publie sur GitHub.
- Chaque release conserve une procedure de retour arriere testee.

## Architecture cible

| Couche | Responsabilites |
| --- | --- |
| Muse Luxe | Wake word, micro, lecture, boutons, LED, volume, batterie, jack, watchdog et Safe Mode |
| Home Assistant | Assist, zones, presences, intentions deterministes, annonces, minuteurs et scripts bornes |
| Chuwi | Canary/Whisper, Piper, LFM/Llama, traduction, analyse audio et messages |
| Music Assistant | Bibliotheques, radios, groupes et transfert audio |
| Frigate | Detection camera sans donner au firmware acces aux flux video |
| Infrastructure | Etats OPNsense, Victron et Proxmox en lecture; actions sensibles encapsulees |

## Socle technique

### Phase 0 - Reference `hal.6`

- Archiver binaire, manifeste, sommes de controle et configuration Home
  Assistant.
- Documenter flash USB, OTA privee et restauration de l'API chiffree.
- Conserver les mesures flash, heap, PSRAM, Wi-Fi, latence et erreurs TTS.

Sortie: restauration de `hal.6` possible sans reconstruire le firmware.

### Phase 1 - Architecture et resilience `hal.7`

- Decouper le YAML en `hardware`, `audio`, `voice`, `ui`, `recovery`,
  `diagnostics` et `updates`.
- Remplacer les changements disperses de phase par une machine d'etat unique.
- Gerer deconnexion HA, perte Wi-Fi, erreur STT/TTS, audio bloque et timeout.
- Configurer Safe Mode et un bouton de recuperation desactive par defaut.
- Rendre les transitions micro, DAC et wake word idempotentes.

Sortie: 10 coupures Wi-Fi et 10 redemarrages HA sans intervention, puis retour
a l'attente en moins de 10 secondes apres chaque erreur.

### Phase 2 - Empreinte et reproductibilite `hal.7`

- Produire en CI un rapport par composant et bloquer les regressions de taille.
- Viser moins de 93 % de flash avant les fonctions utilisateur.
- Evaluer `improv_serial`, portail captif, effets et ressources non utilisees.
- Utiliser le composant `es8388` local apres comparaison avec l'amont.
- Epingler ESPHome, ESP-IDF, Docker et les actions GitHub.
- Conserver localement les modeles redistribuables et referencer par commit les
  autres.
- Generer version, taille, MD5/SHA-256 et manifeste depuis le meme build.

Sortie: build sans branche flottante, manifeste coherent et aucun secret dans
l'historique ou les artefacts publics.

### Phase 3 - Observabilite et endurance `hal.8`

- Compter wake words, succes, erreurs, timeouts, reconnexions et recuperations.
- Exposer dernier motif de recuperation et etat de sante synthetique.
- Garder les diagnostics couteux desactives par defaut.
- Automatiser TTS, veille, coupure reseau, OTA, boutons, jack et memoire.
- Executer 100 cycles TTS et 24 heures de veille avant une release stable.

Sortie: aucun crash ou ring-buffer reset, aucune fuite memoire continue et une
trace exploitable pour chaque erreur injectee.

### Phase 4 - Calibration acoustique `hal.8`

- Mesurer gain, suppression de bruit et multiplicateur audio.
- Creer un corpus familial consenti, local et a retention courte.
- Comparer les profils Okay Hal/Nabu et les sensibilites sur les memes sons.
- Tester une variante VAD uniquement si son gain justifie son cout memoire.
- Ne jamais utiliser une empreinte vocale comme authentification.

Sortie: profils jour/nuit mesures, faux reveils quantifies et stabilite egale a
`hal.7`.

## Fonctions utilisateur

### Phase 5 - Fondations familiales `hal.9.0`

#### Annonces intelligentes

- Cibler enceinte, piece, etage, personne ou maison entiere.
- Adapter volume, carillon et priorite aux modes jour/nuit.
- Mettre en file les annonces non urgentes pendant musique ou conversation.

#### Assistant de cuisine et minuteurs

- Plusieurs minuteurs nommes avec pause, reprise et annulation.
- LED representant le temps restant et annonces intermediaires.
- Son local de secours si HA tombe apres la creation du minuteur.

#### Modes physiques et conversation continue

- Appui simple: mute; appui long: confidentialite; double: arret; triple:
  fonction configurable.
- Mode nuit avec volume et LED reduits.
- Un appui ouvre une conversation multi-tour; appui, voix ou timeout la ferme.
- Une LED sans ambiguite indique toute session micro continue.

Sortie: aucune session ouverte apres timeout, annonces prioritaires propres et
minuteurs resilients a une reconnexion.

### Phase 6 - Communication et audio `hal.9.1`

#### Interphone familial

- `Appelle la cuisine` ouvre un canal entre deux satellites.
- Bouton central pour accepter, parler, refuser et raccrocher.
- Commencer en push-to-talk; n'evaluer le duplex qu'apres mesure de l'echo.
- Carillon et LED obligatoires: aucune ecoute silencieuse.

#### Messages differes

- `Dis a Anna que le diner est pret quand elle rentre` stocke un message local.
- Remise sur presence explicite, avec confirmation, report et expiration.
- Conserver la transcription plutot que l'enregistrement brut si possible.

#### Audio qui suit l'utilisateur

- Transferer musique, podcast ou radio vers une piece sur demande ou regle
  explicite.
- Creer des groupes temporaires et conserver position, source et volume relatif.
- Proposer un mode manuel pour eviter les transferts intempestifs.

Sortie: aucun canal fantome, message remis une fois au bon destinataire et
transfert audio sans redemarrer le satellite.

### Phase 7 - Intelligence de la maison `hal.9.2`

#### Narrateur de la maison

- Expliquer acces Internet, cameras hors ligne, Proxmox, batterie et
  consommation inhabituelle.
- Collecter les faits par outils en lecture; le modele ne fait que les resumer.
- Indiquer la fraicheur des donnees importantes.

#### Energie et urgence

- Annoncer coupure, passage sur batterie, autonomie et retour secteur.
- Proposer des delestages via scripts bornes et confirmation explicite.
- Maintenir les alertes essentielles sans Internet.

#### Routines interactives

- Guider depart, coucher, fermeture serveur, panne, alarme ou evacuation.
- Verifier chaque etape avec les capteurs, avec pause, reprise et annulation.
- Permettre de reprendre la routine sur une autre enceinte.

#### Carillon video intelligent

- Frigate annonce personne ou evenement pertinent avec zone.
- Proposer l'envoi d'une image au telephone ou a un ecran autorise.
- Appliquer anti-spam, horaires silencieux et seuil de confiance.
- Pas de reconnaissance faciale annoncee sans consentement familial explicite.

Sortie: reponses fondees sur des entites reelles, aucune action critique
exposee au LLM et alertes Frigate dedupliquees.

### Phase 8 - Fonctions experimentales `hal.9.3`

#### Gardien acoustique

- Detecter sur le Chuwi alarme fumee, bris de verre, pleurs ou aboiements.
- Activation par piece, segments minimaux et retention courte.
- Croiser avec d'autres capteurs avant une action importante.

#### Interprete instantane

- Session bilingue continue avec STT, traduction et TTS locaux.
- Choix des langues par voix ou bouton et LED d'ecoute continue.
- Aucun historique par defaut apres la session.

#### Radio et secours hors ligne

- Lire depuis microSD sons, consignes, routines et medias essentiels sans HA.
- Maintenir des messages minimaux pour panne secteur et evacuation.
- Entree/sortie physique du mode secours et synchronisation depuis le LAN admin.

Sortie: fonctions desactivables independamment, politique audio respectee et
mode secours valide pendant une panne simulee de HA.

## Distribution et maintenance `hal.10`

- Canaux `development`, `beta` et `stable` avec manifestes separes.
- Une enceinte canari avant toute promotion familiale.
- Changelog, inventaire des dependances, taille et compatibilite automatises.
- Guides d'installation, USB, rollback, diagnostic et confidentialite.
- Modeles d'issues pour crash, audio, wake word et materiel.
- Proposer a l'amont les corrections generiques apres validation.

Sortie: une autre personne peut installer, tester, diagnostiquer et restaurer
le firmware avec la seule documentation.

## Garde-fous permanents

- Pas de BLE dans le build audio principal tant que les ressources sont tendues.
- Pas de Secure Boot, eFuse ou verrouillage irreversible pour le moment.
- Pas de desarmement, deverrouillage ou coupure dangereuse par simple voix.
- Les sirenes restent des scripts temporises avec arret garanti.
- Les commandes critiques exigent confirmation, contexte et journalisation.
- Analyse acoustique et reconnaissance de personnes sont locales et opt-in.
- Le mode confidentialite est visible; une coupure electrique materielle du
  micro reste la seule garantie forte.

## Calendrier indicatif

| Periode | Objectif |
| --- | --- |
| Semaines 1-2 | Machine d'etat et resilience `hal.7-alpha` |
| Semaine 3 | Empreinte, dependances et `hal.7` |
| Semaines 4-5 | Observabilite et endurance `hal.8-alpha` |
| Semaine 6 | Calibration et `hal.8` |
| Semaines 7-8 | Annonces, minuteurs et modes `hal.9.0` |
| Semaines 9-10 | Interphone, messages et audio `hal.9.1` |
| Semaines 11-12 | Narrateur, energie, routines et Frigate `hal.9.2` |
| Apres validation | Acoustique, traduction et secours `hal.9.3` |
| Stabilisation | Canaux, documentation et `hal.10` |

Une fonction n'entre dans `stable` qu'apres validation de ses criteres et du
retour vers la version precedente.
