CREATE UNIQUE INDEX IF NOT EXISTS idx_places_dataset_key
    ON places ((external_refs->>'dataset'), (external_refs->>'dataset_key'))
    WHERE external_refs ? 'dataset' AND external_refs ? 'dataset_key';
