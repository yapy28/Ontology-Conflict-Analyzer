import sys
import os
import argparse
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS
from collections import defaultdict
from pathlib import Path
from rdflib.exceptions import ParserError
from datetime import datetime

class Logger:
    """Custom logger to write to both console and file"""
    def __init__(self, log_file):
        self.terminal = sys.stdout
        self.log = open(log_file, 'w', encoding='utf-8')
        
        # Write header to log file
        self.log.write(f"CONFLICT ANALYSIS LOG - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        self.log.write("=" * 80 + "\n")
        self.log.flush()
    
    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush()
    
    def flush(self):
        self.terminal.flush()
        self.log.flush()
    
    def close(self):
        self.log.close()

class OntologyConflictDetector:
    def __init__(self, ontology_files, log_file=None):
        """Initialize with multiple ontology files for pre-merge analysis"""
        if isinstance(ontology_files, str):
            self.ontology_files = [ontology_files]
        else:
            self.ontology_files = ontology_files
            
        if log_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.log_file = f"conflict_analysis_{timestamp}.log"
        else:
            self.log_file = log_file
        
        # Initialize logger
        self.logger = None
        
        # Load all ontologies
        self.graphs = {}
        self.combined_graph = Graph()
        
        for file_path in self.ontology_files:
            try:
                print(f"Loading ontology: {file_path}")
                g = Graph()
                file_size = Path(file_path).stat().st_size / (1024*1024)
                if file_size > 100:
                    print(f"Large file detected ({file_size:.1f}MB). This may take a while...")
                
                g.parse(file_path, format='turtle')
                self.graphs[file_path] = g
                
                # Add to combined graph for cross-ontology analysis
                for triple in g:
                    self.combined_graph.add(triple)
                    
                print(f"✓ Loaded {len(g)} triples from {Path(file_path).name}")
                
            except FileNotFoundError:
                print(f"Error: File not found: {file_path}")
                continue
            except ParserError as e:
                print(f"Error parsing {file_path}: {e}")
                continue
            except Exception as e:
                print(f"Unexpected error loading {file_path}: {e}")
                continue

        self.era = Namespace("http://www.data.europa.eu/949/")
        
        # Bind common namespaces
        self.combined_graph.bind("era", self.era)
        self.combined_graph.bind("owl", OWL)
        self.combined_graph.bind("rdf", RDF)
        self.combined_graph.bind("rdfs", RDFS)
        self.combined_graph.bind("skos", SKOS)

    def setup_logging(self):
        """Set up logging to both console and file"""
        self.logger = Logger(self.log_file)
        sys.stdout = self.logger
        
        print(f"Ontology Files: {', '.join([Path(f).name for f in self.ontology_files])}")
        print(f"Log File: {self.log_file}")
        print(f"Analysis Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

    def cleanup_logging(self):
        """Restore stdout and close log file"""
        if self.logger:
            sys.stdout = self.logger.terminal
            self.logger.close()

    # PRIORITY 1: MERGER-BREAKING CONFLICTS
    
    def detect_uri_collisions(self):
        """Detect same URIs with different definitions across ontology files"""
        print("\n🔴 PRIORITY 1: URI COLLISION DETECTION")
        print("=" * 50)
        
        uri_definitions = defaultdict(list)
        
        # Collect all URI definitions from each ontology
        for file_path, graph in self.graphs.items():
            file_name = Path(file_path).name
            
            # Check classes
            for uri in graph.subjects(RDF.type, OWL.Class):
                labels = list(graph.objects(uri, RDFS.label))
                comments = list(graph.objects(uri, RDFS.comment))
                equivalent_classes = list(graph.objects(uri, OWL.equivalentClass))
                
                uri_definitions[str(uri)].append({
                    'file': file_name,
                    'type': 'Class',
                    'labels': [str(l) for l in labels],
                    'comments': [str(c) for c in comments],
                    'equivalent_classes': [str(e) for e in equivalent_classes]
                })
            
            # Check properties
            for prop_type in [OWL.ObjectProperty, OWL.DatatypeProperty, OWL.FunctionalProperty]:
                for uri in graph.subjects(RDF.type, prop_type):
                    labels = list(graph.objects(uri, RDFS.label))
                    domains = list(graph.objects(uri, RDFS.domain))
                    ranges = list(graph.objects(uri, RDFS.range))
                    
                    uri_definitions[str(uri)].append({
                        'file': file_name,
                        'type': str(prop_type).split('#')[1],
                        'labels': [str(l) for l in labels],
                        'domains': [str(d) for d in domains],
                        'ranges': [str(r) for r in ranges]
                    })
        
        # Find conflicts
        conflicts_found = 0
        for uri, definitions in uri_definitions.items():
            if len(definitions) > 1:
                # Check for conflicting definitions
                labels = set()
                types = set()
                ranges = set()
                domains = set()
                
                for defn in definitions:
                    labels.update(defn.get('labels', []))
                    types.add(defn.get('type', ''))
                    ranges.update(defn.get('ranges', []))
                    domains.update(defn.get('domains', []))
                
                has_conflict = False
                
                # Type conflicts - modified to ignore valid OWL combinations
                if len(types) > 1 and '' not in types:
                    # Check if this is just a valid OWL property combination
                    valid_combo = False
                    
                    # FunctionalProperty can be combined with either ObjectProperty or DatatypeProperty
                    if types == {'FunctionalProperty', 'ObjectProperty'} or types == {'FunctionalProperty', 'DatatypeProperty'}:
                        valid_combo = True
                    
                    # Only flag if it's not a valid combination
                    if not valid_combo:
                        print(f"\n⚠️  URI TYPE CONFLICT: {uri}")
                        print(f"   Different types across files: {', '.join(types)}")
                        for defn in definitions:
                            print(f"   - {defn['file']}: {defn['type']}")
                        has_conflict = True
                
                # Range conflicts for properties
                if len(ranges) > 1 and '' not in ranges:
                    print(f"\n⚠️  PROPERTY RANGE CONFLICT: {uri}")
                    print(f"   Different ranges: {', '.join(ranges)}")
                    for defn in definitions:
                        if defn.get('ranges'):
                            print(f"   - {defn['file']}: {', '.join(defn['ranges'])}")
                    has_conflict = True
                
                # Label conflicts (significant differences)
                if len(labels) > 1:
                    # Check if labels are significantly different (not just case/whitespace)
                    normalized_labels = {l.lower().strip() for l in labels if l}
                    if len(normalized_labels) > 1:
                        print(f"\n⚠️  LABEL CONFLICT: {uri}")
                        print(f"   Different labels: {', '.join(labels)}")
                        for defn in definitions:
                            if defn.get('labels'):
                                print(f"   - {defn['file']}: {', '.join(defn['labels'])}")
                        has_conflict = True
                
                if has_conflict:
                    conflicts_found += 1
        
        print(f"\n📊 URI COLLISION SUMMARY: {conflicts_found} conflicts found")
        print("   These conflicts will break ontology merging!")
        
        return conflicts_found

    def detect_property_type_conflicts(self):
        """Detect properties with conflicting types (ObjectProperty vs DatatypeProperty)"""
        print("\n🔴 PRIORITY 1: PROPERTY TYPE CONFLICTS")
        print("=" * 50)
        
        property_types = defaultdict(set)
        
        # Collect property types from all ontologies
        for file_path, graph in self.graphs.items():
            file_name = Path(file_path).name
            
            for prop_type in [OWL.ObjectProperty, OWL.DatatypeProperty, OWL.FunctionalProperty]:
                for prop in graph.subjects(RDF.type, prop_type):
                    property_types[str(prop)].add((str(prop_type).split('#')[1], file_name))
        
        # Find REAL conflicts (only ObjectProperty vs DatatypeProperty)
        conflicts = []
        for prop, types in property_types.items():
            type_names = {t[0] for t in types}
            
            # Check for the ONLY real conflict: ObjectProperty vs DatatypeProperty
            has_object = 'ObjectProperty' in type_names
            has_datatype = 'DatatypeProperty' in type_names
            
            if has_object and has_datatype:
                conflicts.append((prop, types))
        
        if conflicts:
            print(f"Found {len(conflicts)} REAL property type conflicts:")
            for prop, types in conflicts[:10]:  # Show first 10
                print(f"\n⚠️  {prop}")
                for type_name, file_name in types:
                    print(f"   - {type_name} in {file_name}")
            print("\n   Note: These are genuine conflicts - a property cannot be both")
            print("         ObjectProperty and DatatypeProperty simultaneously.")
        else:
            print("✅ No property type conflicts found")
            print("   (FunctionalProperty can coexist with ObjectProperty or DatatypeProperty)")
        
        return len(conflicts)

    # PRIORITY 2: SEMANTIC CONFLICTS
    
    def detect_semantic_duplicates(self):
        """Detect different URIs that likely represent the same concepts"""
        print("\n🟡 PRIORITY 2: SEMANTIC DUPLICATE DETECTION")
        print("=" * 50)
        
        # Group classes by their labels (case-insensitive)
        label_groups = defaultdict(list)
        
        for uri in self.combined_graph.subjects(RDF.type, OWL.Class):
            labels = list(self.combined_graph.objects(uri, RDFS.label))
            for label in labels:
                normalized_label = str(label).lower().strip()
                if normalized_label:
                    label_groups[normalized_label].append(str(uri))
        
        # Find potential duplicates
        duplicates_found = 0
        for label, uris in label_groups.items():
            if len(uris) > 1:
                print(f"\n🔍 Potential semantic duplicates for '{label}':")
                for uri in uris:
                    # Find which file this URI comes from
                    source_files = []
                    for file_path, graph in self.graphs.items():
                        if (URIRef(uri), RDF.type, OWL.Class) in graph:
                            source_files.append(Path(file_path).name)
                    print(f"   - {uri} (from: {', '.join(source_files)})")
                duplicates_found += 1
        
        print(f"\n📊 SEMANTIC DUPLICATES SUMMARY: {duplicates_found} potential duplicate groups found")
        return duplicates_found

    def detect_equivalent_class_candidates(self):
        """Detect classes that might be equivalent but not declared as such"""
        print("\n🟡 PRIORITY 2: EQUIVALENT CLASS CANDIDATES")
        print("=" * 50)
        
        # Look for classes with similar names but different URIs
        class_info = {}
        
        for uri in self.combined_graph.subjects(RDF.type, OWL.Class):
            labels = [str(l) for l in self.combined_graph.objects(uri, RDFS.label)]
            comments = [str(c) for c in self.combined_graph.objects(uri, RDFS.comment)]
            
            # Extract class name from URI
            class_name = str(uri).split('/')[-1].split('#')[-1]
            
            class_info[str(uri)] = {
                'name': class_name,
                'labels': labels,
                'comments': comments
            }
        
        # Group by similar names/labels
        similar_groups = defaultdict(list)
        
        for uri, info in class_info.items():
            # Use first label if available, otherwise use class name
            key = info['labels'][0].lower() if info['labels'] else info['name'].lower()
            similar_groups[key].append((uri, info))
        
        # Find groups with multiple classes
        candidates_found = 0
        for key, classes in similar_groups.items():
            if len(classes) > 1:
                print(f"\n🎯 Similar classes for '{key}':")
                for uri, info in classes:
                    source_files = []
                    for file_path, graph in self.graphs.items():
                        if (URIRef(uri), RDF.type, OWL.Class) in graph:
                            source_files.append(Path(file_path).name)
                    print(f"   - {uri}")
                    print(f"     Labels: {', '.join(info['labels']) if info['labels'] else 'None'}")
                    print(f"     Sources: {', '.join(source_files)}")
                candidates_found += 1
        
        print(f"\n📊 EQUIVALENT CLASS CANDIDATES: {candidates_found} groups found")
        return candidates_found

    # PRIORITY 3: ADDITIONAL ANALYSES
    
    def detect_class_conflicts(self):
        """Detect general class-related conflicts"""
        print("\n🟢 PRIORITY 3: CLASS-LEVEL CONFLICTS")
        print("=" * 50)
        
        # Check for classes with no labels
        unlabeled_classes = []
        for uri in self.combined_graph.subjects(RDF.type, OWL.Class):
            labels = list(self.combined_graph.objects(uri, RDFS.label))
            if not labels:
                # Find source files
                source_files = []
                for file_path, graph in self.graphs.items():
                    if (uri, RDF.type, OWL.Class) in graph:
                        source_files.append(Path(file_path).name)
                unlabeled_classes.append((str(uri), source_files))
        
        if unlabeled_classes:
            print(f"Found {len(unlabeled_classes)} classes without labels:")
            for uri, sources in unlabeled_classes[:10]:  # Show first 10
                print(f"   - {uri} (from: {', '.join(sources)})")
        else:
            print("✅ All classes have labels")
        
        return len(unlabeled_classes)

    def detect_property_conflicts(self):
        """Detect general property-related conflicts"""
        print("\n🟢 PRIORITY 3: PROPERTY-LEVEL CONFLICTS")
        print("=" * 50)
        
        # Check for properties with no domains or ranges
        underspecified_properties = []
        
        for prop_type in [OWL.ObjectProperty, OWL.DatatypeProperty]:
            for prop in self.combined_graph.subjects(RDF.type, prop_type):
                domains = list(self.combined_graph.objects(prop, RDFS.domain))
                ranges = list(self.combined_graph.objects(prop, RDFS.range))
                
                if not domains and not ranges:
                    # Find source files
                    source_files = []
                    for file_path, graph in self.graphs.items():
                        if (prop, RDF.type, prop_type) in graph:
                            source_files.append(Path(file_path).name)
                    underspecified_properties.append((str(prop), str(prop_type).split('#')[1], source_files))
        
        if underspecified_properties:
            print(f"Found {len(underspecified_properties)} properties without domain/range:")
            for prop, prop_type, sources in underspecified_properties[:10]:  # Show first 10
                print(f"   - {prop} ({prop_type}) (from: {', '.join(sources)})")
        else:
            print("✅ All properties have domain or range specified")
        
        return len(underspecified_properties)

    def detect_inverse_property_candidates(self):
        """Detect properties that might be inverses of each other"""
        print("\n🟡 PRIORITY 2: INVERSE PROPERTY DETECTION")
        print("=" * 50)
        
        # More specific inverse patterns - must be at word boundaries
        inverse_patterns = [
            ('hasParent', 'hasChild'),
            ('parentOf', 'childOf'),
            ('contains', 'containedIn'),
            ('includes', 'includedIn'),
            ('owns', 'ownedBy'),
            ('manages', 'managedBy'),
            ('controls', 'controlledBy'),
            ('above', 'below'),
            ('before', 'after'),
            ('precedes', 'follows'),
            ('greater', 'less'),
            ('input', 'output'),
            ('source', 'target'),
            ('from', 'to'),
        ]
        
        # Get all object properties with their source files
        properties = []
        for prop in self.combined_graph.subjects(RDF.type, OWL.ObjectProperty):
            prop_str = str(prop)
            labels = [str(l) for l in self.combined_graph.objects(prop, RDFS.label)]
            
            # Find source files for this property
            source_files = []
            for file_path, graph in self.graphs.items():
                if (prop, RDF.type, OWL.ObjectProperty) in graph:
                    source_files.append(Path(file_path).name)
            
            properties.append((prop_str, labels, source_files))
        
        # Find potential inverse relationships
        inverse_candidates = []
        
        for prop1, labels1, sources1 in properties:
            for prop2, labels2, sources2 in properties:
                if prop1 != prop2:
                    # Extract property names from URIs
                    prop1_name = prop1.split('/')[-1].split('#')[-1]
                    prop2_name = prop2.split('/')[-1].split('#')[-1]
                    
                    # Check URI-based patterns (more reliable)
                    for pattern1, pattern2 in inverse_patterns:
                        if ((pattern1.lower() in prop1_name.lower() and pattern2.lower() in prop2_name.lower()) or
                            (pattern2.lower() in prop1_name.lower() and pattern1.lower() in prop2_name.lower())):
                            
                            # Use first label if available, otherwise use property name
                            label1 = labels1[0] if labels1 else prop1_name
                            label2 = labels2[0] if labels2 else prop2_name
                            
                            inverse_candidates.append((prop1, prop2, label1, label2, sources1, sources2))
                            break
                    
                    # Also check for exact label-based patterns (case-insensitive)
                    if labels1 and labels2:
                        for label1 in labels1:
                            for label2 in labels2:
                                label1_clean = label1.lower().strip()
                                label2_clean = label2.lower().strip()
                                
                                for pattern1, pattern2 in inverse_patterns:
                                    if ((pattern1.lower() == label1_clean and pattern2.lower() == label2_clean) or
                                        (pattern2.lower() == label1_clean and pattern1.lower() == label2_clean)):
                                        inverse_candidates.append((prop1, prop2, label1, label2, sources1, sources2))
                                        break
        
        # Remove duplicates
        unique_candidates = []
        seen = set()
        for p1, p2, l1, l2, s1, s2 in inverse_candidates:
            pair = tuple(sorted([p1, p2]))
            if pair not in seen:
                seen.add(pair)
                unique_candidates.append((p1, p2, l1, l2, s1, s2))
        
        if unique_candidates:
            print(f"Found {len(unique_candidates)} potential inverse property pairs:")
            # Show more results since we're being more selective
            for p1, p2, l1, l2, s1, s2 in unique_candidates[:25]:  # Show first 25
                print(f"\n🔗 {p1} ({l1})")
                print(f"   Sources: {', '.join(s1)}")
                print(f"   ↔️  {p2} ({l2})")
                print(f"   Sources: {', '.join(s2)}")
            
            if len(unique_candidates) > 25:
                print(f"\n... and {len(unique_candidates) - 25} more pairs")
        else:
            print("✓ No obvious inverse property candidates found")
        
        return len(unique_candidates)

    # ...existing code...
    
    def run_full_analysis(self):
        """Run comprehensive conflict analysis with priorities"""
        self.setup_logging()
        
        try:
            print("\nCOMPREHENSIVE ONTOLOGY CONFLICT ANALYSIS")
            print("=" * 60)
            print(f"Analyzing: {', '.join([Path(f).name for f in self.ontology_files])}")
            
            # PRIORITY 1: Merger-breaking conflicts
            print("\n" + "🔴" * 20 + " PRIORITY 1 CONFLICTS " + "🔴" * 20)
            uri_conflicts = self.detect_uri_collisions()
            type_conflicts = self.detect_property_type_conflicts()
            
            # PRIORITY 2: Semantic conflicts  
            print("\n" + "🟡" * 20 + " PRIORITY 2 CONFLICTS " + "🟡" * 20)
            semantic_duplicates = self.detect_semantic_duplicates()
            inverse_candidates = self.detect_inverse_property_candidates()
            equivalent_candidates = self.detect_equivalent_class_candidates()
            
            # PRIORITY 3: Existing analyses
            print("\n" + "🟢" * 20 + " PRIORITY 3 CONFLICTS " + "🟢" * 20)
            self.detect_class_conflicts()
            self.detect_property_conflicts()
            
            # Summary
            print("\n" + "=" * 80)
            print("🎯 CONFLICT SUMMARY")
            print("=" * 80)
            print(f"🔴 CRITICAL (Priority 1):")
            print(f"   - URI Collisions: {uri_conflicts}")
            print(f"   - Property Type Conflicts: {type_conflicts}")
            print(f"🟡 SEMANTIC (Priority 2):")
            print(f"   - Semantic Duplicates: {semantic_duplicates}")
            print(f"   - Inverse Property Candidates: {inverse_candidates}")
            print(f"   - Equivalent Class Candidates: {equivalent_candidates}")
            
            total_critical = uri_conflicts + type_conflicts
            if total_critical > 0:
                print(f"\n⚠️  {total_critical} CRITICAL conflicts found!")
                print("   These MUST be resolved before merging ontologies.")
            else:
                print(f"\n✅ No critical conflicts found. Safe to proceed with merging.")
                
        except Exception as e:
            print(f"Error during analysis: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.cleanup_logging()

def main():
    """Main function with enhanced command line argument parsing"""
    parser = argparse.ArgumentParser(description='Analyze ontology conflicts across multiple files')
    parser.add_argument('ontology_files', nargs='+', 
                       help='Path(s) to ontology files to analyze (.ttl, .owl, .rdf, .n3 formats)')
    parser.add_argument('--output-dir', '-o', 
                       default='logs',
                       help='Output directory for log files (default: logs)')
    parser.add_argument('--log-name', '-l',
                       help='Custom log file name (default: auto-generated)')
    
    args = parser.parse_args()
    
    # Validate input files
    valid_files = []
    for file_path in args.ontology_files:
        if Path(file_path).exists():
            valid_files.append(file_path)
        else:
            print(f"Warning: File not found: {file_path}")
    
    if not valid_files:
        print("Error: No valid ontology files found.")
        return
    
    # Create output directory if it doesn't exist
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # Generate log file name
    if args.log_name:
        log_file = output_dir / args.log_name
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if len(valid_files) == 1:
            filename = Path(valid_files[0]).stem
            log_file = output_dir / f"conflict_analysis_{filename}_{timestamp}.log"
        else:
            log_file = output_dir / f"conflict_analysis_multi_{timestamp}.log"
    
    print(f"Analyzing {len(valid_files)} ontology file(s)")
    print(f"Output log: {log_file}")
    
    try:
        detector = OntologyConflictDetector(valid_files, str(log_file))
        detector.run_full_analysis()
        print(f"\nAnalysis complete. Results saved to: {log_file}")
        
    except KeyboardInterrupt:
        print("\nAnalysis interrupted by user")
    except Exception as e:
        print(f"Error during analysis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()