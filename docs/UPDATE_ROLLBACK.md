# AetherMind Pro Update and Rollback

Private in-house beta may use manual archive replacement. Anything shared or external requires CI distribution proof and update-server distribution proof, with a real update/rollback channel.

- Update: verify checksum for the new archive, extract, run `status`, then run `map` and `coordinate`.
- Rollback: restore the prior verified archive and rerun `status`.
- State remains in the customer-selected state directory and can be exported with `aethermind-pro export`.
- Distribution: shared artifacts must prove the CI-published artifact can be delivered through the update server and rolled back without founder-local paths or shell knowledge.

Public self-serve release is blocked until a public-grade update/rollback channel and signing/notarization evidence exist for each declared platform.
