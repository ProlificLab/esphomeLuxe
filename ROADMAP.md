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
| Fonctions `hal.9` | `9.0-alpha.5` sous 93%, minuteurs `9.0-ha-alpha.2` et LED `9.0-ha-alpha.3`; audio `9.1-ha-alpha.5`; messages `9.1-ha-alpha.4`; interphone `9.1-ha-alpha.3`; revue vidéo `9.2-ha-alpha.6`; acoustique `9.3-ha-alpha.3` source |
| Distribution `hal.10` | `hal.10-alpha.14`: messages familiaux liés à la file et au candidat exact |

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

Etat source `hal.9.0-ha-alpha.2`: les minuteurs Assist natifs restent portes
par l'ESP32 avec nom, compte, LED et son final local. Un package HA optionnel,
desactive par defaut, annonce les jalons 5 min, 1 min, 30 s et 10 s via la file
normale. Il refuse tout rattrapage apres reconnexion ou saut de duree. Les
annonces non urgentes attendent aussi la fin de la musique et des sessions
vocales; pause, reprise, minuteurs concurrents et reconnexion restent a qualifier
physiquement apres l'endurance.

#### Modes physiques et conversation continue

- Appui simple: mute; appui long: confidentialite; double: arret; triple:
  fonction configurable.
- Mode nuit avec volume et LED reduits.
- Un appui ouvre une conversation multi-tour; appui, voix ou timeout la ferme.
- Une LED sans ambiguite indique toute session micro continue.

Etat source `hal.9.0-ha-alpha.3`: HA applique uniquement une luminosite bornee
jour/nuit a l'entite LED ESPHome existante; couleurs et effets restent possedes
par la machine d'etat locale. Ecoute, confidentialite, erreur et secours gardent
des planchers visibles. Le gradient minuteur `hal.9.0-alpha.5` conserve la
luminosite courante au lieu de la reecrire chaque seconde, pour un OTA toujours
sous 93%. Qualification physique de chaque phase et d'une transition pendant
un minuteur reste requise apres l'endurance.

Etat outil `hal.9.0-qualification.1`: le test API des modes refuse une mauvaise
version, une enceinte occupee ou des minuteurs actifs, exige des compteurs voix
stables et restaure les deux modes dans un bloc final. Sa preuve JSON n'est
publiee atomiquement qu'apres retour verifie a `waiting/healthy`. Boutons, audio
et LED restent volontairement une observation physique separee.

Etat outil `hal.9.0-qualification.4`: le dossier minuteur ferme douze scenarios
physiques et mesure deux noms distincts, les quatre jalons une seule fois en
jour puis en nuit, zero rejeu apres reconnexion et un son final local pendant
la perte HA. Il est lie a la version, a l'OTA et aux deux packages HA exacts.

Sortie: aucune session ouverte apres timeout, annonces prioritaires propres et
minuteurs resilients a une reconnexion.

### Phase 6 - Communication et audio `hal.9.1`

#### Interphone familial

- `Appelle la cuisine` ouvre un canal entre deux satellites.
- Bouton central pour accepter, parler, refuser et raccrocher.
- Commencer en push-to-talk; n'evaluer le duplex qu'apres mesure de l'echo.
- Carillon et LED obligatoires: aucune ecoute silencieuse.

Etat source `hal.9.1-ha-alpha.3`: le coordinateur Home Assistant impose des
pieces mappees, un opt-in, un carillon sur ouverture et relais, 45 secondes de
sonnerie et cinq minutes de session. Le transport est une transcription locale
ephemere rendue par Piper, sans audio brut ni duplex; un redemarrage HA ferme
tout etat actif. La qualification reste ouverte jusqu'au second satellite et a
l'origine de piece materielle fiable.

#### Messages differes

- `Dis a Anna que le diner est pret quand elle rentre` stocke un message local.
- Remise sur presence explicite, avec confirmation, report et expiration.
- Conserver la transcription plutot que l'enregistrement brut si possible.

Etat source `hal.9.1-ha-alpha.4`: trois slots persistants de 240 caracteres
refusent tout ecrasement et sont traites FIFO par identifiant horodate. Une
livraison revendique le slot avant TTS; un redemarrage ou blocage de six minutes
la place en revue sans rejeu automatique. Retry ou discard deviennent alors
explicitement humains. La migration mono-slot conserve un message valide sans
prolonger un message expire. Deploiement et qualification physique attendent la
fin de l'endurance.

Etat outil `hal.9.1-qualification.1`: le dossier messages lie version, OTA,
deux packages et provisionneur. Il ferme seize scenarios, deux destinataires,
FIFO, expiration, quarantaines, retry/discard, carillons, zero doublon
automatique et une file finale vide sans conserver de transcription.

#### Audio qui suit l'utilisateur

- Transferer musique, podcast ou radio vers une piece sur demande ou regle
  explicite.
- Creer des groupes temporaires et conserver position, source et volume relatif.
- Proposer un mode manuel pour eviter les transferts intempestifs.

Etat source `hal.9.1-ha-alpha.5`: le transfert de file reste strictement manuel
et desactive par defaut. Les groupes temporaires acceptent deux a quatre Muse
disponibles pour 5 a 240 minutes, revendiquent leur etat avant `join`, restaurent
les volumes individuels et ferment par le meme chemin sur demande ou expiration.
Une creation/fermeture interrompue, un timer perdu ou un membre indisponible
passe en `review`; seul un nettoyage humain confirme peut envoyer les commandes
de recuperation. Position, volumes et absence de groupe fantome restent a
qualifier avec un second satellite.

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

Etat source `hal.9.2-ha-alpha.6`: l'integration Frigate officielle est epinglee et
utilise un compte `viewer` sur le port authentifie. Onze cameras alimentent un
etat normalise; les 449 entites brutes sont masquees a Assist et les 121
commandes generees sont desactivees. Une revue locale optionnelle expose pendant
cinq minutes les deux entites image d'entree explicitement mappees dans un
dashboard HA authentifie, sans URL publique, copie, jeton ou envoi externe.
La livraison telephone reste bloquee car aucun Companion n'est inscrit.

Etat outil `hal.9.2-qualification.1`: le dossier de revue lie version, OTA,
package, dashboard et provisionneur. Il ferme les deux cameras, les rejets de
seuil, type, carte et fraicheur, deux expirations a cinq minutes, un redemarrage
HA, l'authentification et zero URL, jeton ou livraison externe.

Sortie: reponses fondees sur des entites reelles, aucune action critique
exposee au LLM et alertes Frigate dedupliquees.

### Phase 8 - Fonctions experimentales `hal.9.3`

#### Gardien acoustique

- Detecter sur le Chuwi alarme fumee, bris de verre, pleurs ou aboiements.
- Activation par piece, segments minimaux et retention courte.
- Croiser avec d'autres capteurs avant une action importante.

Etat source `hal.9.3-ha-alpha.3`: le classifieur CPU natif de Frigate est
prepare par camera via un manifeste de consentement, un flux go2rtc explicite,
quatre classes fermees et une retention maximale d'un jour. La transcription
est interdite, HA revient a `off` apres redemarrage et ne peut produire qu'une
annonce de verification, eventuellement corroboree par un capteur dedie. Aucun
microphone camera n'est active; consentement, test du codec, charge CPU, faux
positifs et suppression physique a un jour restent ouverts.

Etat outil `hal.9.3-qualification.2`: le dossier acoustique lie version, OTA,
package HA, preparateur, politique et hash de configuration privee. Il ferme
consentement, quatre classes sur deux heures chacune, faux positifs, RMS, CPU,
retention, non-transcription, absence d'action et rollback audio desactive.

#### Interprete instantane

- Session bilingue continue avec STT, traduction et TTS locaux.
- Choix des langues par voix ou bouton et LED d'ecoute continue.
- Aucun historique par defaut apres la session.

Etat `hal.9.3-ha-alpha.2`: deux pipelines locaux francais-anglais utilisent
Canary/Whisper, Granite et Piper sans outil domotique. La session est bornee a
dix minutes, restaure le pipeline precedent et efface explicitement le contexte
ESPHome a la sortie. La qualification acoustique bilingue physique reste ouverte.

Etat outil `hal.9.3-qualification.1`: le dossier bilingue lie version, OTA,
package, configurateur et phrases locales. Il ferme quinze scenarios, cinq
phrases par direction sous quinze secondes, cinq resets de contexte et zero
action domotique, avec Granite et les deux pipelines exacts.

#### Radio et secours hors ligne

- Lire depuis microSD sons, consignes, routines et medias essentiels sans HA.
- Maintenir des messages minimaux pour panne secteur et evacuation.
- Entree/sortie physique du mode secours et synchronisation depuis le LAN admin.

Etat source `hal.9.0-alpha.5`: le bus SPI officiel de la Luxe alimente un
lecteur FAT16/32 minimal, strictement sans ecriture, limite a six WAV 8.3 de
trois minutes. Le quadruple-clic active ou quitte le mode persistant; les autres
gestes parcourent, arretent ou ouvrent directement la consigne d'evacuation.
Le preparateur admin valide format et SHA-256. Des diagnostics ESP32 minimaux
et des logs de production limites aux erreurs ramènent l'OTA a 92,9%; une image
USB WARN sans auto-update garde le diagnostic verbeux. L'OTA attend la fin de
l'endurance alpha 2 et une carte physique revue.

Etat outil `hal.9.0-qualification.5`: les deux portes secours partagent
obligatoirement le meme dossier hashé. Celui-ci lie version, OTA, package,
composant FAT et manifeste de carte inchange, puis ferme quinze scenarios,
les six lectures et les cycles de reboot et deconnexion/reconnexion HA.

Sortie: fonctions desactivables independamment, politique audio respectee et
mode secours valide pendant une panne simulee de HA.

## Distribution et maintenance `hal.10`

- Canaux `development`, `beta` et `stable` avec manifestes separes.
- Une enceinte canari avant toute promotion familiale.
- Changelog, inventaire des dependances, taille et compatibilite automatises.
- Guides d'installation, USB, rollback, diagnostic et confidentialite.
- Modeles d'issues pour crash, audio, wake word et materiel.
- Proposer a l'amont les corrections generiques apres validation.

Etat source `hal.10-alpha.14`: toute promotion reconstruit proprement le
firmware epingle, exige un dossier JSON recent avec preuves pour 13 portes beta
ou 33 portes stable, verifie commit/version/SHA-256, publie un binaire versionne
et n'active le canal qu'en publiant son manifeste en dernier. Un worktree sale,
une prerelease stable ou une porte ouverte stable sont refuses. La preuve
d'endurance detecte aussi les telemetries figees et les redemarrages, refuse par
defaut d'ecraser un journal et produit un resume JSON atomique.
La porte modes charge aussi une preuve liee par hash, controle sa version, ses
quatre transitions, ses compteurs et son nettoyage; elle ne remplace jamais
l'observation physique des boutons et LED.
Les huit fonctions auparavant implicites ont maintenant leur propre porte
stable: annonces routees, minuteurs, LED nuit, messages differes, fraicheur des
faits maison, transfert de routine, revue video et gardien acoustique.
La porte controles physiques exige desormais un dossier recent lie par hash a
la version et au binaire OTA, avec dix observations humaines fermees; une simple
phrase dans le dossier de promotion n'est plus acceptee.
La porte LED nuit charge egalement un dossier hashé avec les neuf profils et six
scenarios, lie au binaire OTA et au hash du package HA recalcule depuis la source.
La porte minuteurs charge un dossier hashé de douze scenarios avec des mesures
fermees, lie au binaire OTA et aux hashes des packages de base et timer coach.
Les deux portes secours doivent partager un dossier hashé unique, lie au
binaire OTA, au package ESPHome, au composant FAT et au manifeste microSD.
La porte interprète charge un dossier hashé lie au binaire OTA, aux trois
sources HA, au digest Granite, aux deux pipelines et aux mesures bilingues.
La porte acoustique charge un dossier hashé lie au binaire OTA, aux sources
Frigate/HA, au consentement, aux mesures de qualite et au rollback prive.
La porte revue vidéo charge un dossier hashé lie au binaire OTA, au package,
au dashboard, au provisionneur et aux observations authentifiees fermees.
La porte messages charge un dossier hashé lie au binaire OTA, aux packages,
au provisionneur, aux compteurs de remise et a l'etat final vide.

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
