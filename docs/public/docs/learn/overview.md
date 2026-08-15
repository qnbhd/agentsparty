# Learn agentsparty (/docs/learn/overview)

# Learn agentsparty

This tutorial builds **one** system and grows it at every step: a document
pipeline where a Writer drafts, a Reviewer decides, and a Reader publishes.
Each step is a small diff to the previous one — the roles and messages from
earlier steps stay, and new structure is added on top.

The point of the sequence is not to show seven different protocols. It is to
show one protocol surviving seven changes: adding a alt, tripping over a
projection failure, typing a payload, replacing a participant, and making the
session durable — without rewriting the conversation.

| Step | You add | New concept |
| --- | --- | --- |
| [Two roles](/docs/learn/two-roles) | Writer → Reader message | protocol, `Cast`, OpenAI model |
| [Add a alt](/docs/learn/add-a-alt) | Reviewer approves or rejects | `alt`, branch cases |
| [Knowledge of alt](/docs/learn/knowledge-of-alt) | Reader must see the outcome | `ProjectionError` |
| [Typed payloads](/docs/learn/typed-payloads) | A positive-only counter | codecs, `refine` |
| [Human review](/docs/learn/human-review) | A person in the Reviewer seat | participant kinds |
| [Journal and resume](/docs/learn/journal-and-resume) | Restart without re-asking | `Journal` |
| [Observable session](/docs/learn/observable-session) | Watch what happened | `Tracer` |

Every step uses the OpenAI model configured in the example. The full programs
live under `docs/examples/tutorial/`.

Start with [Two roles](/docs/learn/two-roles).

