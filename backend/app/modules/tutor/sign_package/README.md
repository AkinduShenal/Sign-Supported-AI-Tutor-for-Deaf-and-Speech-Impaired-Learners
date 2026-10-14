# Generated sign-manifest snapshot

These JSON files are exact deployment snapshots of:

- `avatar-sign-package/manifest/signs.json`
- `avatar-sign-package/manifest/phrase_map.json`

`avatar-sign-package/` remains the canonical source. The backend uses that
source in a full repository checkout and falls back to this snapshot when
Railway deploys only the configured `/backend` root directory.

After editing either canonical manifest, copy both files here and run the
backend tests. The manifest-sync test will fail if the snapshot is stale.
