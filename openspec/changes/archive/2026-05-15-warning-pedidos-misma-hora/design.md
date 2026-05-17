# Design: Delivery-Hour Collision Detection

**Change**: warning-pedidos-misma-hora  
**Status**: ARCHIVED  
**Archived**: 2026-05-15

## Architecture Overview

The collision detection feature is a query-only addition to the existing pedido service. No data model changes.

```
Mobile App (Flutter)
    │
    ├─ _checkColision()
    │   └─ GET /api/v1/pedidos/check-colision?fecha_entrega=...&exclude_id=...
    │
    └─ _showColisionDialog() (non-blocking alert)
         │
         ├─ User selects "Cancelar" → abort order creation
         └─ User selects "Sí, guardar" → proceed with normal save flow


Backend (FastAPI)
    │
    └─ GET /api/v1/pedidos/check-colision
         │
         └─ pedido_service.check_colision_hora()
              │
              └─ PostgreSQL: SELECT date_trunc('hour', delivery_time), COUNT(*)
                  FROM pedidos WHERE delivery_time IS NOT NULL
                  AND date_trunc('hour', delivery_time) = requested_hour
                  AND pedido_id != exclude_id
```

## Backend Implementation

### Service Layer (`pedido_service.py`)

**Method**: `check_colision_hora(fecha_entrega: datetime, exclude_id: Optional[str] = None) -> dict`

**Logic**:
1. Accept delivery datetime and optional exclude_id
2. Query PostgreSQL for orders in the same truncated hour
3. Return collision status, count, and window boundaries

**Query**:
```sql
SELECT 
  COUNT(*) as cantidad,
  date_trunc('hour', delivery_time) as hora_inicio,
  date_trunc('hour', delivery_time) + INTERVAL '1 hour' as hora_fin
FROM pedidos
WHERE date_trunc('hour', delivery_time) = date_trunc('hour', %s)
  AND (exclude_id IS NULL OR pedido_id != exclude_id)
GROUP BY date_trunc('hour', delivery_time);
```

**Return Type**: `ColisionHoraResponse`
```python
class ColisionHoraResponse(BaseModel):
    hay_colision: bool
    cantidad: int
    hora_inicio: datetime
    hora_fin: datetime
```

### API Endpoint (`pedidos.py`)

**Route**: `GET /api/v1/pedidos/check-colision`

**Query Parameters**:
- `fecha_entrega` (str, required): ISO 8601 datetime
- `exclude_id` (str, optional): Order ID to exclude

**Handler**:
1. Parse and validate fecha_entrega (reject if invalid format)
2. Call `pedido_service.check_colision_hora(fecha_entrega, exclude_id)`
3. Return `ColisionHoraResponse` JSON

**Error Handling**:
- 400 Bad Request if fecha_entrega format is invalid
- 400 Bad Request if exclude_id is provided but not found (optional — can silently ignore)

## Mobile Implementation

### Screen: `nuevo_pedido_screen.dart`

**Flow**:
1. User enters delivery date and time
2. User taps "Guardar" button
3. `_guardarPedido()` is called
4. **Before DB save**, call `_checkColision()`

**Method**: `_checkColision()`
```dart
Future<void> _checkColision() async {
  try {
    // GET /api/v1/pedidos/check-colision?fecha_entrega=...&exclude_id=...
    final response = await ApiClient.get(
      '/api/v1/pedidos/check-colision',
      queryParams: {
        'fecha_entrega': deliveryDateTime.toIso8601String(),
        if (widget.pedidoId != null) 'exclude_id': widget.pedidoId,
      },
    );
    
    final colision = ColisionHoraResponse.fromJson(response);
    
    if (colision.hayColision) {
      _showColisionDialog(colision);
      return; // abort current flow
    }
    
    // No collision, proceed to save
    _guardarPedido();
  } catch (e) {
    // Log error, show generic error message
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(text: 'Error checking delivery time'),
    );
  }
}
```

**Dialog**: `_showColisionDialog(ColisionHoraResponse colision)`
```dart
showDialog(
  context: context,
  builder: (context) => AlertDialog(
    title: Text('Ya tenés un pedido en esa hora'),
    content: Text('Tenés otro pedido entre ${colision.horaInicio.hour}:00 '
                  'y ${colision.horaFin.hour}:00. ¿Deseas continuar?'),
    actions: [
      TextButton(
        child: Text('Cancelar'),
        onPressed: () => Navigator.pop(context), // dismiss
      ),
      TextButton(
        child: Text('Sí, guardar'),
        onPressed: () {
          Navigator.pop(context);
          _guardarPedido(); // proceed with normal save
        },
      ),
    ],
  ),
);
```

## Database

**No schema changes required.** The feature uses existing `pedidos` table and `delivery_time` column.

**Indexes** (assumed to exist for performance):
- `pedidos.delivery_time` — for efficient date_trunc grouping

## Error Handling & Edge Cases

| Scenario | Handling |
|----------|----------|
| Invalid delivery datetime | API returns 400 Bad Request |
| Network error during check | Show generic error; user can retry or skip warning |
| Zero collisions | hay_colision = false; proceed normally |
| Multiple collisions | cantidad > 1; show first collision window |
| User updates existing order | Pass exclude_id to skip self in collision check |

## Performance Considerations

- **Query Complexity**: O(n) where n = orders in the delivery hour. Expected: <100 per hour (reasonable)
- **No N+1**: Single grouped query via date_trunc
- **Timezone Risk**: `date_trunc` uses server timezone. Safe in UTC Docker, risky in non-UTC production. Recommendation: Add `AT TIME ZONE 'UTC'` explicitly for production

## Non-Blocking Design Rationale

The warning is non-blocking because:
1. Delivery overlaps (same hour) do not prevent order fulfillment
2. Logistical complexity is manageable (delivery team sorts by customer)
3. Users should have autonomy to accept the warning and proceed
4. Blocking would prevent legitimate orders during peak hours

---

*Complete design verified. See archive-report.md for verification results.*
