# Qualification des alertes video Frigate

Le package annonce uniquement un evenement `person` recent de `sonnette` ou
`avant_jardin`. Il est desactive par defaut, silencieux en mode nuit, limite a
une confiance de `0.75`, un cooldown global de 60 secondes et une cible Muse
fermee. Il n'identifie jamais une personne, ne copie aucune image et n'appelle
aucun controle camera ou alarme.

## Anti-doublon

Les sept derniers identifiants acceptes sont conserves dans une FIFO persistante
de 255 caracteres. Un meme evenement ne peut donc pas etre reparle simplement
parce qu'un autre evenement a remplace le dernier ID. Les identifiants sont
bornes a 32 caracteres et ne peuvent contenir le separateur `|`. Les evenements
de plus de 30 secondes et ceux dates de plus de cinq secondes dans le futur sont
refuses. Seuls trois noms de zone sont lus, dans une chaine bornee a 96
caracteres.

## Protocole physique

Attendre la fin de l'endurance, puis copier
`docs/video-alert-record.example.json` dans `release/`. Publier sur
`frigate/events` des charges synthetiques sans image, `sub_label`, identite ou
URL. Utiliser des ID uniques reserves au test et remettre chaque horodatage a
partir de l'heure UTC courante.

Tester les deux cameras, les bords de confiance et d'age, le cooldown entre
cameras, les types/labels/false-positive invalides, le mode nuit et les ID
invalides. Remplir la FIFO a sept, inserer un autre evenement entre un `new` et
un `update` du premier, puis verifier que le premier reste silencieux. Redemarrer
HA et republier un ID encore dans la FIFO: il doit rester silencieux.

Compter une annonce uniquement si le carillon et la phrase sont entendus, puis
si le lecteur revient a `idle`. Les annonces acceptees et audibles doivent etre
identiques, sans erreur. Terminer avec alertes `off`, nuit `off`, MQTT `on`, voix
`waiting/healthy`, lecteur `idle` et une FIFO valide de sept IDs. Ne conserver
aucun payload brut dans la preuve.

```sh
version="REPLACE_WITH_VERSION"
python3 scripts/check_video_alert_evidence.py \
  "release/video-alert-$version.json" \
  --expected-version "$version" \
  --expected-firmware-sha256 "$(sha256sum "release/muse-luxe-$version.ota.bin" | cut -d' ' -f1)" \
  --expected-package-sha256 "$(sha256sum home-assistant/packages/muse_video_alerts.yaml | cut -d' ' -f1)" \
  --expected-base-package-sha256 "$(sha256sum home-assistant/packages/muse_luxe.yaml | cut -d' ' -f1)" \
  --expected-safety-checker-sha256 "$(sha256sum scripts/check_video_alert_safety.py | cut -d' ' -f1)" \
  --expected-model-test-sha256 "$(sha256sum scripts/test_video_alert_model.py | cut -d' ' -f1)" \
  --expected-mqtt-provision-sha256 "$(sha256sum scripts/configure_frigate_mqtt.sh | cut -d' ' -f1)" \
  --expected-frigate-policy-sha256 "$(sha256sum scripts/check_frigate_readonly.py | cut -d' ' -f1)"
```

Lier ensuite le dossier avec
`camera_alerts_deduplicated.evidence = sha256:DIGEST video-alert-VERSION.json`.
Cette documentation et son exemple echoue ne constituent pas une preuve
physique.
