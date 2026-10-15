# syntax=docker/dockerfile:1
ARG CI_BASE_IMAGE=ci-base:node24-trixie
FROM ${CI_BASE_IMAGE}

# Empty selects the current stable .NET 10 SDK from Microsoft's Debian feed.
# Set to the exact APT package version when reproducible SDK pinning is needed.
ARG DOTNET_SDK_PACKAGE_VERSION=""
ENV DOTNET_CLI_TELEMETRY_OPTOUT=1 \
    DOTNET_NOLOGO=1 \
    DOTNET_GENERATE_ASPNET_CERTIFICATE=false \
    DOTNET_CLI_WORKLOAD_UPDATE_NOTIFY_DISABLE=true

# The Debian 13 feed provides .NET 10 for both amd64 and arm64. APT installs
# native runtime dependencies along with the SDK, runtime and ASP.NET runtime.
RUN curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 \
       https://packages.microsoft.com/config/debian/13/packages-microsoft-prod.deb \
       -o /tmp/packages-microsoft-prod.deb \
    && dpkg -i /tmp/packages-microsoft-prod.deb \
    && rm /tmp/packages-microsoft-prod.deb \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
       "dotnet-sdk-10.0${DOTNET_SDK_PACKAGE_VERSION:+=$DOTNET_SDK_PACKAGE_VERSION}" \
    && rm -rf /var/lib/apt/lists/* \
    && dotnet --info \
    && dotnet --list-sdks | grep -E '^10\.'
