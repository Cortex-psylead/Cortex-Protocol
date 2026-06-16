# NEUTRALITY.md
## Cognitive Neutrality Architecture — Canonical Doctrine
**Document ID: ARCH-NEUTRALITY-001 | Version: 1.0**
**Cortex Protocol — Protocol Stewards & White Branch**
**Status: Normative — referenced by STANDARD.md, CONSTITUTION.md, GOVERNANCE.md**

---

> *"Neutrality is not the absence of opinion. It is the structural impossibility of injecting one."*

---

## Preamble

This document formally defines the **Cognitive Neutrality Clause** of the Cortex Protocol — the architectural invariant that prevents any institutional, political, commercial, or ideological actor from using the protocol's own infrastructure to influence the cognitive state of its users.

The Cognitive Neutrality Clause is not a policy declaration. Policies can be changed by actors with sufficient authority. The Clause is a **mathematical and architectural constraint** enforced at the code level, whose violation requires rewriting core modules, not amending a terms-of-service document.

This is the foundational distinction between the Cortex Protocol and every privacy policy, clinical ethics board, and AI safety framework that preceded it: **we do not ask institutions to behave neutrally. We make non-neutral behavior technically impossible by design.**

This document:
1. Defines Cognitive Neutrality as a formal architectural invariant (§1)
2. Maps each enforcement mechanism to its implementing module (§2)
3. Introduces the **Split-Gate Doctrine** — the dual-mode operational architecture for research and commercial deployments (§3)
4. Catalogs the residual honest vulnerabilities that the current architecture does not fully close (§4)
5. Specifies the governance process for modifications to this doctrine (§5)

---

## §1 — Cognitive Neutrality: Formal Definition

### 1.1 The Invariant

**Cognitive Neutrality** is satisfied if and only if:
