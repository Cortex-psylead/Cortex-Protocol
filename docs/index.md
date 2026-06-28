---
layout: default
title: Cortex Protocol
description: An Open Standard for Neurophysiological Data Sovereignty in Human-AI Interaction
---

<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

  /* Forzar el fondo global y tipografía premium */
  body, .markdown-body {
    background-color: #0d1117 !important;
    color: #c9d1d9 !important;
    font-family: 'Space Grotesk', -apple-system, BlinkMacSystemFont, sans-serif !important;
    max-width: 850px;
    margin: 0 auto;
    padding: 40px 20px;
    line-height: 1.6;
  }

  /* Corrección absoluta de Encabezados */
  h1, h2, h3, h4, .markdown-body h1, .markdown-body h2, .markdown-body h3 {
    color: #f0f6fc !important;
    font-weight: 600 !important;
    border-bottom: 1px solid #21262d !important;
    padding-bottom: 8px;
    margin-top: 32px;
  }
  h1 { font-size: 2.2em !important; border-bottom: none !important; }
  h3 { font-size: 1.3em !important; border-bottom: none !important; color: #8b949e !important; }

  /* Enlaces estilizados */
  a, .markdown-body a {
    color: #58a6ff !important;
    text-decoration: none !important;
    font-weight: 500;
  }
  a:hover { text-decoration: underline !important; }

  /* SOLUCIÓN AL BUG DE TABLAS: Forzar colores oscuros sobre la plantilla */
  table, tr, td, th, .markdown-body table, .markdown-body tr, .markdown-body td, .markdown-body th {
    background-color: #161b22 !important;
    color: #e6edf3 !important;
    border: 1px solid #30363d !important;
  }
  th, .markdown-body th {
    background-color: #21262d !important;
    color: #f0f6fc !important;
    font-weight: 600 !important;
  }
  tr:nth-child(even) { background-color: #0d1117 !important; }

  /* SOLUCIÓN AL BUG DE CÓDIGO (Quick Start invisible) */
  div.highlighter-rouge, pre, code, .highlight, .markdown-body pre, .markdown-body code {
    background-color: #161b22 !important;
    color: #ff7b72 !important; /* Color de comando llamativo */
    border: 1px solid #30363d !important;
    border-radius: 8px !important;
  }
  pre, y pre code {
    font-family: 'JetBrains Mono', monospace !important;
    color: #e6edf3 !important;
    padding: 16px !important;
  }

  /* Cita de Autor con Efecto de Brillo Criptográfico */
  blockquote, .markdown-body blockquote {
    border-left: 4px solid #00f2fe !important;
    background: linear-gradient(90deg, #111827 0%, #1f2937 100%) !important;
    color: #acbac7 !important;
    padding: 16px !important;
    margin: 24px 0 !important;
    border-radius: 0 8px 8px 0;
    box-shadow: 0 4px 20px rgba(0, 242, 254, 0.08);
  }

  /* Ajustes estéticos extras */
  hr { background-color: #30363d !important; height: 1px !important; border: none !important; }
  li { margin-bottom: 6px; }
</style>

# 🧠 Cortex Protocol

### An Open Standard for Neurophysiological Data Sovereignty in Human-AI Interaction

[![License: GPL v3](https://img.shields.io/badge/License-GPL_v3-blue.svg)](https://github.com/Cortex-psylead/Cortex-Protocol/blob/main/LICENSE)
[![Milestone 0](https://img.shields.io/badge/Milestone_0-Locked_🔒-brightgreen)](https://github.com/Cortex-psylead/Cortex-Protocol/blob/main/ROADMAP.md)
[![Standard: RFC v0.1](https://img.shields.io/badge/Standard-RFC_v0.1-orange)](https://github.com/Cortex-psylead/Cortex-Protocol/blob/main/STANDARD.md)

> *"The standard does not need to be everywhere. It needs to make everywhere safer."*
---

## What is Cortex Protocol?

Cortex Protocol is an open, royalty-free technical standard for protecting neurophysiological data sovereignty when an AI agent interacts with human biometric data.

Think of it as what **HTTPS did for web security**, applied to the human nervous system.

---

## Core Guarantees

| Guarantee | Mechanism |
| :--- | :--- |
| Raw biometric data never leaves your device | SAL air-gap boundary |
| AI agents receive only anonymized tensors | Two-phase HMAC transformation |
| Clinical thresholds are cryptographically enforced | White Branch signed CCMs |

---

## Quick Start

    git clone https://github.com/Cortex-psylead/Cortex-Protocol
    cd Cortex-Protocol
    pkg install python-numpy python-scipy matplotlib -y
    python src/sal/cognitive_shield.py

Expected output: baseline establishment, CDI block event, and `cortex_demo.png` saved in the project root.

---

## Documentation

| Document | Description |
| :--- | :--- |
| [Architecture](https://github.com/Cortex-psylead/Cortex-Protocol/blob/main/ARCHITECTURE.md) | System layers and sovereignty loop |
| [Clinical Bridge](https://github.com/Cortex-psylead/Cortex-Protocol/blob/main/CLINICAL-BRIDGE.md) | Evidence-based clinical protocols |
| [Governance](https://github.com/Cortex-psylead/Cortex-Protocol/blob/main/GOVERNANCE.md) | Governance roles and anti-capture provisions |
| [Security Policy](https://github.com/Cortex-psylead/Cortex-Protocol/blob/main/SECURITY.md) | Threat model and cryptographic governance |
| [Standard Specification](https://github.com/Cortex-psylead/Cortex-Protocol/blob/main/STANDARD.md) | SHALL/SHOULD/MAY requirements |
| [Roadmap](https://github.com/Cortex-psylead/Cortex-Protocol/blob/main/ROADMAP.md) | Milestones M0 to M3 |

---

## Contribute

We need three types of collaborators:

- 🧠 **Clinical researchers** — Validate CDI thresholds. Become the first Governance Node.
- ⚙️ **Engineers** — Build the BrainFlow adapter, integrate TPM 2.0.
- 📋 **Standards specialists** — IEEE P2510 engagement, EU AI Act compliance.

[Open an Issue](https://github.com/Cortex-psylead/Cortex-Protocol/issues) to get started.

---

## License

GNU GPL v3 — permanently open. No entity can make this standard proprietary.

---

[GitHub Repository](https://github.com/Cortex-psylead/Cortex-Protocol) · [Contributing](https://github.com/Cortex-psylead/Cortex-Protocol/blob/main/CONTRIBUTING.md) · [Security](https://github.com/Cortex-psylead/Cortex-Protocol/blob/main/SECURITY.md)

