# AgentBus Memory Layer

AgentBus memory is a repo-native layer that turns task and result history into searchable notes.

## Why it exists

The repo already stores the raw audit trail:

- task files
- result files
- inbox markers
- routing ledgers

That history is reliable, but it is not optimized for quick retrieval. The memory layer adds a compact, agent-friendly view on top of the raw source files.

## What memory stores

Each memory note is a markdown file with YAML frontmatter. It includes:

- a stable memory id
- a title and summary
- the authoring agent
- the source file or event that produced it
- tags for fast lookup
- related artifacts

## How it works

- a worker finishes a task
- AgentBus writes the result file
- AgentBus also writes a memory note that summarizes the outcome
- later agents can search those notes by keyword, trace id, tag, or source path

## What it is not

- not a replacement for the source files
- not a hidden database
- not a black box retrieval system

## CLI

Useful commands:

- `agentbus memory add`
- `agentbus memory capture`
- `agentbus memory search`

## Recommended usage

- keep memory entries short and concrete
- reference the source task/result path
- include trace ids whenever possible
- tag notes by agent, project area, and decision type

## Next step

If you want stronger retrieval later, this layer can be paired with embeddings or an external index without changing the underlying file format.
