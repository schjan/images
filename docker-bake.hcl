variable "IMAGE_PREFIX" {
  default = "ci"
}

variable "NODE_IMAGE" {
  default = "docker.io/library/node:24-trixie"
}

variable "DOCKER_IMAGE" {
  default = "docker.io/library/docker:29.9.0-cli"
}

variable "RUST_VERSION" {
  default = "1.99.0"
}

variable "DOTNET_SDK_PACKAGE_VERSION" {
  default = ""
}

# One architecture at a time for local --load; override when publishing.
variable "PLATFORMS" {
  type    = list(string)
  default = ["linux/arm64"]
}

group "default" {
  targets = ["base", "rust", "dotnet"]
}

target "_common" {
  context   = "."
  platforms = PLATFORMS
}

target "base" {
  inherits  = ["_common"]
  dockerfile = "base/Dockerfile"
  tags       = ["${IMAGE_PREFIX}-base:node24-trixie"]
  args = {
    NODE_IMAGE   = NODE_IMAGE
    DOCKER_IMAGE = DOCKER_IMAGE
  }
}

target "rust" {
  inherits   = ["_common"]
  dockerfile = "rust/Dockerfile"
  tags       = ["${IMAGE_PREFIX}-rust:${RUST_VERSION}-trixie"]
  contexts = {
    ci-base = "target:base"
  }
  args = {
    CI_BASE_IMAGE = "ci-base"
    RUST_VERSION  = RUST_VERSION
  }
}

target "dotnet" {
  inherits   = ["_common"]
  dockerfile = "dotnet/Dockerfile"
  tags       = ["${IMAGE_PREFIX}-dotnet:10.0-trixie"]
  contexts = {
    ci-base = "target:base"
  }
  args = {
    CI_BASE_IMAGE               = "ci-base"
    DOTNET_SDK_PACKAGE_VERSION = DOTNET_SDK_PACKAGE_VERSION
  }
}
