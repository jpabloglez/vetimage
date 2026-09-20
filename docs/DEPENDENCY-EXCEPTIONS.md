# Carried dependency advisories

Advisories this project knowingly ships with, why, and what would change that.

CI's **Dependency Audit** job fails the build on `high` and `critical`. Moderate
advisories do not fail it, which is a deliberate choice and also a hazard: left
unwritten, a moderate becomes something everyone has half-noticed and nobody has
decided about. Every advisory at **moderate or above** must therefore appear
here, with the analysis behind the decision — not a severity label and a shrug.

`scripts/check_dependency_exceptions.py` compares this file against a live
`npm audit` and fails CI if the two disagree, so an advisory cannot be added to
the tree, or silently disappear from it, without someone touching this document.

**"Not fixed" is not the same as "not exploitable."** Both entries below are
unreachable in the delivered application, and each says how that was checked and
how to re-check it. If you cannot make that argument for a new advisory, the
answer is to upgrade, not to add a row here.

---

## GHSA-w5hq-g745-h8pq — `uuid` — moderate

**Missing buffer bounds check in v3/v5/v6 when `buf` is provided.**

Path: `cornerstone-wado-image-loader@4.13.2 → uuid@9.0.1`

### Why it is not fixed

`npm audit fix` resolves it only by downgrading `cornerstone-wado-image-loader`
to **4.2.1**, a major-version rollback of the DICOM image loader. That is the
component that decodes every radiograph the platform displays. Trading a working
viewer for an advisory that does not reach the browser is a bad bargain.

### Why it does not reach the browser

The package's `main` is `./dist/cornerstoneWADOImageLoader.bundle.min.js` — a
**pre-bundled** file. It contains no reference to `uuid`, so Vite never pulls
`uuid` into the module graph, and none of its code is emitted into our output.
The `uuid: ^9.0.0` line in the package's `dependencies` is an artifact of how
upstream builds that bundle; `npm audit` walks declared dependencies, not
shipped code.

Verified against a real build (`npm run build`), searching `dist/assets/*.js`
for markers that must be present if `uuid` were bundled:

| marker | meaning | occurrences |
|---|---|---|
| `getRandomValues` | how uuid draws randomness | 0 |
| `unsafeStringify` | uuid's byte→string routine | 0 |
| `89ab` | uuid's variant-nibble table | 0 |

Separately, the advisory only bites when `v3`, `v5` or `v6` is called **with a
`buf` argument**. `v4` — the random variant libraries normally use — is
unaffected.

### To re-check

```bash
docker compose exec frontend-vetimage sh -c \
  'cd /var/www/app/frontend && npm run build && grep -c getRandomValues dist/assets/*.js'
```

Any non-zero count means uuid now ships and this entry no longer holds.

### What would change the decision

- `cornerstone-wado-image-loader` releases a version depending on `uuid ≥ 11.1.0`
  (or drops the dependency), at which point simply upgrade.
- The advisory is re-rated **high** — CI then fails, correctly.
- A build change makes uuid reachable, which the re-check above would catch.

The longer-term fix is the migration to Cornerstone3D, which replaces this
package with `@cornerstonejs/dicom-image-loader` and retires the entry entirely.

---

## GHSA-968p-4wvh-cqc8 — `@babel/runtime` — moderate

**Inefficient RegExp complexity in generated code with `.replace` when
transpiling named capturing groups.**

Path: `cornerstone-tools@6.0.10 → @babel/runtime`

### Why it is not fixed

The only offered resolution downgrades `cornerstone-tools` to **3.0.0** — three
major versions back, on the package that provides the viewer's window/level,
zoom, pan and scroll tools.

### Why it does not reach the browser

The advisory is narrower than "Babel helpers are present". It concerns the
`wrapRegExp` helper, which Babel emits **only** when transpiling a regular
expression that uses named capture groups. Absent that helper, the vulnerable
code does not exist in the output.

| marker | in `cornerstone-tools` shipped entry | in our built bundle |
|---|---|---|
| `wrapRegExp` | 0 | 0 |
| `_wrapRegExp` | — | 0 |
| `BabelRegExp` | 0 | 0 |

Other Babel helpers *do* ship — `regeneratorRuntime` appears 15 times — so this
is not a claim that `@babel/runtime` is absent. It is the narrower and checkable
claim that the helper this advisory is about is absent.

Reaching it would additionally require feeding attacker-controlled input to such
a regex, which is a second condition that does not hold either.

### To re-check

```bash
docker compose exec frontend-vetimage sh -c \
  'cd /var/www/app/frontend && npm run build && grep -c wrapRegExp dist/assets/*.js'
```

### What would change the decision

- `cornerstone-tools` ships a release on a patched `@babel/runtime`.
- Any dependency starts using named capture groups, making `wrapRegExp` appear
  in the bundle — which the re-check above would catch.
- Re-rated high, at which point CI fails and this is no longer a choice.

---

## Adding an entry

Don't, if you can upgrade instead. If you genuinely cannot:

1. State the **path** — which direct dependency pulls it in.
2. State what `npm audit fix` would do, and precisely why that is unacceptable.
   "Breaking change" alone is not a reason; name what breaks.
3. Show the **reachability analysis**, with a command anyone can run to
   reproduce it. An entry without this is an admission, not an exception.
4. State what would change the decision, so the entry can eventually be deleted.
5. Add the advisory id to `ACCEPTED` in
   `scripts/check_dependency_exceptions.py`, or CI will fail.
