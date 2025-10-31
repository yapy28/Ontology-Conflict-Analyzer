# Ontology Conflict Detector

A Python tool for analyzing conflicts across multiple ontology files before merging them. This script helps identify critical conflicts that would break ontology merging and semantic issues that need attention.

## Features

The conflict detector analyzes ontologies across three priority levels:

### 🔴 **Priority 1: Critical Conflicts** (Must Fix Before Merging)

- **URI Collisions**: Same URIs with different definitions across files
- **Property Type Conflicts**: Properties defined as both ObjectProperty and DatatypeProperty

### 🟡 **Priority 2: Semantic Conflicts** (Should Review)

- **Semantic Duplicates**: Different URIs representing the same concepts
- **Inverse Property Candidates**: Properties that might be inverses of each other
- **Equivalent Class Candidates**: Classes that might be equivalent but not declared as such

### 🟢 **Priority 3: Quality Issues** (Nice to Fix)

- **Unlabeled Classes**: Classes without rdfs:label
- **Underspecified Properties**: Properties without domain or range

## Requirements

```bash
pip install rdflib
```

## Usage

### Basic Usage

Analyze a single ontology file:

```bash
python "onto_conflict_detect.py" path/to/ontology.ttl
```

Analyze multiple ontology files:

```bash
python "onto_conflict_detect.py" file1.ttl file2.ttl file3.ttl
```

### Advanced Options

```bash
python "onto_conflict_detect.py" [files] [options]

Options:
  -o, --output-dir DIR    Output directory for log files (default: logs)
  -l, --log-name NAME     Custom log file name (default: auto-generated)
  -a, --agnostic          Enable namespace-agnostic mode (compare by local names)
  -h, --help             Show help message
```

#### Namespace-Agnostic Mode

The `--agnostic` (or `-a`) flag enables namespace-agnostic comparison mode. In this mode, the detector groups ontology elements by their **local names** (the part after `#` or the last `/` in the URI) rather than comparing full URIs.

**When to use:**
- Comparing ontologies from different organizations with different namespaces
- Finding potential semantic duplicates across namespace boundaries
- Harmonizing terminology before formally merging ontologies
- Detecting unintentional naming conflicts in distributed development

**Example:**
```bash
# Compare by local names across namespaces
python "onto_conflict_detect.py" file1.ttl file2.ttl --agnostic

# Normal mode: compare exact URIs (default)
python "onto_conflict_detect.py" file1.ttl file2.ttl
```

In agnostic mode, URIs like `http://example.org#Vehicle` and `http://different.org#Vehicle` will be grouped together and compared, even though they have different namespaces. The output will show:
- **NAMESPACE-AGNOSTIC URI GROUPS**: URIs with the same local name
- **MERGE-BREAKING conflicts**: Structural incompatibilities (types, domains, ranges)
- **SEMANTIC CANDIDATES**: Label or comment differences

See `examples/agnostic_example.md` for a detailed walkthrough.

### Examples

```bash
# Analyze multiple ontologies with custom output directory
python "onto_conflict_detect.py" *.ttl -o analysis_results

# Analyze with custom log name
python "onto_conflict_detect.py" ontology1.ttl ontology2.ttl -l custom_conflicts.log

# Analyze all TTL files in current directory
python "onto_conflict_detect.py" *.ttl
```

## Supported File Formats

- Turtle (.ttl)
- OWL (.owl)
- RDF/XML (.rdf)
- N3 (.n3)

## Output

The script creates a detailed log file with:

- Console output (real-time analysis)
- Complete log file with timestamps
- Structured conflict reports by priority
- Summary statistics

### Log File Location

By default, log files are saved to the `logs/` directory with timestamps:

- Single file: `conflict_analysis_[filename]_[timestamp].log`
- Multiple files: `conflict_analysis_multi_[timestamp].log`

## Understanding the Results

### Critical Conflicts (🔴 Priority 1)

These **MUST** be resolved before merging:

```
⚠️  URI TYPE CONFLICT: http://data.europa.eu/949/name
   Different types across files: Class, DatatypeProperty
   - file1.ttl: Class
   - file2.ttl: DatatypeProperty
```

**Action Required**: Decide whether this should be a Class or DatatypeProperty and update accordingly.

### Semantic Conflicts (🟡 Priority 2)

These **SHOULD** be reviewed for data quality:

```
🔍 Potential semantic duplicates for 'station':
   - http://data.europa.eu/949/Station (from: file1.ttl)
   - http://data.europa.eu/949/TrainStation (from: file2.ttl)
```

**Action Suggested**: Consider using owl:equivalentClass or owl:sameAs to link these concepts.

### Quality Issues (🟢 Priority 3)

These are **NICE TO FIX** for better ontology quality:

```
Found 25 classes without labels:
   - http://data.europa.eu/949/SomeClass (from: file1.ttl)
```

**Action Suggested**: Add rdfs:label properties for better usability.

## Performance Tips

### Large Files

- Files >100MB will show a warning and may take longer to process
- Consider splitting very large ontologies if possible
- The script loads all files into memory simultaneously

### Memory Usage

- Each ontology is loaded completely into memory
- For multiple large files, ensure sufficient RAM is available
- Monitor memory usage with large datasets

## Troubleshooting

### Common Issues

**"File not found" errors:**

```bash
Warning: File not found: nonexistent.ttl
```

- Check file paths are correct
- Ensure files exist and are readable

**"Error parsing" messages:**

```bash
Error parsing file.ttl: Invalid syntax at line 123
```

- Verify the ontology file syntax is valid
- Try opening the file in an RDF editor to check for errors

**Large number of inverse property candidates:**

- This might indicate overly broad pattern matching
- Focus on the first 25 results shown in the output
- Many false positives are normal and can be ignored

### Memory Issues

If you encounter memory errors with large files:

1. Process files individually instead of all at once
2. Increase available system memory
3. Consider using smaller subsets for initial analysis

## Integration with Ontology Development

### Pre-Merge Checklist

1. ✅ Run conflict detector on all files to be merged
2. ✅ Resolve all Priority 1 (Critical) conflicts
3. ✅ Review Priority 2 (Semantic) conflicts
4. ✅ Consider fixing Priority 3 (Quality) issues
5. ✅ Re-run analysis to confirm fixes

### Continuous Integration
Consider running this script as part of your ontology development pipeline to catch conflicts early.

## Contributing
To extend the conflict detector:
- Add new conflict detection methods to the `OntologyConflictDetector` class
- Follow the priority system (1=Critical, 2=Semantic, 3=Quality)
- Include source file information in all conflict reports
- Add appropriate emoji indicators for visual clarity

## Testing

### Running Tests

To verify the agnostic mode functionality:

```bash
cd tests
python test_agnostic_mode.py
```

This smoke test verifies that:
- The `--agnostic` flag is properly recognized
- Agnostic mode banner appears in output
- Namespace-agnostic grouping occurs correctly
- Default mode continues to work without the flag

### Test Files

The `tests/` directory contains example ontology files:
- `example1.ttl`: Sample ontology with namespace `http://example.org/ontology1#`
- `example2.ttl`: Sample ontology with namespace `http://different.org/vocab#`

Both files define similar concepts (`Vehicle`, `Car`, `hasOwner`) with the same local names but different namespaces and labels, making them ideal for demonstrating agnostic mode.

## Version History

- v3: Added namespace-agnostic comparison mode with `--agnostic` flag
- v2: Added priority-based conflict categorization, improved inverse property detection, enhanced logging
- v1: Initial version with basic conflict detection
