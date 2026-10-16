# ProctorAI Coding Sandbox Security Architecture & Assessment

## 1. Executive Summary & Philosophy

ProctorAI implements candidate code execution as a **distinct security boundary**, entirely decoupled from the core FastAPI application server. All candidate submissions are considered **untrusted and adversarial by default**.

Under no circumstances is candidate code executed inside the main API process or evaluated using Python's `eval()` or `exec()` in the API server. Execution occurs strictly within isolated, ephemeral execution environments with bounded resource quotas, network denial, and non-root privileges.

> [!CAUTION]
> **Important Security Disclosure:**
> No software sandbox should ever be claimed to be 100% impenetrable without continuous independent validation, penetration testing, and defense-in-depth virtualization. This document assesses the current isolation mechanisms and outlines mandatory hardening requirements before production deployment to public untrusted networks.

---

## 2. Threat Model & Adversarial Vectors

The sandbox protects against the following primary threat categories:

| Threat Vector | Attack Mechanism | Sandbox Countermeasure |
|---|---|---|
| **CPU Starvation (DoS)** | Infinite loops (`while True: pass`) | Hard wall-clock timeout (`timeout_seconds`), CPU quota (`cpu_quota=50000`), and immediate `SIGKILL` termination. |
| **Memory Exhaustion (OOM)** | Giant array allocations (`[0] * 10**8`) | Docker `mem_limit="128m"` and subprocess memory error trapping; returns `MEMORY_LIMIT_EXCEEDED` without host degradation. |
| **Output Flooding** | Runaway stdout generation (`while True: print(...)`) | Hard buffer ceiling (`SANDBOX_MAX_OUTPUT_BYTES = 64KB`); returns `OUTPUT_LIMIT_EXCEEDED` to prevent disk/pipe exhaustion. |
| **Process Multiplication** | Fork bombs (`while True: os.fork()`) | Docker `pids_limit=32` restricting maximum concurrent processes. |
| **Network Egress / SSRF** | Outbound socket connections, port scanning, metadata service probing (`169.254.169.254`) | `network_mode="none"` in Docker (zero network interfaces). In fallback mode, socket instantiation is denied by security wrapper policy. |
| **Credential Harvesting** | Inspecting `os.environ` for DB credentials, JWT secrets, API keys | Never mount host environment; subprocess runner creates clean environment with only sanitized `PATH` and `PYTHONUNBUFFERED`. |
| **Host Escape / Container Breakout** | Mounting `/var/run/docker.sock` to gain root control over host | Zero mounts of host Docker socket or application directories. Container root filesystem is mounted `read_only=True`. |
| **Privilege Escalation** | SUID binaries or gaining root within container | `user="1000:1000"` (non-root), `security_opt=["no-new-privileges:true"]`, and `cap_drop=["ALL"]`. |
| **Test Case Exfiltration** | Inferring hidden test case inputs and expected outputs | Hidden test inputs and outputs are strictly stripped before returning API responses to candidates. |
| **Runner Service Exhaustion** | Flooding execution requests | Token-bucket sliding window rate limiting (`SandboxRateLimiter`) with `429 Too Many Requests`. |
| **Unauthorized Runner Invocations** | Bypassing API control plane to invoke runner directly | Authenticated runner interface requiring shared secret `X-Runner-Token`. |

---

## 3. Implemented Sandbox Architecture

```
[ Candidate Browser ]
         │ (Submits Code via HTTPS)
         ▼
[ ProctorAI API Control Plane ]
  ├── Rate Limiter (Sliding Window, 429 on Burst)
  ├── Input Sanitizer & Problem Specs (Hidden Tests Stripped)
  ├── Submission Queue (QUEUED -> PROCESSING -> COMPLETED)
  └── Runner Boundary Client (Authenticates via X-Runner-Token)
         │
         ▼  (Strict Network Denial, Zero Secrets Inherited)
[ Isolated Sandbox Execution Boundary ]
  ├── Docker Runner (Default Production Mode):
  │     ├── Non-Root User: UID 1000:1000
  │     ├── Network Mode: "none" (Zero Ingress/Egress)
  │     ├── Read-Only Root Filesystem + 16MB tmpfs
  │     ├── Resource Limits: 128MB RAM, 50% CPU Quota, 32 PIDs
  │     ├── All Linux Capabilities Dropped (cap_drop=["ALL"])
  │     └── Disposable (remove=True, destroyed immediately)
  │
  └── Subprocess Runner (Clean Fallback Mode):
        ├── Clean Environment (Zero App Secrets / DB URLs)
        ├── Ephemeral Working Directory (tempfile.TemporaryDirectory)
        ├── Socket Monkeypatching (Network Denial)
        ├── Output Capping (64KB Ceiling)
        └── Hard Wall-Clock Process Termination
```

---

## 4. Limitations of Current Isolation Mechanisms

While the current architecture protects against application-level exploits and common candidate abuse, several architectural limitations must be understood:

1. **Shared Linux Kernel (Containerization):**
   - Standard Docker containers share the host Linux kernel. Any unpatched kernel zero-day vulnerability (e.g., local privilege escalation, `io_uring` vulnerabilities) could theoretically allow container escape if malicious code triggers a kernel bug.
2. **Subprocess Fallback Mode Limitations:**
   - In environments where Docker is disabled (e.g. Windows unit test environments), Python-level monkeypatching of `socket` and `urllib` is used. While effective against standard candidate code and import attempts, native C extensions (`ctypes`, `cffi`) could theoretically bypass Python-level monkeypatching if enabled.
3. **Hardware / Cache Side Channels:**
   - On multi-tenant shared CPU cores, microarchitectural side-channel attacks (Spectre/Meltdown variants) could theoretically measure cache latency if hyperthreading is enabled across untrusted workloads.

---

## 5. Required Hardening Before Public Production Deployment

Before deploying ProctorAI to public internet environments where arbitrary untrusted users can execute arbitrary binary/compiled code, the following infrastructure hardening is **mandatory**:

1. **MicroVM-Level Virtualization:**
   - Migrate execution backend to **AWS Firecracker** or **Cloud Hypervisor**. Firecracker provisions lightweight Linux virtual machines with their own isolated kernel in <5 milliseconds, completely eliminating kernel-sharing risks.
2. **User-Space Kernel Emulation:**
   - Alternatively, configure the Docker container runtime to use **Google gVisor** (`runsc`) or **Kata Containers**. gVisor implements a user-space kernel in Go that intercepts all guest syscalls, insulating the host Linux kernel from direct interaction.
3. **Seccomp-BPF Syscall Filtering:**
   - Deploy strict seccomp-bpf whitelist profiles that block dangerous syscalls (`ptrace`, `bpf`, `keyctl`, `mount`, `chroot`, `sys_rawio`, etc.).
4. **VPC Network Air-Gapping:**
   - Host execution runner nodes in an isolated AWS/GCP subnet with a security group that blocks all outbound Internet egress (`0.0.0.0/0`) and has no route to the internal database or Kubernetes control plane.
5. **Independent Security Validation:**
   - Engage an independent third-party penetration testing firm to conduct black-box and gray-box sandbox escape audits.
