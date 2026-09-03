# KubeSphere Continuous Delivery Design — Sample Service "hello-web"

## 1. Input Assumptions

| Item | Assumption |
|------|-----------|
| **Service** | `hello-web` — a stateless HTTP service, container image built from a Git repo, deployed to Kubernetes |
| **Source repo** | `https://github.com/example-org/hello-web` (private, GitHub) |
| **Manifest repo** | `https://github.com/example-org/hello-web-k8s` (GitOps, Kustomize overlays: dev/staging/prod) |
| **Registry** | Docker Hub (`docker.io/exampleorg/hello-web`) — replace with Harbor/ACR/GCR as needed |
| **KubeSphere** | v4.2.x with DevOps + GitOps (ArgoCD) extensions enabled |
| **DevOps project namespace** | `demo-project` (already created) |
| **Environments** | dev → staging → prod, each in its own Kubernetes namespace (`hello-dev`, `hello-staging`, `hello-prod`) |
| **Pipeline type** | Jenkinsfile-based multi-branch pipeline in KubeSphere DevOps + ArgoCD Application for GitOps deploy |
| **Auth method** | GitHub Personal Access Token (PAT) for Git; Docker Hub username/password for registry; kubeconfig for cluster access |
| **No existing credentials** | All credentials are created from scratch in this design |

## 2. Acceptance Criteria

1. **Credential correctness**: Every Secret uses `type: credential.devops.kubesphere.io/*` (NOT `Opaque`), with correct `stringData` keys per SKILL.md table.
2. **Credential sync**: After creation, `credential.devops.kubesphere.io/syncstatus` annotation becomes `successful` (synced to Jenkins).
3. **Pipeline runs end-to-end**: Multi-branch pipeline checks out code, builds/pushes image, updates manifest repo, and triggers ArgoCD sync.
4. **GitOps boundary**: ArgoCD Application references the manifest repo via GitRepository; no hardcoded tokens in pipeline scripts.
5. **Deployment verification**: Post-deploy stage validates rollout status, health endpoint, and ArgoCD sync health.
6. **Rollback**: Documented `kubectl rollout undo` + ArgoCD revert + Git revert procedures; rollback tested in staging before prod.
7. **Least privilege**: Credentials scoped to `demo-project` namespace; GitHub PAT limited to repo scope; Docker Hub token is read-write (push) only; kubeconfig scoped to target namespaces.
8. **No Opaque secrets**: Verified by `kubectl get secrets -n demo-project -o jsonpath='{.items[*].type}'` — all types start with `credential.devops.kubesphere.io/`.
