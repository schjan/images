# CI images

Shared Debian 13 / Node.js job images with separate Rust and .NET toolchains.
The runner supplies the Docker engine through `DOCKER_HOST`, networking, and
init. These images contain client tools, not a daemon, host socket, credentials,
or infrastructure settings.

## Published images

All images support native `linux/amd64` and `linux/arm64` builds.

| Image | Versioned tag | Moving tags | Adds |
| --- | --- | --- | --- |
| `ghcr.io/schjan/images/ci-base` | `node26-trixie` | `node-trixie` | Node/npm, Bash, Git, curl, CA certificates, jq, tar/gzip/xz/zstd, zip/unzip, Docker CLI and Buildx/Compose |
| `ghcr.io/schjan/images/ci-rust` | `1.99.1-trixie` | `1-trixie` | Rust, rustfmt, Clippy, C/C++ build tools, CMake, pkg-config |
| `ghcr.io/schjan/images/ci-dotnet` | `10.0.403-trixie` | `10-trixie`, `10.0-trixie` | .NET 10 SDK, runtimes, and native dependencies from Microsoft's Debian 13 feed |

The registry prefix follows the lowercase GitHub repository name. Versioned
image tags can be rebuilt for OS/security updates; they are not immutable.
Every publication also gets a `build-<run id>-<attempt>` tag and a digest
reference for reproducibility and rollback. Configure registry retention to
preserve the builds you need.

Consumers that want automatic toolchain updates can use `ci-rust:1-trixie` or
`ci-dotnet:10-trixie`. Moving tags only advance after both architectures pass
and the combined build manifest is verified. They still trade reproducibility
for convenience: a new compiler, Clippy release, or SDK can expose CI failures
without a consumer dependency PR. Pin a digest when that tradeoff is unsuitable.

`ci-base:node-trixie` is also the standalone language Dockerfiles' default base.
Bake connects language targets directly to its base build, so it needs no
previously published base image.

## Versions and Renovate

Defaults live in `docker-bake.hcl` and the standalone Dockerfiles. Renovate
updates both copies together:

- **Rust:** the `rust-version` datasource reads official Rust distribution
  manifests. A custom manager tracks both `RUST_VERSION` pins in one Rust
  toolchain PR.
- **.NET:** the `deb` datasource reads Microsoft's Debian 13 feed. Both
  `DOTNET_SDK_PACKAGE_VERSION` pins use the exact APT package version
  (`10.0.403-1`), grouped into one .NET 10 SDK PR. Tracking the
  `dotnet-sdk-10.0` package keeps updates within .NET 10 rather than moving to 11.
- **Node/Docker:** Renovate's Dockerfile manager tracks `base/Dockerfile`, and
  a custom manager tracks the corresponding Bake overrides. Without the latter,
  Bake would silently keep installing the old versions after a Dockerfile PR.

Native smoke tests check the installed Node major, Docker CLI, Rust version,
and .NET SDK version against the resolved Bake plan. Regression tests check update extraction,
pin alignment, and safe publication of all aliases. Renovate does not automerge
these updates.

Environment variables override the Bake defaults: `NODE_IMAGE`, `DOCKER_IMAGE`,
`RUST_VERSION`, `DOTNET_SDK_PACKAGE_VERSION`, `IMAGE_PREFIX`, and `PLATFORMS`.
Node/Docker references can include digests. Rust uses an explicit toolchain;
the rustup bootstrap installer follows upstream. The SDK package is pinned, but
APT still resolves its runtime/native dependencies. This is not a fully locked
build.

## Build and check

Requires Docker with Buildx/Bake and Python 3. ARM64 is the local default:

```sh
# Build/load all three images and run their smoke tests.
bash scripts/check.sh

# Build one language image and its shared base.
bash scripts/check.sh rust
bash scripts/check.sh dotnet

# Native AMD64 build.
PLATFORMS=linux/amd64 bash scripts/check.sh

# Refresh upstream OS/image layers.
bash scripts/check.sh --pull

# Publication and Renovate regression tests; no registry access.
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

Smoke tests exercise the CI tools, GNU tar/zstd round trips, an offline Rust
build/Clippy/run, and an offline .NET 10 console build/run. No Docker daemon is
needed inside the smoke-test containers; test files stay under `/tmp`.

For standalone builds, build the common base first:

```sh
docker build -f base/Dockerfile -t ci-base:node-trixie .
docker build -f rust/Dockerfile -t ci-rust:1.99.1-trixie .
docker build -f dotnet/Dockerfile -t ci-dotnet:10.0.403-trixie .
```

Rust uses `/usr/local/cargo` and `/usr/local/rustup`, adds Cargo to `PATH`, and
disables incremental compilation for smaller caches. .NET disables telemetry,
first-run certificate generation, and workload-update notifications.

## GitHub Actions and publication

`.github/workflows/images.yml` uses native AMD64/ARM64 runners. It builds and
smoke-tests all targets and runs the regression tests on pull requests, without
publishing. Pushes to `main` publish only after both architectures pass. Manual
dispatch publishes only from `main`; other branches only build/test.

Every Tuesday at 05:17 UTC, a scheduled refresh rebuilds all layers for OS,
upstream image, and package updates. Manual **refresh** does the same. With the
SDK now pinned, newer .NET SDK versions arrive through Renovate PRs rather than
silently changing during a refresh.

Each native build pushes only its tested primary image with an architecture
suffix. The publication job validates both digest records and their source
revision, assembles an immutable build manifest from those digests, verifies its
platforms, then assigns all versioned and moving tags to that same digest. It
does not rebuild images. Main publications are serialized; failed architectures
never advance combined moving tags. Failed staging tags are not consumer tags.

The job summary lists every tag and digest. Build caches are separate by target
and architecture. Build records last seven days; digest-transfer artifacts last
one day. GHCR login uses `GITHUB_TOKEN` with `packages: write`, not a personal
access token. Packages must be public for anonymous consumers.

## Consumer caches

A moving image tag is not a compiler identity. Rust consumers should include
`rustc -Vv` in their build-cache key, together with OS/architecture, lockfile,
and the relevant source revision. Werker already hashes the image reference
and full compiler identity, so a compiler update behind `1-trixie` cannot
restore another compiler's build cache. If the image only refreshes OS packages,
the compiler key stays the same; include a resolved image digest too when native
build dependencies require stricter isolation.

A future .NET consumer should similarly include the selected SDK from
`dotnet --version` (plus OS/architecture and dependency inputs), not just the
moving `10-trixie` tag. There is no .NET consumer pipeline here yet.
