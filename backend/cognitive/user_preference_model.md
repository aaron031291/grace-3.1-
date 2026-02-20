# User Preference Model

**File:** `cognitive/user_preference_model.py`

## Purpose

Learns and remembers user preferences across sessions

## Overview

User Preference Model

Learns and remembers user preferences across sessions:
- Preferred programming language
- Technical level (beginner/intermediate/expert)
- Response style (concise/detailed)
- Topics of interest
- Common question patterns

Built from Genesis ID session tracking and conversation history.
Feeds into chat intelligence to personalize responses.

## Classes

- `UserPreference`
- `UserPreferenceEngine`

## Key Methods

- `observe_interaction()`
- `get_preferences()`
- `get_system_prompt_additions()`

## Database Tables

- `user_preferences`

## Dataclasses

None

## Connects To

Self-contained

## How It Works

This module is part of Grace 3.1's autonomous intelligence system.
See the source code docstring and inline comments for detailed logic.

---
*Auto-generated documentation for Grace 3.1 rocketdev branch*
