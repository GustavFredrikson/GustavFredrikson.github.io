---
title: cka-dojo
summary: A command-line dojo for the Certified Kubernetes Administrator exam. It builds real, disposable kubeadm clusters, breaks them on purpose and grades the state you leave behind.
year: 2026
role: Design & development
tags: [Go, Kubernetes, CLI, Education]
link: https://github.com/GustavFredrikson/cka-dojo
order: 1
cover: ../../assets/work/cka-dojo.png
coverDark: ../../assets/work/cka-dojo-dark.png
---

Most CKA practice is either reading or clicking through a hosted sandbox that hides the parts of a cluster you most need to understand. I wanted to practise the way the exam works: on a real cluster, from a shell, with no hints about which command to type. So I built `dojo`, a Go CLI that provisions a four-machine Kubernetes cluster in local VMs and turns it into a training ground.

## Graded on state, not commands

Every exercise starts a scenario, prints a task and then steps aside. When you run `dojo grade`, it inspects the cluster itself — Pods, endpoints, policies, certificates, static manifests, systemd units — and checks the result against the requirements. It doesn't matter whether you used `kubectl edit`, a YAML file or Helm, only whether the cluster ends up right.

```
$ dojo learn services
Services learning path
   LEVEL  STAGE            EXERCISE                      TITLE
   -----  -----            --------                      -----
✓  0      Learn            mental model                  Services
·  1      Follow           services-follow               Create and expose a healthy web workload
🔒  2      Build            services-build                Expose a workload without a recipe
🔒  3      Inspect          services-inspect              Watch selectors become endpoints
🔒  4      Fix, guided      services-guided-selector-fix  Repair a known selector mismatch
🔒  5      Fix, contextual  services-no-endpoints         A Service that does not answer
·  2      Build            services-nodeport             Expose an application on a fixed node port
·  5      Fix, contextual  services-target-port          A Service has endpoints but requests fail
🔒  2      Build            services-types                The other two Service types
Progress: 0/8 attempted · 0/8 passed · 0/8 mastered
Legend: · available  ↻ attempted  ✓ passed  ★ mastered  🔒 prerequisites incomplete
```

## A deliberate ladder

Each topic climbs the same steps: learn, follow, build, inspect, guided fix, contextual fix, diagnose and finally an exam-style task. Passing an exercise unlocks the next one, and mastery can require passing twice, the last time without hints. A recommender ranks what to practise next from your own attempt history, weighing exam weight, gaps, recency and stage, and shows its reasoning.

The curriculum covers 96 exercises in 17 modules: workloads, scheduling, RBAC, Services and DNS, NetworkPolicy, Ingress and the Gateway API, storage, admission, etcd backup and restore, Helm and Kustomize, troubleshooting, and the cluster lifecycle — bootstrapping with kubeadm, upgrades and a highly available control plane.

## Owning the install

The cluster runs in [Lima](https://lima-vm.io) VMs: a control-plane node, two workers and a separate workstation that is not part of the cluster. That separation is what makes the hardest labs possible — a scenario can stop the kubelet on a worker or corrupt a control-plane manifest without breaking the shell you are fixing it from. For the same reason `dojo` installs Kubernetes itself with kubeadm rather than using a ready-made template: to break the installation, you have to own it.

Labs can also declare variants. `node-not-ready` might stop the kubelet or containerd — same symptom, different diagnosis — chosen from a recorded seed, so repeating a lab doesn't mean repeating the answer.

## How it is built

The engine and the content are kept strictly apart. Exercises are YAML and Markdown — faults, graders, hints and solutions — embedded in a single self-contained binary, so adding curriculum never requires Go. Underneath sit a provider interface (Lima today, with an in-memory fake so the engine is tested without VMs), a fault vocabulary for breaking a cluster and a grader vocabulary for deciding it is fixed. Every exercise has been run end to end on a live cluster: graded broken, fixed by hand, graded again, reset and graded once more.
