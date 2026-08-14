### Added Features

- Include vulnerable ranges in CycloneDX output format [Issue [#3512](https://github.com/anchore/grype/issues/3512)] [PR [#3519](https://github.com/anchore/grype/pull/3519) @somaz94]

### Bug Fixes

- honor match.rust.using-cpes configuration [PR [#3611](https://github.com/anchore/grype/pull/3611) @Dashtid]

### Dependencies

11 dependency changes (11 updated). 2 vulnerabilities remediated.

**🟢 Remediated (2)**

- [GHSA-hc8v-wwc9-vgxm](https://github.com/advisories/GHSA-hc8v-wwc9-vgxm) (High) — github.com/go-git/go-git/v5
- [GHSA-qgq7-7hm3-q39j](https://github.com/advisories/GHSA-qgq7-7hm3-q39j) (Medium) — github.com/go-git/go-git/v5

<details>
<summary>Updated (11 packages)</summary>

- github.com/anchore/syft `v1.50.0` → `v1.51.0`
- github.com/diskfs/go-diskfs `v1.9.3` → `v1.9.4`
- github.com/gabriel-vasile/mimetype `v1.4.13` → `v1.4.15`
- github.com/go-git/go-billy/v5 `v5.9.0` → `v5.9.1`
- github.com/go-git/go-git/v5 `v5.19.1` → `v5.19.2` **(🟢 remediated [GHSA-hc8v-wwc9-vgxm](https://github.com/advisories/GHSA-hc8v-wwc9-vgxm), [GHSA-qgq7-7hm3-q39j](https://github.com/advisories/GHSA-qgq7-7hm3-q39j))**
- github.com/klauspost/compress `v1.19.0` → `v1.19.1`
- github.com/magiconair/properties `v1.8.10` → `v1.18.11`
- github.com/santhosh-tekuri/jsonschema/v6 `v6.0.2` → `v6.0.3`
- github.com/ulikunitz/xz `v0.5.15` → `v0.5.16`
- go.yaml.in/yaml/v3 `v3.0.4` → `v3.0.5`
- modernc.org/sqlite `v1.54.0` → `v1.55.0`
</details>

**[(Full Changelog)](https://github.com/anchore/grype/compare/v0.116.1...v0.117.0)**
