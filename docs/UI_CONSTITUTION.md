# AI Command Center (ACC) UI Constitution

Version: 1.0
Status: Authoritative UI Governance Document
Scope: All ACC UI, UX, Visualization, Layout, Interaction, Themes, Navigation, and Operator Experience

---

# Article 1 — Purpose

The purpose of the ACC user interface is not to provide a chat application.

The purpose of the ACC user interface is to provide an operational command center for observing, understanding, controlling, and auditing an AI-driven workspace operating system.

ACC is an AI Operating System.

The UI exists to expose system state and enable operator control.

The UI must always prioritize:

1. Awareness
2. State Visibility
3. Control
4. Explainability
5. Trust
6. Verification

before aesthetics or novelty.

---

# Article 2 — Design Philosophy

## Principle 1 — State Over Conversation

Traditional AI products place conversation at the center.

ACC places system state at the center.

The operator must always understand:

* Current Goal
* Current Execution
* Current Agents
* Current Approvals
* Current Knowledge State
* Current Provider Health

without opening a chat.

---

## Principle 2 — Operations Before Settings

The most important information must always be operational information.

Operators should never navigate through settings menus to understand system activity.

---

## Principle 3 — Everything Must Be Observable

Any backend subsystem visible in architecture diagrams must eventually have a dedicated UI surface.

Invisible systems are considered incomplete systems.

---

## Principle 4 — Trust Through Evidence

The UI must show:

* Evidence
* Receipts
* Status
* Sources
* Validation Results

The UI must never encourage trust based on AI confidence alone.

---

## Principle 5 — Human Command Authority

ACC may recommend.

ACC may execute.

ACC may automate.

ACC may never obscure operator authority.

Human approval pathways must remain visible and understandable.

---

# Article 3 — Visual Identity

ACC shall visually represent:

* Mission Control
* Operations Center
* Command Bridge
* AI Operating System

ACC shall not resemble:

* Messaging Applications
* Social Networks
* Consumer Chatbots
* Generic Admin Dashboards

---

# Article 4 — Theme System

ACC shall support three official themes.

---

## Theme 1 — Mission Control (Default)

Purpose:

Primary operational experience.

Visual Characteristics:

* Dark graphite background
* Layered surfaces
* High information density
* Clear hierarchy

Palette:

Background: #0E1116

Surface Primary: #171B22

Surface Secondary: #1D2330

Border: #262C36

Text Primary: #F5F7FA

Text Secondary: #9CA7B8

---

## Theme 2 — Executive

Purpose:

Leadership dashboards.

Palette:

Background: #F7F8FA

Surface: #FFFFFF

Border: #DCE1E8

Text Primary: #1E293B

Text Secondary: #64748B

---

## Theme 3 — Tactical

Purpose:

Advanced operators.

Characteristics:

* Dense telemetry
* High contrast
* Minimal whitespace
* Maximum situational awareness

---

# Article 5 — Color Constitution

Colors communicate subsystem ownership.

Colors are semantic.

Colors are never decorative.

---

## Goals

Color:

Amber

Purpose:

Objectives
Planning
Intent

---

## Executions

Color:

Blue

Token:

`EXECUTION_BLUE`

Purpose:

Work
Progress
Runtime Activity

---

## Agents

Color:

Purple

Purpose:

Autonomous Operations

---

## World Model

Color:

Teal

Purpose:

Knowledge
Relationships
Memory

---

## Providers

Color:

Cyan

Purpose:

Infrastructure
Connectivity

---

## Approvals

Color:

Orange

Purpose:

Human Attention Required

---

## Success

Color:

Green

Purpose:

Healthy
Verified
Operational

---

## Warning

Color:

Yellow

Purpose:

Risk
Degradation

---

## Failure

Color:

Red

Purpose:

Action Required

---

# Article 6 — Information Hierarchy

Every screen must answer:

1. What is the system trying to achieve?
2. What is currently executing?
3. What requires attention?
4. What changed recently?
5. What should happen next?

Information hierarchy always follows this order.

---

# Article 7 — Hero Sections

Every primary workspace must begin with a Hero Section.

Hero Sections establish context.

Hero Sections are mandatory.

---

## Hero Structure

Must contain:

* Workspace Name
* Current State
* Primary Metric
* Critical Summary
* Immediate Action

---

## Example

Execution Runtime

1 Active Run

Current Step:
Validate Receipts

3 / 8 Steps Complete

---

# Article 8 — Dashboard Constitution

The Command Center Dashboard is the primary ACC screen.

The Dashboard is the operational homepage.

---

## Dashboard Layout

### Zone 1 — Mission Hero

Top 30%

Displays:

* Active Goal
* Goal Status
* Progress
* Current Focus

---

### Zone 2 — Operations Grid

Middle 40%

Displays:

* Executions
* Agents
* Approvals
* Providers

---

### Zone 3 — System Awareness

Bottom 30%

Displays:

* World Model
* Knowledge Statistics
* Recent Changes
* Workspace Health

---

# Article 9 — Navigation Constitution

Navigation exists to expose operational domains.

Navigation shall not mirror backend folders.

---

## Primary Workspaces

Mandatory:

* Command Center
* World Model
* Executions
* Agents
* Goals
* Approvals
* Providers
* Automation
* System

---

## Chat

Chat is a workspace.

Chat is not the home screen.

Chat is not the primary operating surface.

---

# Article 10 — Card Standards

All cards must contain:

Header

Primary Metric

Status Indicator

Timestamp

Action Area

---

## Card Density

Cards must prioritize information.

Decorative elements are prohibited.

---

# Article 11 — Status Badges

Every subsystem must expose status badges.

---

## Status Types

READY

RUNNING

WAITING

BLOCKED

PAUSED

FAILED

COMPLETE

DEGRADED

OFFLINE

---

## Badge Rules

Status must be visible without opening details.

Status must always have both:

* Color
* Text

Never color alone.

---

# Article 12 — World Model Standards

The World Model is a first-class workspace.

It is not an advanced feature.

It is a core operating surface.

---

## Required Panels

Knowledge Graph

Entity Explorer

Relationship Explorer

Mutation Journal

Selection Inspector

---

# Article 13 — Execution Center Standards

Execution Center must provide complete runtime visibility.

Operators must be able to reconstruct:

* What happened
* Why it happened
* What result occurred

without reading logs.

---

## Required Panels

Execution List

Execution Timeline

Execution Detail

Receipt Viewer

Truth Validation

---

# Article 14 — Agent Monitor Standards

Agent activity must never be hidden.

---

## Required Panels

Active Agents

Agent State

Pipeline Progress

Task Assignment

Execution History

---

# Article 15 — Approval Center Standards

Approval workflows are operationally critical.

Approvals must remain visible even when no modal is open.

---

## Required Panels

Pending Queue

Decision History

Risk Classification

Approval Statistics

---

# Article 16 — Goal Dashboard Standards

Goals represent system intent.

Goals must remain visible across the application.

---

## Required Panels

Goal List

Goal Detail

Plan Preview

Goal Progress

Goal History

---

# Article 17 — Top Bar Constitution

The Top Bar is the global operational status bar.

It must always display:

* Active Goal
* Kernel State
* Active Agents
* Pending Approvals
* Current Model
* Time

without navigation.

---

# Article 18 — Empty State Standards

Empty states must remain informative.

Never display:

"No Data"

Instead display:

* Why data is missing
* What action creates data
* Suggested next step

---

# Article 19 — Animation Standards

Animations exist to communicate state transitions.

Animations must never exist solely for decoration.

Allowed:

* Status transitions
* Progress updates
* Navigation transitions

Prohibited:

* Decorative motion
* Unnecessary particle effects
* Attention-seeking animations

---

# Article 20 — Accessibility

Every operational state must be communicated using:

* Text
* Shape
* Color

No information may rely solely on color.

---

# Article 21 — Constitutional UI Rules

UI code may:

* Read AppState
* Render State
* Publish Events

UI code may not:

* Modify repositories
* Directly call services
* Write databases
* Become a second source of truth

AppState remains the sole UI authority.

---

# Article 22 — Definition of UI Completion

A backend subsystem is not considered complete until:

1. Its state is projected into AppState.
2. Its state is visible in the UI.
3. Operators can understand its status.
4. Operators can take appropriate action.
5. Constitutional verification passes.

Until then, the subsystem remains operationally incomplete.

---

END OF ACC UI CONSTITUTION V1
