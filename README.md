# CI images prototype

A common Debian 13 / Node.js 24 job environment with separate Rust and .NET 10
images. These are Forgejo **job images**. The runner supplies the CI Docker
engine through `DOCKER_HOST`, container networking, and init; these images contain
client tools and no daemon, host socket, credentials, or infrastructure settings.

| Target | Default local tag | Adds |
| --- | --- | --- |
| `base` | `ci-base:node24-trixie` | Node/npm, Bash, Git, curl, CA certificates, jq, tar/gzip/xz/zstd, zip/unzip, Docker CLI and Buildx/Compose plugins |
| `rust` | `ci-rust:1.99.0-trixie` | Rust 1.99.0, rustfmt, Clippy, C/C++ build tools, CMake, pkg-config |
| `dotnet` | `ci-dotnet:10.0-trixie` | Stable .NET 10 SDK and native dependencies from Microsoft's Debian 13 APT feed |

The shared foundation is the official `node:24-trixie` image, which already
contains buildpack-deps. Docker client tools come from the official Docker CLI
image. Rust is installed with the official rustup installer. APT installs .NET's
SDK, runtimes and native dependencies together. The default command is Bash.

## Build and check

Requires Docker with a current Buildx/Bake plugin and Python 3 for the check
script. From this directory:

```sh
# ARM64 by default. Build all three, load into Docker, and run their smoke tests.
bash scripts/check.sh

# A single language target also builds its shared base through Bake.
bash scripts/check.sh rust

# For native checks on an x86-64 machine:
PLATFORMS=linux/amd64 bash scripts/check.sh
```

Smoke tests verify Node 24, the CI tools, GNU tar/zstd round trips, an offline Rust
build/Clippy run, and an offline .NET 10 console build/run. No Docker daemon is
needed inside the smoke-test containers. Workspaces and test files are temporary.

Validated locally on Linux ARM64 on 2026-10-15: all three images built and passed
these smoke tests (Rust 1.99.0 and .NET SDK 10.0.402). The amd64/multi-architecture
Bake plan was checked, but amd64 builds and registry publication have not run.

Bake connects language targets directly to the base build. It does not need an
already-published base image, and builds the shared layers once. For standalone
Docker builds instead:

```sh
docker build -f base/Dockerfile -t ci-base:node24-trixie .
docker build -f rust/Dockerfile -t ci-rust:1.99.0-trixie .
docker build -f dotnet/Dockerfile -t ci-dotnet:10.0-trixie .
```

## Versions and updates

The defaults live in `docker-bake.hcl`. Environment variables override them:
`NODE_IMAGE`, `DOCKER_IMAGE`, `RUST_VERSION`, `DOTNET_SDK_PACKAGE_VERSION`,
`IMAGE_PREFIX`, and `PLATFORMS`. The Dockerfile defaults also support standalone
builds; keep them aligned if editing the prototype's defaults.

.NET follows stable 10.0 SDK packages by default. For an exact SDK build, set
`DOTNET_SDK_PACKAGE_VERSION` to the complete version reported by
`apt-get update && apt-cache madison dotnet-sdk-10.0` in a disposable .NET
container. Node/Docker base refs
can include digests. Rust's toolchain version is explicit; the rustup bootstrap
installer currently follows upstream. This prototype is not a fully locked build.

Rebuild with `--pull` for upstream OS/security updates, and rebuild language
images whenever the shared base changes. Example:

```sh
RUST_VERSION=1.99.0 bash scripts/check.sh --pull
```

Rust puts tools under `/usr/local/cargo` and `/usr/local/rustup`, adds Cargo's
binaries to `PATH`, and disables incremental compilation to reduce CI cache size.
.NET disables CLI telemetry, first-run ASP.NET certificate generation and workload
update notifications. SDK versions remain visible through `rustc --version` and
`dotnet --info`; select a compatible image for each project's toolchain/global.json.

## GitHub Actions and GHCR publication

`.github/workflows/images.yml` runs automatically after these files are added to
GitHub. It needs no personal access token or registry secret: login uses the
repository's `GITHUB_TOKEN` with `packages: write` permission.

- Pull requests build and smoke-test all three images without logging in or pushing.
- Pushes to `main` build, test, and publish. Manual dispatch from `main` also publishes;
  dispatching another branch only builds/tests.
- Every Tuesday at 05:17 UTC, a scheduled build refreshes all layers to pick up OS,
  upstream image and stable .NET 10 SDK updates. Manual **refresh** does the same.
- AMD64 uses `ubuntu-24.04`; ARM64 uses `ubuntu-24.04-arm`. Both build and execute
  their smoke tests natively. No QEMU is required.
- BuildKit caches are separate for each target and architecture, using GitHub's
  Actions cache service and its normal eviction policy. Build records last seven
  days; small digest-transfer artifacts last one day.

The registry prefix is derived automatically from the lowercase GitHub repository
name. For an `example/images` repository, the published version tags are:

```text
ghcr.io/example/images/ci-base:node24-trixie
ghcr.io/example/images/ci-rust:1.99.0-trixie
ghcr.io/example/images/ci-dotnet:10.0-trixie
```

Each native build pushes its already-tested image with an `-amd64` or `-arm64`
suffix. After **both** builds pass, the publication job combines their recorded
content digests into the version tags above. It does not rebuild the images.
Main publications are serialized to keep the architecture staging tags consistent.
Each image also gets a unique `build-<run id>-<attempt>` tag. The publication job
summary lists all version/build tags and digest references suitable for consumers.
A failed architecture can leave a staging tag updated, but does not advance the
combined version tags. Old build tags/package versions remain in GHCR; choose a
registry retention policy as the public project grows.

GitHub initially creates GHCR packages as private. After the first publication,
make the three packages public in their package settings. The OCI source label
links them to the GitHub repository. Set Forgejo's `CI_RUST_IMAGE` Actions variable
to the Rust image reference from the job summary, preferably with `@sha256:<digest>`.

For manual local publication, the same Bake file still works:

```sh
# Replace <owner>/<repo> and authenticate to GHCR first.
IMAGE_PREFIX='ghcr.io/<owner>/<repo>/ci' PLATFORMS=linux/amd64,linux/arm64 \
  docker buildx bake --pull --push
```

The workflow has been statically checked and its helper logic is tested locally.
An end-to-end GitHub/GHCR run requires creating the public repository and pushing
these files; no registry publication has been performed from this workspace.
