#!/usr/bin/env python3
"""
extract_terms.py — Generate per-term SCBD static files from gist ontology modules.

For each named term in the gist: namespace, produces Turtle, RDF/XML, and JSON-LD
fragments containing its Symmetric Concise Bounded Description (SCBD), suitable for
serving as dereferenceable linked data from GitHub Pages via w3id.org.

SCBD definition (W3C CBD Member Submission):
  SCBD(node) = CBD(node)
             + {(s,p,node) for all s,p}
             + CBD(s) for each blank node s in the inbound set above

CBD(node) = {(node,p,o)} + CBD(o) for each blank node o

Usage:
    python extract_terms.py --version 14.1.0 [--source-dir ...] [--output-dir docs]
"""
import argparse
import sys
from pathlib import Path

from rdflib import BNode, Graph, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS, XSD

GIST_NS = "https://w3id.org/semanticarts/ns/ontology/gist/"
GISTD_NS = "https://w3id.org/semanticarts/ns/data/gist/"
DCTERMS_NS = "http://purl.org/dc/terms/"

PREFIXES = {
    "gist": Namespace(GIST_NS),
    "gistd": Namespace(GISTD_NS),
    "owl": OWL,
    "rdf": RDF,
    "rdfs": RDFS,
    "skos": SKOS,
    "xsd": XSD,
    "dcterms": Namespace(DCTERMS_NS),
}

JSONLD_CONTEXT = {
    "gist": GIST_NS,
    "gistd": GISTD_NS,
    "owl": str(OWL),
    "rdf": str(RDF),
    "rdfs": str(RDFS),
    "skos": str(SKOS),
    "xsd": str(XSD),
    "dcterms": DCTERMS_NS,
}

SOURCE_MODULES = [
    "gistCore{v}.ttl",
    "gistRdfsAnnotations{v}.ttl",
    "gistSubClassAssertions{v}.ttl",
]


# ---------------------------------------------------------------------------
# Graph loading
# ---------------------------------------------------------------------------

def load_graph(turtle_dir: Path, version: str) -> Graph:
    g = Graph()
    for prefix, ns in PREFIXES.items():
        g.bind(prefix, ns, override=True)

    for template in SOURCE_MODULES:
        path = turtle_dir / template.format(v=version)
        if not path.exists():
            print(f"  WARNING: {path} not found, skipping", file=sys.stderr)
            continue
        print(f"  Parsing {path.name} ...")
        g.parse(str(path), format="turtle")

    print(f"  Graph loaded: {len(g):,} triples")
    return g


# ---------------------------------------------------------------------------
# SCBD / CBD
# ---------------------------------------------------------------------------

def cbd(node: BNode | URIRef, g: Graph, visited: set | None = None) -> set:
    """Concise Bounded Description: outbound triples + recursive blank node objects."""
    if visited is None:
        visited = set()
    if node in visited:
        return set()
    visited.add(node)

    triples: set = set()
    for s, p, o in g.triples((node, None, None)):
        triples.add((s, p, o))
        if isinstance(o, BNode):
            triples |= cbd(o, g, visited)
    return triples


def scbd(node: URIRef, g: Graph) -> set:
    """Symmetric CBD: CBD(node) + inbound triples + CBD of blank-node subjects."""
    triples = cbd(node, g)

    bn_visited: set = set()
    for s, p, o in g.triples((None, None, node)):
        triples.add((s, p, o))
        if isinstance(s, BNode):
            triples |= cbd(s, g, bn_visited)

    return triples


# ---------------------------------------------------------------------------
# Fragment graph helpers
# ---------------------------------------------------------------------------

def build_fragment(triples: set) -> Graph:
    g = Graph()
    for prefix, ns in PREFIXES.items():
        g.bind(prefix, ns, override=True)
    for triple in triples:
        g.add(triple)
    return g


# ---------------------------------------------------------------------------
# Term enumeration
# ---------------------------------------------------------------------------

def enumerate_terms(g: Graph) -> list[URIRef]:
    """Return all named subjects in the gist: namespace, sorted."""
    terms = {
        s for s in g.subjects()
        if isinstance(s, URIRef) and str(s).startswith(GIST_NS)
    }
    return sorted(terms, key=str)


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------

def write_fragment(fg: Graph, term_dir: Path, local_name: str) -> None:
    term_dir.mkdir(parents=True, exist_ok=True)

    fg.serialize(destination=str(term_dir / f"{local_name}.ttl"), format="turtle")
    fg.serialize(destination=str(term_dir / f"{local_name}.rdf"), format="xml")
    fg.serialize(
        destination=str(term_dir / f"{local_name}.jsonld"),
        format="json-ld",
        context=JSONLD_CONTEXT,
        indent=2,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1].strip())
    parser.add_argument("--version", required=True, help="Ontology version, e.g. 14.1.0")
    parser.add_argument(
        "--source-dir",
        type=Path,
        help="Directory containing the versioned Turtle files (default: auto-detect from CWD)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("docs"),
        help="Root output directory (default: docs/)",
    )
    args = parser.parse_args()

    version = args.version
    bundle = f"gist{version}_webDownload"

    if args.source_dir:
        turtle_dir = args.source_dir
    else:
        # Auto-detect: bundle in CWD, or in sibling gist repo
        candidates = [
            Path.cwd() / bundle / "ontologies" / "turtle",
            Path(__file__).parent.parent.parent / "gist" / bundle / "ontologies" / "turtle",
        ]
        turtle_dir = next((p for p in candidates if p.exists()), None)
        if turtle_dir is None:
            print(
                f"ERROR: Could not find {bundle}/ontologies/turtle/. "
                "Pass --source-dir explicitly.",
                file=sys.stderr,
            )
            sys.exit(1)

    print(f"Source: {turtle_dir}")
    print(f"Output: {args.output_dir}")

    g = load_graph(turtle_dir, version)
    terms = enumerate_terms(g)
    print(f"\nFound {len(terms)} gist: terms")

    term_dir = args.output_dir / "terms"
    skipped = 0

    for term_uri in terms:
        local_name = str(term_uri).removeprefix(GIST_NS)
        if not local_name or "/" in local_name:
            skipped += 1
            continue

        triples = scbd(term_uri, g)
        if not triples:
            skipped += 1
            continue

        fg = build_fragment(triples)
        write_fragment(fg, term_dir, local_name)

    written = len(terms) - skipped
    print(f"Wrote {written} terms x 3 formats -> {term_dir}")
    if skipped:
        print(f"Skipped {skipped} terms (empty SCBD or malformed local name)")

    print("Done.")


if __name__ == "__main__":
    main()
