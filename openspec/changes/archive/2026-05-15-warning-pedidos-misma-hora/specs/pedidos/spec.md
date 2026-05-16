# Delta Spec: Delivery-Hour Collision Detection

**Change**: warning-pedidos-misma-hora  
**Domain**: pedidos  
**Type**: Delta Spec  
**Archived**: 2026-05-15

## New Requirements

### Requirement: Collision Detection Endpoint

**Given** a user is creating or updating an order with a specific delivery datetime  
**When** the system receives a GET request to `/api/v1/pedidos/check-colision`  
**Then** the backend MUST return:
- `hay_colision` (boolean): True if there exists another order in the same hour
- `cantidad` (integer): Number of colliding orders
- `hora_inicio` (ISO 8601 datetime): Start of the collision window (hour boundary)
- `hora_fin` (ISO 8601 datetime): End of the collision window (next hour boundary)

**Query Parameters**:
- `fecha_entrega` (REQUIRED): Delivery datetime in ISO 8601 format
- `exclude_id` (OPTIONAL): Order ID to exclude from collision check (for updates)

**Status Code**: 200 OK or 400 Bad Request (invalid date format)

### Requirement: Collision Detection Algorithm

**Given** a delivery datetime  
**When** the system checks for collisions  
**Then** it MUST group all existing orders by truncated hour and count those matching the hour of the query datetime  

**Note**: Uses PostgreSQL `date_trunc('hour', delivery_time)` for grouping. Assumes server is in UTC or explicitly uses AT TIME ZONE.

### Requirement: Non-Blocking Warning Dialog

**Given** the mobile app detects a collision (hay_colision = true)  
**When** the user attempts to save an order  
**Then** the app MUST show an AlertDialog:
- Title: "Ya tenés un pedido en esa hora"
- Body: "Tenés otro pedido entre {hora_inicio} y {hora_fin}. ¿Deseas continuar?"
- Buttons: "Cancelar" (dismiss) | "Sí, guardar" (proceed)

**Behavior**:
- The warning is non-blocking (user can choose to proceed)
- If user cancels: order creation is aborted
- If user confirms: order is saved as normal
- No special database flags required (save process unchanged)

### Requirement: Integration Test Coverage

**Given** the collision warning feature is implemented  
**When** tests run  
**Then** integration tests MUST cover:
- Collision detection with same-hour delivery
- No collision with different-hour delivery
- User proceeding despite warning

---

## Modified Requirements

None. This delta introduces new functionality without changing existing requirements.

---

## Removed Requirements

None.

---

*Complete implementation verified with 0 CRITICAL issues. See archive-report.md for details.*
