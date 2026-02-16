TypeQL 3.0 Concise Reference Guide for LLM Agents

1. [CORE_CONCEPTS]: The PERA Model and TypeQL Fundamentals

The Polymorphic Entity-Relation-Attribute (PERA) model is the strategic foundation of TypeDB 3.0, enabling a direct mapping of conceptual domain logic into a strictly-typed schema. This model eliminates the "object-relational impedance mismatch" by allowing complex, hierarchical, and multi-relational structures to exist without traditional normalization or reification. By utilizing a type-theoretic approach, TypeDB ensures Deterministic Execution and Transactional Safety while maintaining the flexibility of a hypergraph structure.

The PERA model consists of three primary components:

* Entities: Independent objects representing standalone concepts (e.g., person, vehicle). They are identified by unique internal Instance Identifiers (IIDs).
* Relations: Dependent types that define interactions between other instances via role interfaces. A relation requires "players" to exist; relations can also play roles in other relations, enabling deep nesting. They are identified by IIDs.
* Attributes: Value-carrying properties. Unlike entities, an attribute instance is identified by its value (e.g., all owners with the age of 30 refer to the same attribute instance). Attributes depend on owners unless marked with the @independent annotation.

TypeQL 3.0 standardizes all variable declarations with a unified $ prefix, categorized by the type-checker into four categories:

1. $Instance: Represents data objects (Entities, Relations, Attributes) in the database.
2. $Value: Represents computed literals or results of expressions.
3. $Type: Represents schema labels, allowing the schema itself to be variablized for parametric queries.
4. $List: Represents ordered series of data, essential for handling serialized results.

Data integrity is further supported by specific Lossless Casting rules: Integer can be losslessly cast to Double or Decimal, and Date to Datetime. However, Double to Decimal casting is not permitted due to precision differences.

Operations follow a Pipeline Execution Model where data flows through successive stages. This model distinguishes between Stateful Stages (e.g., match, insert, update), which interact with the database state, and Stateless Stages (e.g., select, reduce), which perform transformations on the current stream. This structure ensures that TypeQL operations are deterministic transitions, where each stage refines the bindings passed to the next.

2. [QUERY_TYPES]: Schema Manipulation and Data Pipelines

TypeQL 3.0 represents a paradigm shift from the logic-programming (inference-based) model of version 2.x to a Functional Database Programming Model. Rebuilt in Rust, the engine treats reasoning as explicit, modular computation rather than implicit background inference. This shift provides a 3-5x performance improvement and ensures that query execution is predictable and transparent.

Schema Queries

Schema manipulation is performed in a single-stage query to modify the structural blueprint:

* define: Adds types, interfaces, or functions.
* undefine: Removes schema elements (e.g., undefine owns name from person;).
* redefine: Modifies existing definitions. For precision in schema evolution, TypeQL 3.0 restricts redefine to a single statement per query.

Data Manipulation Stages

Data pipelines chain multiple stages to process streams of variable bindings.

* match: The primary producer and filter. If it is the first stage, it retrieves data; if it follows another stage, it filters the incoming stream based on its pattern.
* fetch: A terminal stage that serializes variable bindings into structured JSON. Because it is terminal, fetch cannot be followed by any other stage (e.g., reduce or sort). It is optimized for REST API compatibility and direct application-side consumption.

Write Operations

* insert: Creates new data instances, ownerships, or role-players.
* delete: Removes existing data or relationships.
* update: Specialised for modifying data with a cardinality of at most one (replaces existing ownership/role).
* put: An idempotent write stage. It performs an existence check for a pattern before insertion. When paired with @unique or @key, it prevents duplicate data creation across concurrent transactions.

Functions: The Reasoning Layer

Functions replace the inferential rules of 2.x. Under the "Queries as Functions" paradigm, functions are goal-driven and explicitly called.

* Scalar/Tuple Returns: Return at most one row. They must use first or last modifiers to convert a pipeline stream into a single output.
* Stream Returns: Denoted by {} in the signature, returning zero or more rows. This modularity allows logic to be separated from the data model, operating on raw values, instances, or even recursive structures.

3. [SYNTAX_PATTERNS]: Pattern Matching and Constraints

TypeQL uses declarative pattern matching where patterns act as types to ensure Semantic Integrity. The TypeDB type-checker rejects queries that are logically impossible according to the schema (e.g., matching a type with an attribute it does not own).

PERA Definitions (Schema)

define 
  entity user, owns username @key, plays friendship:friend;
  attribute username, value string;
  relation friendship, relates friend @card(0..2);


Pattern Matching (Data)

* isa: Constrains an instance to a type.
* has: Constraints an instance to an attribute ownership.
* links: Connects role players within a relation instance.
* label: Identifies a type by its schema string label.

match $u isa user, has username $n;
match $f isa friendship, links (friend: $u);


Logical Operators

* or: Disjunction (branching logic).
* not: Negation (exclusion logic; internal variables do not cause result duplication).
* try: Optionality (results are returned whether or not the block matches).

Aggregations & Grouping

The reduce stage summaries streams. When using groupby, the reduction is performed per unique value of the grouping variable.

match $file isa file, has size-kb $s;
reduce $total = sum($s), $count = count groupby $file;


Pagination

* sort: Orders the stream (e.g., sort $v asc).
* offset: Skips n rows.
* limit: Restricts the stream to n results.

These patterns are strictly enforced by the TypeDB type-checker to maintain the confluence of database logic and type theory.

4. [KEYWORD_GLOSSARY]: Essential Keywords and Operators

Standardized keywords act as the instruction set for the TypeDB engine, providing a deterministic vocabulary for LLM agents.

Keyword	Category	Brief Description
entity	Structural	Defines an independent object type.
relation	Structural	Defines a dependent interaction type.
attribute	Structural	Defines a value-carrying property type.
sub	Structural	Declares single-inheritance subtyping.
owns	Structural	Defines an attribute ownership interface.
plays	Structural	Defines a role-playing interface.
relates	Structural	Defines a role scoped within a relation.
links	Pattern	Connects role players in a relation instance.
isa	Pattern	Constraints an instance to a specific type.
has	Pattern	Constraints an instance to an attribute.
match	Pipeline	Initial/Filtering stage for retrieval.
fetch	Pipeline	Terminal stage for JSON serialization.
insert	Pipeline	Stage for adding new data instances.
put	Pipeline	Idempotent write (checks existence first).
reduce	Pipeline	Stateless stage for aggregation/grouping.
with	Pipeline	Preamble for ad-hoc query-level functions.
@card(n..m)	Annotation	Restricts number of role players or owners.
@key	Annotation	Primary ID; implies @unique and @card(1..1).
@unique	Annotation	Ensures value uniqueness across a type.
@independent	Annotation	Prevents auto-deletion of "dangling" attributes.
@cascade	Annotation	Enables cascading deletes for relations.
@range	Annotation	Restricts attribute to a numeric/date range.
@regex	Annotation	Restricts attribute to a regex pattern.
@values	Annotation	Restricts attribute to specific enum-style values.
@subkey	Annotation	Defines part of a composite joint key.
count	Operator	Returns number of results/distinct values.
sum / mean	Operator	Arithmetic sum or mean of numeric variables.
abs() / ceil()	Operator	Built-in: absolute value / nearest greater integer.
floor() / round()	Operator	Built-in: nearest lesser integer / nearest integer.

5. [USE_CASES]: Practical Logic Implementations

Complex Fetch with Subquery

[USE_CASE:STRUCTURED_FETCH] Retrieves publishers and their books in a nested JSON structure.

match $p isa publisher;
fetch {
  "name": $p.name,
  "titles": [
    match $b isa book; ($p, $b) isa publishing;
    fetch { "title": $b.title }
  ]
};


Functional Recursion (Schema)

[USE_CASE:RECURSION_FUN] A reachability function stored in the schema for transitive closure.

define fun reachable($from: node) -> { node }:
  match 
    { $_ isa edge, links (from: $from, to: $to); }
    or 
    { let $mid in reachable($from); $_ isa edge, links (from: $mid, to: $to); };
  return { $to };


Functional Recursion (Ad-hoc)

[USE_CASE:RECURSION_WITH] Defining recursion at the query level using the with preamble.

with fun path($start: node) -> { node }:
  match { ($start, $target) isa edge; } 
     or { let $via in path($start); ($via, $target) isa edge; };
  return { $target };
match $n isa node, has id "A";
let $reachable in path($n);
fetch { "reachable_id": $reachable.id };


Analytical Reduction

[USE_CASE:ANALYTICS] Calculates statistics grouped by file type.

match $f isa file, has size-kb $s;
reduce $total_size = sum($s), $file_count = count groupby $f;


Polymorphic Retrieval

[USE_CASE:POLYMORPHISM] Retrieving data from multiple subtypes (e.g., employee, contractor) via the supertype user.

match $u isa user, has full-name $n;
fetch {
  "name": $n,
  "type_label": $u.label
};


This guide serves as a stand-alone reference for TypeQL 3.0 excellence, ensuring that all interactions adhere to the high-performance, type-theoretic standards of the PERA model.
