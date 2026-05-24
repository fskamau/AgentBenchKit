# Docker execution and security limitations

## Default containment settings

The Docker runner constructs a named `docker run --rm` container with `--pull=never`, `--network=none`, `--read-only`, `--cap-drop=ALL`, `--security-opt=no-new-privileges`, `--pids-limit=128`, memory and CPU limits, non-root UID/GID `65534:65534`, a restricted writable `/tmp` tmpfs, and one writable bind mount of a **disposable repository copy** at `/workspace`. The runner attempts `docker rm -f` in `finally`, even when the Docker command times out. No original benchmark source tree is mounted into the container.

Dependencies, if required, must either be baked into a prebuilt image or available from a supplied offline wheelhouse. `--wheelhouse DIR` maps those wheels read-only into the container and installs `requirements.txt` into `/workspace/.deps` with `pip --no-index`. In every case, dependency build/install scripts are executable code and should be treated as potentially hostile.

## What containers cannot guarantee

Docker isolation is **not** equivalent to a hardened virtual-machine boundary against arbitrary attacker-supplied programs. Kernel vulnerabilities, exposed host daemons, insufficient seccomp/AppArmor/SELinux policy, resource abuse, writable mounts, and Docker daemon privilege configurations can defeat assumptions. The default runner does not configure a custom seccomp profile or user namespaces. A malicious subprocess may fork children or exploit runtime bugs. For hostile third-party agents or untrusted patches, use dedicated locked-down VMs/microVMs with hard timeouts, separate nonprivileged Docker daemons, further filesystem restrictions and network filtering enforced outside the container.

Docker image supply-chain integrity is also relevant. Pin images by digest in serious reproducibility environments, verify build provenance, and avoid implicit latest tags. The example `docker/Dockerfile` names a specific versioned base; the CLI default `python:3.11-slim` can change between pulls. Docker jobs must pull/build the image explicitly **before** evaluation since the evaluation container has network access disabled.

## Local runner

`--engine local --allow-local` deliberately runs subprocesses on the host. It is provided for **trusted unit-test fixtures only**, without a security guarantee. The local runner uses argv rather than a shell, but test code itself can run any processes and may leave child processes after a timeout. Never select it to evaluate unknown downloaded repository code.

## Operational checks

```bash
docker version
docker pull python:3.11-slim
agentbenchkit sandbox status
agentbenchkit benchmark run pagination-boundary --engine docker --output reports-out/docker-smoke
```

Inspect output for `inconclusive_environment` and raw Docker stderr. Failure to find the image, daemon, or required dependency is environmental and must not be labeled agent error.
