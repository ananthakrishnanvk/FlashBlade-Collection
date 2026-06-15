# S3 Export Modules — Capabilities

Two modules cooperate to expose object-store account buckets over S3:

- `purefb_s3_export_policy` — defines the reusable **policy** (rules + enabled flag).
- `purefb_s3acc_export` — **binds** an account to a server using one of those policies.

Both require FlashBlade REST API `2.20`+ and the `py-pure-client` SDK.

---

## `purefb_s3_export_policy` — manage the policy object

A reusable rule-set that controls which buckets in an object-store account are visible over S3 through an account export.

**Identity:** policy `name` (cluster-wide).

### Operations

| Op | How |
|---|---|
| Create | `state: present` + new `name` |
| Update enabled flag | `enabled: true/false` |
| Rename | `rename: <new-name>` (errors if policy missing) |
| Delete | `state: absent` |
| Manage inline rules | `rules: [...]` |

### Rule shape

`rules` is an ordered list of dicts:

- `name` — idempotency key
- `actions` — only `pure:S3Access` supported today
- `effect` — `allow` or `deny`
- `resources` — bucket names, glob OK (`my-bucket*`, `*`)

### Rule reconciliation behavior on update

- Missing rules → POST
- Divergent rules (matched by name) → PATCH
- Extra rules not in your list → DELETE
- Omit `rules` entirely to leave existing rules untouched
- Comparison is order-insensitive on `actions` / `resources`

### Example

```yaml
- name: Create an S3 export policy with two rules
  purestorage.flashblade.purefb_s3_export_policy:
    name: my_export_policy
    enabled: true
    rules:
      - name: allow_all_buckets
        actions: ["pure:S3Access"]
        effect: allow
        resources: ["*"]
      - name: deny_finance
        actions: ["pure:S3Access"]
        effect: deny
        resources: ["finance-*"]
    fb_url: 10.10.10.2
    api_token: T-...
```

---

## `purefb_s3acc_export` — manage the account → server binding

Materializes an account's S3 surface on a specific server via an export policy.

**Identity:** `(account, server)` pair — looked up via `member.name='X' and server.name='Y'`.

### Operations

| Op | How |
|---|---|
| Create | `state: present` + `account` + `server` + `policy` (required on create) |
| Enable / disable | `enabled: true/false` |
| Re-point to a different policy | `policy: <new-policy>` |
| Delete | `state: absent` |

**Not supported:** changing `account` or `server` after creation — they form the identity, so delete and recreate instead.

### Example

```yaml
- name: Export account acme on server fb-01 using policy acme-export
  purestorage.flashblade.purefb_s3acc_export:
    account: acme
    server: fb-01
    policy: acme-export
    fb_url: 10.10.10.2
    api_token: T-...

- name: Re-point an existing account export at a different policy
  purestorage.flashblade.purefb_s3acc_export:
    account: acme
    server: fb-01
    policy: acme-export-v2
    fb_url: 10.10.10.2
    api_token: T-...
```

---

## Cross-cutting features (both modules)

- **Check mode:** yes (`supports_check_mode=True`)
- **Idempotency:** update paths only PATCH fields that actually differ
- **Fleet context:** `context: <member-name>` to target a fleet member
- **Min API:** FlashBlade REST `2.20`
- **SDK:** `py-pure-client` required

---

## How they fit together

```
[purefb_s3_export_policy]                 [purefb_s3acc_export]
       defines                                   binds
   ┌──────────────┐                       ┌─────────────────┐
   │  policy P    │ ◄──── policy: P ──────┤ account A       │
   │  rules [...] │                       │ server  S       │
   │  enabled     │                       │ enabled         │
   └──────────────┘                       └─────────────────┘
```

Typical playbook order: create the policy first, then create the account export pointing at it.
