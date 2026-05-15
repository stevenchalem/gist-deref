# gist-deref

Static dereferenceable linked-data artifacts for the Semantic Arts gist ontology.

This repository generates and hosts one small RDF fragment per named `gist:` term so
IRIs such as `https://w3id.org/semanticarts/ns/ontology/gist/Account` can resolve
to useful machine-readable descriptions. The generated fragments are intended to be
served from GitHub Pages and reached through `w3id.org` redirects with basic content
negotiation.

## What Is Included

- `tools/extract_terms.py`: builds per-term Symmetric Concise Bounded Description
  (SCBD) fragments from gist ontology Turtle modules.
- `tools/semanticarts.htaccess`: proposed `w3id.org` Apache rewrite rules for the
  gist namespace and ontology document IRIs.
- `docs/terms/`: generated static term files. The current checkout contains 216
  terms in three serializations each:
  - Turtle: `*.ttl`
  - RDF/XML: `*.rdf`
  - JSON-LD: `*.jsonld`

The generated files in this repository currently target gist `14.1.0`.

## How It Works

`extract_terms.py` loads these source modules from a gist web download bundle:

- `gistCore{version}.ttl`
- `gistRdfsAnnotations{version}.ttl`
- `gistSubClassAssertions{version}.ttl`

For each named subject in the `https://w3id.org/semanticarts/ns/ontology/gist/`
namespace, it writes an SCBD fragment to `docs/terms/{LocalName}.{ttl,rdf,jsonld}`.

The SCBD includes:

- the term's outbound triples;
- recursive outbound triples for blank node objects;
- inbound triples that point at the term;
- recursive CBDs for blank node subjects in those inbound triples.

This keeps each dereferenced term small while preserving local OWL restrictions and
other blank-node structures needed to understand the term in context.

## Requirements

- Python 3.10 or newer
- `rdflib`

Install the Python dependency in your preferred environment:

```sh
python -m pip install rdflib
```

## Generate Term Files

Run the generator from the repository root:

```sh
python tools/extract_terms.py --version 14.1.0
```

By default, the script searches for source Turtle files in either of these locations:

- `./gist14.1.0_webDownload/ontologies/turtle`
- `../gist/gist14.1.0_webDownload/ontologies/turtle`

You can also pass the source directory explicitly:

```sh
python tools/extract_terms.py --version 14.1.0 --source-dir /path/to/gist14.1.0_webDownload/ontologies/turtle --output-dir docs
```

The output directory will contain:

```text
docs/
  terms/
    Account.ttl
    Account.rdf
    Account.jsonld
    ...
```

## Publishing

The generated `docs/` directory is suitable for GitHub Pages. The rewrite rules in
`tools/semanticarts.htaccess` are for `w3id.org` and redirect namespace IRIs to the
published GitHub Pages URLs.

Before deploying those rules, update the GitHub Pages base URL in
`tools/semanticarts.htaccess` if the published site is not:

```text
https://semanticarts.github.io/gist-www
```

The current rewrite rules cover:

- `https://w3id.org/semanticarts/ns/ontology/gist/`
- `https://w3id.org/semanticarts/ns/ontology/gist/{Term}`
- `https://w3id.org/semanticarts/ontology/{OntologyDocument}`

For term IRIs, content negotiation redirects to the published `/terms/` path
backed by `docs/terms/` in this repository:

- `text/turtle` -> `/terms/{Term}.ttl`
- `application/rdf+xml` -> `/terms/{Term}.rdf`
- `application/ld+json` or `application/json` -> `/terms/{Term}.jsonld`
- `text/html` -> the term anchor in the WIDOCO HTML documentation
- default clients -> Turtle

The `.htaccess` file also contains routes for full-ontology documents and WIDOCO
HTML documentation. The current repository snapshot includes generated per-term
files under `docs/terms`; add or publish the matching `ontology/` and `html/`
assets before relying on those routes in production.

The local `docs/ontologies/gist-widoco.html` file has been patched so fragment
URLs with bare gist local names, such as `#Address`, scroll to the WIDOCO entity
whose HTML `id` is the full gist IRI. Preserve or reapply that hash-navigation
change if the WIDOCO page is regenerated.

## Example

After publication and `w3id.org` configuration, clients can request a specific
serialization of a term:

```sh
curl -L -H "Accept: text/turtle" https://w3id.org/semanticarts/ns/ontology/gist/Account
curl -L -H "Accept: application/ld+json" https://w3id.org/semanticarts/ns/ontology/gist/Account
```

The same generated files can also be inspected directly in `docs/terms/`.

## Development Notes

- Generated files are committed so GitHub Pages can serve them as static assets.
- Re-run `tools/extract_terms.py` when updating to a new gist version or when the
  SCBD extraction logic changes.
- There is no automated test suite in this repository yet. A practical smoke test
  is to regenerate `docs/terms/` from a known gist bundle and review the resulting
  diff.
- No license file is currently included.
