# Retest of Compute Engine

> Size 32

We are trying to diagnose why there are differences in Compute Engine vs. GKE. So far we have identified two variables:

- MTU: on GKE was set to 8896 (and used the underlying default 1460 for Compute Engine)
- Tier 1 "PREMIUM" was set for GKE but not for Compute Engine
- COMPACT we were never able to get for compute engine, at least greater than 10 instances. I can try again but not sure it will be different.
