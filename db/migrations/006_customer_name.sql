-- Display-name correction only: preserve IDs, OIDC mappings, sessions and ledger history.
UPDATE principals SET name='Subhanjan Das'
WHERE id IN ('harbour:alex','other:alex') AND name='Alex Morgan';
