# Swarm Communication Bus

**File:** `cognitive/swarm_comms.py`

## Purpose

Real-time inter-agent communication and shared task log

## Overview

Swarm Communication Bus + Shared Task Log

Gives KNN sub-agents the ability to:
1. Talk to each other in real-time during a search
2. See what every other agent has found so far
3. React to each other's discoveries (Agent B found X → Agent A searches X deeper)
4. See the full history of what's been searched/uploaded/discovered (no wasted work)

Architecture:
┌─────────────────────────────────────────────────────────┐
│                    SWARM COMM BUS                        │
│                                                           │
│  ┌──────────────────────────────────────────────────┐    │
│  │              SHARED DISCOVERY FEED                │    │
│  │  Real-time stream of what every agent is finding  │    │
│  │  Any agent can read + react to any other agent   │    │
│  └──────────────────────────────────────────────────┘    │
│                                                           │
│  ┌──────────────────────────────────────────────────┐    │
│  │              SHARED TASK LOG                      │    │
│  │  Complete history of every search, upload, ingest │    │
│  │  Agents check before searching (no duplicate work)│    │
│  └──────────────────────────────────────────────────┘    │
│                                                           │
│  ┌──────────────────────────────────────────────────┐    │
│  │              REACTIVE TRIGGERS                    │    │
│  │  "Agent B found X" → triggers Agent A to search X │    │
│  │  Cross-pollination between agents in real-time    │    │
│  └──────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘

## Classes

- `SwarmMessage`
- `TaskLogEntry`
- `SwarmCommBus`
- `SharedTaskLog`

## Key Methods

- `post()`
- `get_recent()`
- `get_discoveries_by()`
- `get_all_topics_found()`
- `register_reactive_listener()`
- `register_reactive_queue()`
- `get_stats()`
- `log_task()`
- `was_already_done()`
- `get_history_for()`
- `get_recent()`
- `get_stats()`
- `get_swarm_comm_bus()`
- `get_shared_task_log()`

## Database Tables

None (no DB tables)

## Dataclasses

- `SwarmMessage`
- `TaskLogEntry`

## Connects To

Self-contained

## How It Works

This module is part of Grace 3.1's autonomous intelligence system.
See the source code docstring and inline comments for detailed logic.

---
*Auto-generated documentation for Grace 3.1 rocketdev branch*
