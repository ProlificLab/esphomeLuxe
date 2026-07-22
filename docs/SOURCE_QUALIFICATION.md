# Source qualification

This record binds the source-only beta and stable gates to one candidate. Keep
all files in an ignored private `release/source-VERSION/` directory. It does not
replace physical canary evidence.

## Required logs

1. Run the tracked-secret audit against the actual private `secrets.yaml`:

   ```bash
   python3 scripts/audit_tracked_secrets.py \
     --private-secrets secrets.yaml --require-private-keys 3 \
     --output release/source-VERSION/secrets-audit.log
   ```

   The report never contains secret values. It must compare at least the API
   encryption key, OTA password and fallback AP password, with zero exact,
   suspicious or prohibited-file findings. Placeholder values cannot pass.
2. From one clean commit, run two independent pinned clean builds. Save complete
   output as `build-first.log` and `build-second.log`, then require both OTA
   SHA-256 values to equal the reviewed candidate SHA-256.
3. Run `scripts/check_firmware_size.sh` on the reviewed OTA and retain
   `firmware-size.log`. Record exact bytes and the one-decimal usage generated
   by the checker; both 93% target and 97% hard limit must pass.
4. Save exact-commit workflow metadata as `ci.log` using:

   ```bash
   gh run view RUN_ID -R ProlificLab/esphomeLuxe \
     --json conclusion,databaseId,event,headSha,jobs,name,status,url \
     > release/source-VERSION/ci.log
   ```

   Record its repository, workflow, run/job IDs, head SHA, event, conclusion and
   canonical GitHub Actions URL. The checker parses this JSON, requires the
   successful `compile` job and rejects a run for another commit.
5. Hash all five distinct non-empty logs and fill
   `docs/source-qualification-record.example.json`. Validate it with:

   ```bash
   python3 scripts/check_source_qualification_evidence.py \
     release/source-VERSION/source-VERSION.json \
     --expected-version VERSION \
     --expected-firmware-sha256 OTA_SHA256 \
     --expected-source-commit FULL_COMMIT \
     --expected-size-bytes OTA_SIZE
   ```

`build_reproducible`, `ci_passed`, `firmware_size_hard_limit` and
`secrets_audit` must reference this same hash-bound record for beta. Stable also
uses it for `firmware_size_target`. The qualification checker rejects prose,
split records, modified logs, unsafe paths, non-reproducible hashes, stale CI,
size drift and an audit that did not compare three real private values.

## Current rotation gate

The present canary was provisioned with recognizable example credentials. Do
not rotate them during the active endurance because that would change and
restart the candidate under test. After endurance review and before beta:

1. generate new independent API, OTA and fallback AP secrets;
2. retain the old OTA password only for the one authenticated transition;
3. build the exact candidate with the new secrets in an isolated directory;
4. upload using the old OTA credential, then verify using the new encrypted API;
5. retain the new local `secrets.yaml` at mode `0600` and securely delete the
   transition copy;
6. rerun this audit with `--require-private-keys 3`.

Never commit either old or new values, print them in logs, or weaken API/OTA
authentication to make the rotation easier.
