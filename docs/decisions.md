# Design decisions

## Context
Self-service deployment for a small infrastructure team. Inspired by Husnain Waleed's infrastructure support, systems administration, security and DevOps background. No employer systems or data are included.

## Scope
Start with one reproducible workflow and explicit failure behavior. Python's standard library keeps local validation accessible. Kubernetes and cloud integration remain separate from local correctness tests.

## Tradeoff
Small, inspectable tooling is easier to explain and test, but does not provide enterprise authentication, tenancy, or production support. This repository makes no production-readiness claim.
