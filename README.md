# FaultSentinel

<p align="center">
  <strong>Calibrated AI Incident Triage & Evidence-Grounded Root Cause Analysis</strong>
</p>

<p align="center">
  An AI-assisted incident intelligence platform that detects anomalous system-log windows, selectively escalates high-risk events, retrieves historical evidence, performs deterministic reasoning, and generates evidence-grounded incident explanations.
</p>

<p align="center">

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)
[![Terraform](https://img.shields.io/badge/Terraform-IaC-7B42BC?style=flat-square&logo=terraform&logoColor=white)](https://www.terraform.io/)
[![Tests](https://img.shields.io/badge/Backend%20Tests-520%20passed-success?style=flat-square)](#testing)
[![v1.1](https://img.shields.io/badge/Release-v1.1.0-purple?style=flat-square)](#release)
[![License](https://img.shields.io/badge/License-MIT-black?style=flat-square)](#license)

</p>

---

## Table of Contents

- [Overview](#overview)
- [Why FaultSentinel](#why-faultsentinel)
- [Core Idea](#core-idea)
- [System Architecture](#system-architecture)
- [End-to-End Pipeline](#end-to-end-pipeline)
- [Key Features](#key-features)
- [Incident Replay Lab](#incident-replay-lab)
- [Reliability & Fault Injection Lab](#reliability--fault-injection-lab)
- [Calibration Drift Monitor](#calibration-drift-monitor)
- [Evidence Graph & Provenance](#evidence-graph--provenance)
- [Decision Passport](#decision-passport)
- [Human Adjudication](#human-adjudication)
- [Recruiter Tour Mode](#recruiter-tour-mode)
- [Research Question](#research-question)
- [Detection Baselines](#detection-baselines)
- [Datasets](#datasets)
- [Evaluation Methodology](#evaluation-methodology)
- [Evaluation Results](#evaluation-results)
- [What the Results Mean](#what-the-results-mean)
- [Production Architecture](#production-architecture)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [API](#api)
- [Frontend](#frontend)
- [Local Development](#local-development)
- [Docker](#docker)
- [Testing](#testing)
- [Observability](#observability)
- [Security](#security)
- [Reproducibility](#reproducibility)
- [Deployment Architecture](#deployment-architecture)
- [Release](#release)
- [Engineering Validation](#engineering-validation)
- [Limitations](#limitations)
- [Design Principles](#design-principles)
- [Roadmap](#roadmap)
- [Author](#author)
- [License](#license)

---

# Overview

**FaultSentinel** is an AI-assisted incident intelligence platform designed for high-volume system-log environments.

Traditional monitoring systems are effective at detecting anomalies, but they often leave engineers with the difficult question:

> **Why did this happen, and what evidence supports the diagnosis?**

A naive LLM-based monitoring system creates another problem: sending every log window to an LLM is expensive, slow, difficult to audit, and unnecessary for normal traffic.

FaultSentinel addresses both problems by separating:

1. **Detection**
2. **Risk calibration**
3. **Selective escalation**
4. **Evidence retrieval**
5. **Deterministic reasoning**
6. **LLM explanation**
7. **Faithfulness verification**
8. **Provenance and auditability**

The system therefore acts as an **AI-assisted investigation layer** rather than simply an LLM chatbot for logs.

---

# Why FaultSentinel?

Modern infrastructure can produce millions of log messages.

A naive architecture looks like this:

```text
Millions of Log Windows
          │
          ▼
        LLM
          │
          ▼
 Expensive Investigation
