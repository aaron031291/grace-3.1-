# Multi Armed Bandit

**File:** `ml_intelligence/multi_armed_bandit.py`

## Overview

Multi-Armed Bandit System - Intelligent Exploration/Exploitation

Optimizes learning topic selection using bandit algorithms.
Balances exploring new topics vs exploiting known high-value topics.

Algorithms Implemented:
- UCB1 (Upper Confidence Bound)
- Thompson Sampling (Bayesian)
- Epsilon-Greedy
- Contextual Bandits
- Exp3 (Exponential-weight algorithm for Exploration and Exploitation)

## Classes

- `BanditAlgorithm`
- `TopicArm`
- `BanditContext`
- `MultiArmedBandit`

## Key Methods

- `add_arm()`
- `select_arm()`
- `update_reward()`
- `get_arm_stats()`
- `get_all_stats()`
- `recommend_next_topics()`
- `save_state()`
- `load_state()`
- `get_bandit()`

---
*Grace 3.1*
