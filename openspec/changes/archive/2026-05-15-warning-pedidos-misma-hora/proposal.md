# Proposal: Same-Hour Collision Warning

**Change**: warning-pedidos-misma-hora  
**Status**: ARCHIVED  
**Archived**: 2026-05-15

## Problem Statement

Users can currently create multiple orders with delivery times in the same hour. This can lead to logistical confusion for the delivery team. A warning system should alert users to potential delivery conflicts without blocking order creation.

## Proposed Solution

Implement a non-blocking collision warning that:
1. Detects when a user attempts to create an order with a delivery time that overlaps (same hour) with existing orders
2. Shows a dialog warning the user
3. Allows the user to proceed despite the warning

## Scope

- Backend: Add collision detection endpoint
- Frontend: Show warning dialog before save
- Testing: Integration test for collision detection

## Rollback Plan

Remove the `/api/v1/pedidos/check-colision` endpoint and the `_checkColision()` call from the mobile app. Database requires no changes.

Time to rollback: 15 minutes.

---

*See archive-report.md for complete implementation details.*
