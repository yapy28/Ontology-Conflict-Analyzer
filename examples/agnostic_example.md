# Namespace-Agnostic Mode Example

This example demonstrates how to use the namespace-agnostic comparison mode (`--agnostic` or `-a` flag) in the Ontology Conflict Detector.

## What is Namespace-Agnostic Mode?

In normal mode, the conflict detector compares ontology elements by their **full URIs**. This means that `http://example.org/ontology1#Vehicle` and `http://different.org/vocab#Vehicle` are treated as completely different entities.

With namespace-agnostic mode enabled, the detector groups elements by their **local names** (the part after `#` or the last `/`). This allows you to find potential conflicts or duplicates across different namespaces that might represent the same concept.

## Example Scenario

Consider two ontology files from different sources:

### File 1: example1.ttl
```turtle
@prefix : <http://example.org/ontology1#> .

:Vehicle a owl:Class ;
    rdfs:label "Vehicle" ;
    rdfs:comment "A means of transportation" .

:Car a owl:Class ;
    rdfs:label "Car" .

:hasOwner a owl:ObjectProperty ;
    rdfs:label "has owner" ;
    rdfs:domain :Vehicle .
```

### File 2: example2.ttl
```turtle
@prefix : <http://different.org/vocab#> .

:Vehicle a owl:Class ;
    rdfs:label "Automobile" ;
    rdfs:comment "A motorized transport device" .

:Car a owl:Class ;
    rdfs:label "Passenger Car" .

:hasOwner a owl:ObjectProperty ;
    rdfs:label "owned by" ;
    rdfs:domain :Car .
```

## Running the Analysis

### Default Mode (exact URI matching)
```bash
python onto_conflict_detect.py example1.ttl example2.ttl
```

In default mode, these are treated as completely separate entities since they have different namespaces.

### Namespace-Agnostic Mode
```bash
python onto_conflict_detect.py example1.ttl example2.ttl --agnostic
# or use short form:
python onto_conflict_detect.py example1.ttl example2.ttl -a
```

With `--agnostic` enabled, the detector will:

1. **Group by local name**: All URIs ending in "Vehicle", "Car", or "hasOwner" will be grouped together regardless of namespace
2. **Detect conflicts**: Show where the same local name has different definitions across namespaces
3. **Classify issues**:
   - **MERGE-BREAKING**: Structural conflicts (different types, domains, ranges)
   - **SEMANTIC CANDIDATES**: Label or comment differences

## Expected Output

When running in agnostic mode, you'll see:

```
================================================================================
🔍 RUNNING IN NAMESPACE-AGNOSTIC MODE
================================================================================
URIs with the same local name but different namespaces will be
grouped together for comparison and conflict detection.
================================================================================

...

🌐 NAMESPACE-AGNOSTIC URI GROUP: 'vehicle'
   Local name appears in 2 different URIs:
   - http://example.org/ontology1#Vehicle
     Files: example1.ttl
   - http://different.org/vocab#Vehicle
     Files: example2.ttl

   ℹ️  SEMANTIC CANDIDATE: Label differences
      Different labels: Vehicle, Automobile
      - http://example.org/ontology1#Vehicle: Vehicle (in example1.ttl)
      - http://different.org/vocab#Vehicle: Automobile (in example2.ttl)

🌐 NAMESPACE-AGNOSTIC URI GROUP: 'hasowner'
   Local name appears in 2 different URIs:
   - http://example.org/ontology1#hasOwner
     Files: example1.ttl
   - http://different.org/vocab#hasOwner
     Files: example2.ttl

   ⚠️  MERGE-BREAKING: Domain conflict across namespaces
      Different domains: http://example.org/ontology1#Vehicle, http://different.org/vocab#Car
```

## Use Cases

Namespace-agnostic mode is useful when:

1. **Merging ontologies from different organizations** that may use different namespaces but similar concepts
2. **Finding semantic duplicates** across namespace boundaries
3. **Harmonizing terminology** before a formal merge
4. **Detecting unintentional naming conflicts** in distributed ontology development

## Tips

- Use agnostic mode as a **discovery tool** to find potential issues
- Always review **MERGE-BREAKING** conflicts carefully as these indicate structural incompatibilities
- **SEMANTIC CANDIDATES** can often be resolved with `owl:equivalentClass` or `owl:sameAs` mappings
- The default mode (exact URI matching) remains the primary check for actual merge conflicts
- Both modes can be run sequentially to get a complete picture

## Testing

To verify the agnostic mode works correctly, run the smoke test:

```bash
cd tests
python test_agnostic_mode.py
```

This will verify that:
- The `--agnostic` flag is recognized
- The mode banner appears in the output
- Namespace-agnostic grouping occurs
- Default mode still works without the flag
