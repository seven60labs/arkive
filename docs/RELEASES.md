# Versioning and releases

ARKive uses semantic versioning in the top-level `VERSION` file (`MAJOR.MINOR.PATCH`, started at 1.0.0).
`install.sh` copies it to `/opt/mini-web/VERSION`; the admin panel shows it (Update tab and page footer).

- PATCH: fixes, content-list tweaks. MINOR: new features (e.g. a new admin tab). MAJOR: changes that need manual steps.

## Cutting a release
1. Bump `VERSION` (e.g. `1.0.0` -> `1.1.0`) and commit: `git commit -am "Release 1.1.0"`.
2. Tag the same commit with a `v` prefix and push both:
   `git tag -a v1.1.0 -m "1.1.0" && git push origin main v1.1.0`
3. Optional but recommended: publish a GitHub Release for the tag (`gh release create v1.1.0 --notes-file CHANGES.txt`).
   Its notes are shown as the changelog in the panel. Drafts and pre-releases are ignored.

The tag and `VERSION` must match: the device refuses a release whose `VERSION` differs from its tag.

## How devices update
Admin panel -> Update -> **Check for updates** runs `sudo mini-update check` (the only commands minitools may run are
`mini-update check|apply|rollback`, see `etc/sudoers.d/023-mini-update`). It reads the newest non-draft release, or the
highest `vX.Y.Z` tag if there are no releases, from the public GitHub API (no credentials).
**Update** (enabled only when a newer version exists) runs in a detached `arkive-update` systemd unit:
download the tag tarball (API, fallback codeload.github.com) -> verify (gzip/tar intact, no absolute/`..` paths,
VERSION == tag, Python and install.sh parse) -> save rollback tarball in `/var/lib/arkive-update/rollback/` (newest 3)
-> run `install.sh` -> wait for the panel to answer. On failure the previous version is restored automatically.
Log: `/var/lib/arkive-update/update.log`. Manual rollback: Update tab -> Roll back, or
`sudo tar xzf /var/lib/arkive-update/rollback/<file>.tgz -C / && sudo systemctl daemon-reload && sudo systemctl restart mini-web mini-videos`.

The repository must be public for this to work. For testing or a private mirror, root may create
`/etc/arkive/update.conf` (root-owned, not group/world-writable) with `REPO=`, `API=`, `CODELOAD=` and
`TOKEN_FILE=` (a root-only 0600 file holding a read-only token; it is sent only to `API`, never shown or logged).
None of this is exposed in the panel.
