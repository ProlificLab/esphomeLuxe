# Muse credential rotation

The preparation phase is offline: it does not connect to the speaker, compile
firmware or install an OTA. Run it only from the private operator workstation.

## Prepare after endurance review

1. Protect the current ignored file and reserve a new ignored directory:

   ```bash
   chmod 600 secrets.yaml
   python3 scripts/prepare_secret_rotation.py \
     secrets.yaml release/rotation-VERSION \
     release/hal9-endurance-24h-final.jsonl.summary.json \
     --expected-version VERSION
   ```

2. Confirm the directory is `0700` and its three files are `0600`. The new
   `secrets.yaml` preserves unrelated values while replacing the API encryption
   key, OTA password and fallback AP password with independent system-CSPRNG
   values. `transition-ota.yaml` contains only the old OTA password.
   Validate the closed bundle without displaying its values:

   ```bash
   python3 scripts/check_secret_rotation_bundle.py release/rotation-VERSION \
     --endurance-summary release/hal9-endurance-24h-final.jsonl.summary.json \
     --expected-version VERSION
   ```
   The schema-v2 manifest binds the exact successful 24-hour summary SHA-256,
   candidate version and finish time. Future, expired, incomplete, modified or
   different-version endurance evidence is rejected before secrets are created.
3. Build the exact candidate in an isolated clean worktree with the new
   `secrets.yaml`. Run the tracked-secret audit with `--require-private-keys 3`,
   two clean builds and the complete source qualification procedure.
4. Do not use the transition credential until the reviewed 24-hour endurance
   summary passes and the exact candidate artifact is ready.

## Future authenticated transition

The installation phase will authenticate the one OTA upload with
`transition-ota.yaml`, then authenticate post-boot verification with the new
API encryption key in `secrets.yaml`. It must never disable encryption, expose
an unauthenticated fallback or silently retry with example credentials.

After the endurance summary and exact candidate are reviewed, the closed
operator command is:

```bash
scripts/install_rotated_canary_ota.sh \
  ARTIFACT MANIFEST ENDURANCE_SUMMARY OTA_SHA256 HOST \
  release/rotation-VERSION release/source-VERSION/source-VERSION.json
```

It repeats bundle, tracked-secret and candidate preflights, validates source
evidence schema v2 and proves that both clean builds mounted the bundle's exact
new secrets. A different artifact, bundle, fingerprint or modified build log is
rejected before confirmation. It then requires the literal
`ROTATE CANARY VERSION SHA256` confirmation and repeats the complete binding
check immediately afterward, including the same endurance-summary digest. The
old OTA value is
mounted read-only only for upload. The new API key must then prove the exact
version, `waiting`, `healthy` and empty error state before local activation.
Never set its confirmation variable in shell history or automation.

After successful exact-version and healthy-state verification, unlink the
transition file and retain only the new ignored `secrets.yaml`. Secure erasure
cannot be guaranteed on SSD or copy-on-write storage, so the old OTA credential
must be considered retired and never reused. Keep the rotation directory out
of backups until the transition file has been removed.

## Recovery boundary

Keep the independently verified `hal.6` rollback artifact. A rollback after
rotation cannot safely use authenticated OTA because immutable `hal.6` boots
its retired credential domain. `rollback_hal6_ota.sh` detects this mismatch and
fails before upload. Use the archived USB image and physical recovery procedure;
never preserve or reuse retired values merely to make the old binary uploadable.
The USB image must first pass `scripts/check_hal6_usb_recovery.py`; an upstream
factory image or a rebuild containing example credentials is not proof of the
immutable image. The optional pre-rotation OTA path likewise requires an
explicit private `HAL6_REFERENCE_SECRETS` file and never trusts
`secrets.example.yaml`.
