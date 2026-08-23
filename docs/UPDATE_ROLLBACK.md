# AetherMind Pro Update and Rollback

Private in-house beta may use manual archive replacement. Anything shared or external requires CI distribution proof and update-server distribution proof, with a real update/rollback channel.

- Update: verify checksum for the new archive, extract, run `status`, then run `map` and `coordinate`.
- Rollback: restore the prior verified archive and rerun `status`.
- State remains in the customer-selected state directory and can be exported with `aethermind-pro export`.
- Distribution: shared artifacts must prove the CI-published artifact can be delivered through the update server and rolled back without founder-local paths or shell knowledge.

Public self-serve release is blocked until a public-grade update/rollback channel and signing/notarization evidence exist for each declared platform.

## AEM compatibility update

Before updating a checkout that has existing project continuity, preserve each
store:

```bash
cp -R .aethermind .aethermind.pre-aem-v0.2
```

After updating, `status` and `layers inspect` read the preserved
`layers.jsonl` records and any canonical `layers.aem` records. New writes go
only to `layers.aem`; `layers.jsonl` and `manifest.json` remain unchanged.

To roll back the application and the store view, retain the post-update store
and restore the preserved copy:

```bash
mv .aethermind .aethermind.from-aem-v0.2
mv .aethermind.pre-aem-v0.2 .aethermind
```

Keep `.aethermind.from-aem-v0.2` until its newer AEM records have been reviewed
and carried forward. The update performs no automatic destructive migration.
