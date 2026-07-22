# Muse credential rotation

The preparation phase is offline: it does not connect to the speaker, compile
firmware or install an OTA. Run it only from the private operator workstation.

## Prepare after endurance review

1. Protect the current ignored file and reserve a new ignored directory:

   ```bash
   chmod 600 secrets.yaml
   python3 scripts/prepare_secret_rotation.py \
     secrets.yaml release/rotation-VERSION
   ```

2. Confirm the directory is `0700` and its three files are `0600`. The new
   `secrets.yaml` preserves unrelated values while replacing the API encryption
   key, OTA password and fallback AP password with independent system-CSPRNG
   values. `transition-ota.yaml` contains only the old OTA password.
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

After successful exact-version and healthy-state verification, unlink the
transition file and retain only the new ignored `secrets.yaml`. Secure erasure
cannot be guaranteed on SSD or copy-on-write storage, so the old OTA credential
must be considered retired and never reused. Keep the rotation directory out
of backups until the transition file has been removed.

## Recovery boundary

Keep the independently verified `hal.6` rollback artifact. A rollback after
rotation must use a deliberately reviewed artifact compatible with the active
credential set; never weaken authentication merely to make an old binary
uploadable.
