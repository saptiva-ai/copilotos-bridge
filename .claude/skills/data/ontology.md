# Ontology & Schema Playbook

## Bank Advisor Ontology

The ontology defines how banking data is structured and queried.

**Location**: `plugins/bank-advisor-private/schemas/`

### Key Concepts

- **Accounts**: Checking, Savings, Credit Cards.
- **Transactions**: Date, Amount, Merchant, Category.
- **Metrics**: Aggregations (Total Spend, Avg Balance).

## Validation Rules

1. **Schema Versioning**: All schema changes MUST bump the version in `metadata`.
2. **Backwards Compatibility**: New fields should be optional unless a data migration is provided.
3. **Type Safety**: Use strict types (Pydantic/SQLAlchemy) for all fields.

## Vector Schema (Weaviate)

Defined in `apps/backend/src/infrastructure/vector_store.py`.

**Updates**:
- If changing embedding model: Requires full re-index.
- If adding properties: Requires schema update in Weaviate.

```python
# Example schema update
client.schema.property.create("BankAdvisor", {
    "name": "category",
    "dataType": ["text"]
})
```
