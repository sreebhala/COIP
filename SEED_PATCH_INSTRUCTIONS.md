# seed.py — 3 edits needed

Neither the `missing_configuration` nor `resource-not-required` routing
condition is exercised by any of the existing REQ-001..REQ-005 fixtures
(confirmed by reading `seed.py`: all 3 existing appointment types have a
`required_room_type` set, and no existing request uses a doctor with zero
availability rows). These are real, already-implemented code paths — the
seed data just never demonstrated them end-to-end. These 3 edits add
minimal fixtures to exercise them, without changing any existing rule,
agent, or route logic.

## Edit 1 — add a new appointment type with no room requirement

In the `DATA` JSON string's `"appointment_types"` array, add one entry:

```json
{"type_code": "APT-TELE", "name": "Teleconsultation", "default_duration_minutes": 15, "required_room_type": null, "operational_buffer_minutes": 5, "active": true}
```

## Edit 2 — add two more patients

In the `patients` loop's list, add:

```python
("PAT-006", "Vikram Demo", "vikram@example.test", "0000003006"),
("PAT-007", "Sana Demo", "sana@example.test", "0000003007"),
```

## Edit 3 — add two more requests

In the `requests` list, add:

```python
# REQ-006: requested doctor (DOC-003) has zero seeded DoctorAvailability
# rows -> ContextBuilder sets routing_status="missing_configuration".
# Exercises the missing-configuration route end to end.
("REQ-006", "PAT-006", "LOC-001", "DOC-003", "APT-NEW", DAY1, "09:00", 0, "phone", "pending", False),

# REQ-007: appointment type APT-TELE has required_room_type=None ->
# ResourceAllocationAgent deterministically returns "Not Required".
# Exercises the resource-not-required route end to end. DOC-001 has
# seeded availability 09:00-13:00 on DAY1, so the rest of the context
# builds normally (this request is only special with respect to the
# resource route, not any other agent).
("REQ-007", "PAT-007", "LOC-001", "DOC-001", "APT-TELE", DAY1, "09:30", 0, "phone", "pending", False),
```

## After editing

Re-seed (safe — `seed()` only inserts rows that don't already exist):

```powershell
cd backend
python -m app.data.seed
```

Then REQ-006 and REQ-007 will appear in `GET /api/v1/appointment-requests`
and the Agent Workflow Console alongside REQ-001..REQ-005.
